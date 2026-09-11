"""Stored-domain descriptive metrics; no security or clinical interpretation."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .core import Domain, IchanError, _integer, _payload, validate_array


@dataclass(frozen=True)
class DistortionMetrics:
    mse: float
    psnr_db: float
    ssim: float | None
    ssim_window: int | None
    ssim_unavailable_reason: str | None
    data_range: int
    modified_fraction: float
    maximum_absolute_change: int


@dataclass(frozen=True)
class RecoveryMetrics:
    exact_payload: bool
    expected_bytes: int
    recovered_bytes: int | None
    bit_errors: int | None
    ber: float | None
    unavailable_reason: str | None


@dataclass(frozen=True)
class MapCost:
    positions: int
    direct_symbol_bits: int
    byte_packed_symbol_bytes: int
    complete_serialized_bytes: int | None = None


def distortion_metrics(cover: np.ndarray, stego: np.ndarray, domain: Domain,
                       *, ssim_window: int | None = 7) -> DistortionMetrics:
    """C23: R=2**b-1. No automatic window shrink across differently sized data.

    SSIM uses uniform weights, sample covariance, K1=.01, K2=.03, and no channel
    axis. Undersized images return an explicit unavailable SSIM, not a substitute.
    An unavailable optional dependency raises E_DEPENDENCY when SSIM is requested.
    """
    validate_array(cover, domain)
    validate_array(stego, domain)
    if cover.shape != stego.shape:
        raise IchanError("E_DOMAIN", "metric arrays must have identical shape")
    difference = cover.astype(np.float64) - stego.astype(np.float64)
    mse = float(np.mean(difference * difference))
    psnr = math.inf if mse == 0 else 10 * math.log10(domain.span * domain.span / mse)
    score = None
    unavailable = "SSIM not requested"
    if ssim_window is not None:
        ssim_window = _integer(ssim_window, "ssim_window", "E_METRIC")
        if ssim_window < 3 or ssim_window % 2 == 0:
            raise IchanError("E_METRIC", "SSIM window must be an odd integer >=3")
        if min(cover.shape) < ssim_window:
            unavailable = "image smaller than the declared SSIM window"
        else:
            try:
                from skimage.metrics import structural_similarity
            except ImportError as exc:
                raise IchanError("E_DEPENDENCY", "install the optional metrics dependency") from exc
            score = float(structural_similarity(
                cover.astype(np.float64), stego.astype(np.float64),
                data_range=domain.span, win_size=ssim_window, channel_axis=None,
                gaussian_weights=False, use_sample_covariance=True, K1=0.01, K2=0.03))
            unavailable = None
    return DistortionMetrics(mse, psnr, score, ssim_window, unavailable, domain.span,
                             float(np.count_nonzero(difference) / cover.size),
                             int(np.max(np.abs(difference))))


def recovery_metrics(expected: bytes, recovered: bytes | None) -> RecoveryMetrics:
    """BER unavailable for rejected or length-mismatched recovery; empty BER=0."""
    _payload(expected)
    if recovered is None:
        return RecoveryMetrics(False, len(expected), None, None, None, "no recovered payload")
    _payload(recovered)
    if len(expected) != len(recovered):
        return RecoveryMetrics(False, len(expected), len(recovered), None, None,
                               "payload lengths differ; BER denominator is not comparable")
    errors = sum((left ^ right).bit_count() for left, right in zip(expected, recovered))
    ber = errors / (8 * len(expected)) if expected else 0.0
    return RecoveryMetrics(expected == recovered, len(expected), len(recovered), errors, ber, None)


def direct_map_cost(mapped_positions: int) -> MapCost:
    """C24: only direct four-symbol storage, not compressed entropy or wire size.

    Complete serialized size stays unavailable until endpoint, framing and other
    container fields have an actual representation in the evaluation protocol.
    """
    positions = _integer(mapped_positions, "mapped_positions", "E_METRIC")
    if positions < 0:
        raise IchanError("E_METRIC", "mapped-position count cannot be negative")
    bits = 2 * positions
    return MapCost(positions, bits, (bits + 7) // 8)
