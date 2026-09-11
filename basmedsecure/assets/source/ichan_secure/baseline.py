"""Disclosed repaired BASMED reproduction: uint8, fresh fit, external depth map.

Not B1, not DICOM support, and not cover-reversible. The ordered map is required
receiver state. No implementation result has been verified by execution.
"""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np

from .core import (Domain, IchanError, PROFILES, _integer, _payload,
                   _read_bits, _write_bits, validate_array)


@dataclass(frozen=True)
class BaselineResult:
    stego: np.ndarray
    depth_map: tuple[int, ...]
    selected_profile: int
    raw_capacity_bits: tuple[int, int, int]
    target_counts: tuple[int, int, int]
    predicted_counts: tuple[int, int, int]
    label_disagreement_count: int
    fit_iterations: tuple[int, ...]
    sklearn_version: str

    @property
    def direct_map_bits(self) -> int:
        """Four-symbol direct map bits only; not Python memory or full wire cost."""
        return 2 * len(self.depth_map)


def _cover(array: np.ndarray) -> np.ndarray:
    validate_array(array, Domain(8, 0))
    if array.dtype != np.dtype("uint8"):
        raise IchanError("E_DOMAIN", "BASMED reproduction requires an unsigned uint8 cover")
    return array


def embed_baseline(cover: np.ndarray, payload: bytes) -> BaselineResult:
    """Fit once per cover, select predicted-label capacity, write ordered map.

    Disclosed operational policy: a convergence warning rejects E_BASELINE_FIT,
    rather than treating an unconverged fit as a successful baseline run.
    """
    _cover(cover)
    _payload(payload)
    flat = cover.reshape(-1, order="C")
    targets = np.where(flat <= 100, 0, np.where(flat <= 150, 1, 2))
    target_counts = tuple(int(np.count_nonzero(targets == k)) for k in range(3))
    if sum(count > 0 for count in target_counts) < 2:
        raise IchanError("E_BASELINE_CLASSES", "fit requires at least two threshold-label classes")
    try:
        import sklearn
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.linear_model import LogisticRegression
    except ImportError as exc:
        raise IchanError("E_DEPENDENCY", "install the optional baseline dependency") from exc
    if sklearn.__version__ != "1.7.2":
        raise IchanError("E_DEPENDENCY", "baseline is frozen to scikit-learn 1.7.2")
    model = LogisticRegression(solver="lbfgs", penalty="l2", C=1.0, tol=1e-4,
                               max_iter=1500, multi_class="multinomial",
                               fit_intercept=True, warm_start=False)
    features = flat.reshape(-1, 1)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(features, targets)
        predicted = model.predict(features)
    except (ValueError, ConvergenceWarning) as exc:
        raise IchanError("E_BASELINE_FIT", "fresh multinomial baseline fit failed") from exc
    counts = tuple(int(np.count_nonzero(predicted == k)) for k in range(3))
    capacities = tuple(sum(profile[k] * counts[k] for k in range(3)) for profile in PROFILES)
    length = len(payload)
    selected = next((c for c in (1, 2, 3) if length <= capacities[c - 1] // 8), None)
    if selected is None:
        raise IchanError("E_CAPACITY", "baseline predicted-label slots cannot hold payload")
    stego = cover.copy(order="C")
    depth_map = []
    consumed = 0
    bit_count = 8 * length
    for index, label in enumerate(predicted):
        if consumed == bit_count:
            break
        width = min(PROFILES[selected - 1][int(label)], bit_count - consumed)
        depth_map.append(width)  # includes zeros and the actual final partial width
        if width:
            value = int(flat[index])
            stego.flat[index] = ((value >> width) << width) | _read_bits(payload, consumed, width)
            consumed += width
    if consumed != bit_count:
        raise IchanError("E_INTERNAL", "baseline failed to consume feasible payload")
    return BaselineResult(stego, tuple(depth_map), selected, capacities, target_counts,
                          counts, int(np.count_nonzero(targets != predicted)),
                          tuple(int(value) for value in model.n_iter_), sklearn.__version__)


def extract_baseline(stego: np.ndarray, depth_map: tuple[int, ...] | list[int]) -> bytes:
    """Read external map exactly; never refit a model or infer a map from stego."""
    _cover(stego)
    if not isinstance(depth_map, (tuple, list)):
        raise IchanError("E_MAP", "external map must be a list or tuple of actual widths")
    if len(depth_map) > int(stego.size):
        raise IchanError("E_MAP", "map is longer than the cover")
    widths = tuple(_integer(value, "map width", "E_MAP") for value in depth_map)
    if any(width not in (0, 1, 2, 3) for width in widths):
        raise IchanError("E_MAP", "map widths must lie in 0..3")
    bit_count = sum(widths)
    if bit_count % 8:
        raise IchanError("E_LENGTH", "external map endpoint is not byte-aligned")
    if widths and widths[-1] == 0:
        raise IchanError("E_MAP", "canonical visited-prefix map ends on a written position")
    recovered = bytearray(bit_count // 8)
    consumed = 0
    for index, width in enumerate(widths):
        if width:
            _write_bits(recovered, consumed, width, int(stego.flat[index]) % (1 << width))
            consumed += width
    return bytes(recovered)
