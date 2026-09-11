"""ICHAN-DH B1 array protocol; see operative B1.1–B1.10 in the specification.

No authentication, cover reversibility, or robustness is provided. Public inputs
must not be concurrently modified during a call. This implementation is untested.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Iterator
import struct
import zlib

import numpy as np


MAGIC = b"ICHS"
VERSION = 1
HEADER_BYTES = 17
HEADER_BITS = 136
MAX_PAYLOAD_BYTES = (1 << 64) - 1
PROFILES = ((1, 0, 0), (2, 1, 0), (3, 2, 1))
_HEADER = struct.Struct(">4sBQI")


class IchanError(ValueError):
    """Protocol rejection with a stable ``code``; never contains partial output."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _integer(value: object, name: str, code: str = "E_DOMAIN") -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise IchanError(code, f"{name} must be an integer, not a boolean")
    return int(value)


@dataclass(frozen=True)
class Domain:
    """Declared stored-value domain, not display range or observed sample range."""

    bits_stored: int
    pixel_representation: int

    def __post_init__(self) -> None:
        b = _integer(self.bits_stored, "bits_stored")
        s = _integer(self.pixel_representation, "pixel_representation")
        if not 2 <= b <= 16 or s not in (0, 1):
            raise IchanError("E_DOMAIN", "require 2..16 stored bits and signedness 0 or 1")
        object.__setattr__(self, "bits_stored", b)
        object.__setattr__(self, "pixel_representation", s)

    @property
    def minimum(self) -> int:
        return -self.pixel_representation * (1 << (self.bits_stored - 1))

    @property
    def maximum(self) -> int:
        return self.minimum + self.span

    @property
    def span(self) -> int:
        return (1 << self.bits_stored) - 1


@dataclass(frozen=True)
class PaddingSpec:
    """Preserve attribute presence: absent, value alone, or inclusive value/range."""

    value: int | None = None
    range_limit: int | None = None

    def __post_init__(self) -> None:
        if self.value is None and self.range_limit is not None:
            raise IchanError("E_DICOM", "padding range requires a padding value")
        for name in ("value", "range_limit"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _integer(value, name, "E_DICOM"))
        if self.range_limit is not None and self.value > self.range_limit:
            raise IchanError("E_DICOM", "MONOCHROME2 padding endpoints must not be reversed")

    def validate(self, domain: Domain) -> None:
        if not isinstance(domain, Domain):
            raise IchanError("E_DOMAIN", "domain must be a Domain instance")
        for value in (self.value, self.range_limit):
            if value is not None and not domain.minimum <= value <= domain.maximum:
                raise IchanError("E_DICOM", "padding lies outside the stored-value domain")

    def disjoint(self, lower: int, upper: int) -> bool:
        if self.value is None:
            return True
        end = self.value if self.range_limit is None else self.range_limit
        return upper < self.value or lower > end


@dataclass(frozen=True)
class HeaderSchedule:
    positions: tuple[int, ...]
    beta: int


@dataclass(frozen=True)
class CapacityReport:
    """Profile tuples are indexed 0..2, corresponding to profiles 1..3.

    ``reserved_raw_slots`` is evaluated on the supplied array. Use the ORIGINAL
    cover for P7 opportunity accounting: header strata, unlike body strata, may
    change, so this prefix statistic is not invariant under embedding.
    """

    pixel_count: int
    beta: int
    raw_bits: tuple[int, int, int]
    reserved_raw_slots: tuple[int, int, int]

    def __post_init__(self) -> None:
        count = _integer(self.pixel_count, "pixel_count")
        beta = _integer(self.beta, "beta")
        if not HEADER_BITS <= beta <= count:
            raise IchanError("E_DOMAIN", "capacity report requires 136 <= beta <= pixel_count")
        object.__setattr__(self, "pixel_count", count)
        object.__setattr__(self, "beta", beta)
        for name, samples in (("raw_bits", count - beta), ("reserved_raw_slots", beta)):
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(values) != 3:
                raise IchanError("E_DOMAIN", "capacity fields must be three-element tuples")
            values = tuple(_integer(value, name) for value in values)
            if (not 0 <= values[0] <= values[1] <= values[2]
                    or any(value > (index + 1) * samples for index, value in enumerate(values))):
                raise IchanError("E_DOMAIN", "capacity fields violate profile bounds/order")
            object.__setattr__(self, name, values)

    @property
    def max_payload_bytes(self) -> tuple[int, int, int]:
        return tuple(value // 8 for value in self.raw_bits)

    @property
    def usable_bits(self) -> tuple[int, int, int]:
        return tuple(8 * (value // 8) for value in self.raw_bits)

    @property
    def tail_bits(self) -> tuple[int, int, int]:
        return tuple(value % 8 for value in self.raw_bits)


@dataclass(frozen=True)
class Header:
    payload_length: int
    checksum: int


def validate_array(array: np.ndarray, domain: Domain) -> np.ndarray:
    """Validate without copying, reshaping, casting, rescaling, or mutating input."""
    if not isinstance(domain, Domain):
        raise IchanError("E_DOMAIN", "domain must be a Domain instance")
    if not isinstance(array, np.ndarray) or np.ma.isMaskedArray(array):
        raise IchanError("E_DOMAIN", "array must be an unmasked NumPy integer array")
    if array.ndim != 2 or any(size <= 0 for size in array.shape):
        raise IchanError("E_DOMAIN", "array must have two positive dimensions")
    if array.dtype.kind not in ("i", "u"):
        raise IchanError("E_DOMAIN", "boolean, floating and object arrays are unsupported")
    if domain.pixel_representation == 1 and array.dtype.kind != "i":
        raise IchanError("E_DOMAIN", "signed domain requires signed integer storage")
    limits = np.iinfo(array.dtype)
    if limits.min > domain.minimum or limits.max < domain.maximum:
        raise IchanError("E_DOMAIN", "array dtype must represent the entire declared domain")
    if int(array.min()) < domain.minimum or int(array.max()) > domain.maximum:
        raise IchanError("E_DOMAIN", "observed sample outside declared domain")
    return array


def _validate_state(array: np.ndarray, domain: Domain, padding: PaddingSpec) -> np.ndarray:
    validate_array(array, domain)
    if not isinstance(padding, PaddingSpec):
        raise IchanError("E_DICOM", "padding must be an explicit PaddingSpec")
    padding.validate(domain)
    return array


def _sample(value: int, domain: Domain) -> int:
    if not isinstance(domain, Domain):
        raise IchanError("E_DOMAIN", "domain must be a Domain instance")
    value = _integer(value, "sample")
    if not domain.minimum <= value <= domain.maximum:
        raise IchanError("E_DOMAIN", "sample outside stored-value domain")
    return value


def _classify(value: int, domain: Domain) -> int:
    scaled = 255 * (value - domain.minimum)
    return 0 if scaled <= 100 * domain.span else (1 if scaled <= 150 * domain.span else 2)


def classify_value(value: int, domain: Domain) -> int:
    """B1.2: exact stratum of a single stored value."""
    return _classify(_sample(value, domain), domain)


def classify(array: np.ndarray, domain: Domain) -> np.ndarray:
    """B1.2: explanatory label array; the embedding path need not materialize it."""
    validate_array(array, domain)
    scaled = 255 * (array.astype(np.int64) - domain.minimum)
    return np.where(scaled <= 100 * domain.span, 0,
                    np.where(scaled <= 150 * domain.span, 1, 2)).astype(np.uint8)


def _block(value: int, width: int, domain: Domain) -> tuple[int, int]:
    size = 1 << width
    lower = domain.minimum + ((value - domain.minimum) // size) * size
    return lower, lower + size - 1


def replacement_block(value: int, width: int, domain: Domain) -> tuple[int, int]:
    """B1.3: inclusive stored-value endpoints of the entire aligned block."""
    value = _sample(value, domain)
    width = _integer(width, "width")
    if not 1 <= width <= domain.bits_stored:
        raise IchanError("E_DOMAIN", "block width must be within 1..bits_stored")
    return _block(value, width, domain)


def _depth(value: int, domain: Domain, padding: PaddingSpec, profile: int) -> int:
    label = _classify(value, domain)
    requested = min(PROFILES[profile - 1][label], domain.bits_stored)
    for width in range(requested, 0, -1):
        lower, upper = _block(value, width, domain)
        if (padding.disjoint(lower, upper) and _classify(lower, domain) == label
                and _classify(upper, domain) == label):
            return width
    return 0


def guarded_depth(value: int, domain: Domain, padding: PaddingSpec, profile: int) -> int:
    """B1.5: largest whole-block-safe depth, not merely nonpadding at x."""
    value = _sample(value, domain)
    if not isinstance(padding, PaddingSpec):
        raise IchanError("E_DICOM", "padding must be a PaddingSpec")
    padding.validate(domain)
    profile = _integer(profile, "profile")
    if profile not in (1, 2, 3):
        raise IchanError("E_DOMAIN", "profile must be 1, 2 or 3")
    return _depth(value, domain, padding, profile)


def _schedule(array: np.ndarray, domain: Domain, padding: PaddingSpec) -> HeaderSchedule:
    positions = []
    for index, value in enumerate(array.flat):
        if padding.disjoint(*_block(int(value), 1, domain)):
            positions.append(index)
            if len(positions) == HEADER_BITS:
                return HeaderSchedule(tuple(positions), index + 1)
    raise IchanError("E_BOOTSTRAP_CAPACITY", "fewer than 136 padding-safe header carriers")


def header_schedule(array: np.ndarray, domain: Domain,
                    padding: PaddingSpec = PaddingSpec()) -> HeaderSchedule:
    """B1.4: first 136 eligible positions, with a variable reserved prefix."""
    _validate_state(array, domain, padding)
    return _schedule(array, domain, padding)


def _capacity(array: np.ndarray, domain: Domain, padding: PaddingSpec,
              schedule: HeaderSchedule) -> CapacityReport:
    raw = [0, 0, 0]
    withheld = [0, 0, 0]
    for index, value in enumerate(array.flat):
        totals = withheld if index < schedule.beta else raw
        for profile in (1, 2, 3):
            totals[profile - 1] += _depth(int(value), domain, padding, profile)
    return CapacityReport(int(array.size), schedule.beta, tuple(raw), tuple(withheld))


def capacity(array: np.ndarray, domain: Domain,
             padding: PaddingSpec = PaddingSpec()) -> CapacityReport:
    """B1.6: raw/byte/tail report. P7 prefix opportunity cost requires original X."""
    _validate_state(array, domain, padding)
    return _capacity(array, domain, padding, _schedule(array, domain, padding))


def select_profile(report: CapacityReport, payload_length: int) -> int:
    """B1.7: first byte-feasible profile; empty payload selects profile 1."""
    length = _integer(payload_length, "payload_length", "E_LENGTH")
    if not 0 <= length <= MAX_PAYLOAD_BYTES:
        raise IchanError("E_LENGTH", "payload length outside unsigned 64-bit range")
    if not isinstance(report, CapacityReport):
        raise IchanError("E_DOMAIN", "report must be a CapacityReport")
    for profile, maximum in enumerate(report.max_payload_bytes, 1):
        if length <= maximum:
            return profile
    raise IchanError("E_CAPACITY", "no guarded profile admits this byte payload")


def _payload(payload: bytes) -> bytes:
    if not isinstance(payload, bytes):
        raise IchanError("E_DOMAIN", "payload must be immutable bytes; encode text explicitly")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise IchanError("E_LENGTH", "payload length exceeds the wire format")
    return payload


def crc32(payload: bytes) -> int:
    """Payload-only CRC-32/ISO-HDLC; not an authentication primitive."""
    return zlib.crc32(_payload(payload), 0) & 0xFFFFFFFF


def build_header(payload: bytes) -> bytes:
    _payload(payload)
    return _HEADER.pack(MAGIC, VERSION, len(payload), crc32(payload))


def parse_header(header: bytes) -> Header:
    _payload(header)
    if len(header) != HEADER_BYTES:
        raise IchanError("E_LENGTH", "header must contain exactly 17 bytes")
    magic, version, length, checksum = _HEADER.unpack(header)
    if magic != MAGIC:
        raise IchanError("E_MAGIC", "header magic is not ICHS")
    if version != VERSION:
        raise IchanError("E_VERSION", "unsupported protocol version")
    return Header(length, checksum)


def frame(payload: bytes) -> bytes:
    """Standalone framing demonstration; embed does not allocate this full copy."""
    return build_header(payload) + payload


def unframe(framed: bytes) -> bytes:
    _payload(framed)
    if len(framed) < HEADER_BYTES:
        raise IchanError("E_LENGTH", "truncated logical frame")
    header = parse_header(framed[:HEADER_BYTES])
    if len(framed) - HEADER_BYTES != header.payload_length:
        raise IchanError("E_LENGTH", "frame body length does not match header")
    payload = framed[HEADER_BYTES:]
    if crc32(payload) != header.checksum:
        raise IchanError("E_CRC", "payload-checksum mismatch")
    return payload


def _read_bits(data: bytes, offset: int, width: int) -> int:
    value = 0
    for position in range(offset, offset + width):
        value = (value << 1) | ((data[position // 8] >> (7 - position % 8)) & 1)
    return value


def _write_bits(data: bytearray, offset: int, width: int, value: int) -> None:
    for step in range(width):
        position = offset + step
        bit = (value >> (width - 1 - step)) & 1
        data[position // 8] |= bit << (7 - position % 8)


def replace_bits(value: int, width: int, chunk: int, domain: Domain) -> int:
    """B1.9 primitive: caller must enforce padding/stratum guard separately."""
    value = _sample(value, domain)
    width = _integer(width, "width")
    chunk = _integer(chunk, "chunk")
    if not 0 <= width <= domain.bits_stored or not 0 <= chunk < (1 << width):
        raise IchanError("E_DOMAIN", "invalid replacement width or chunk")
    return _replace(value, width, chunk, domain)


def _replace(value: int, width: int, chunk: int, domain: Domain) -> int:
    size = 1 << width
    return domain.minimum + ((value - domain.minimum) // size) * size + chunk


def _body_chunks(array: np.ndarray, domain: Domain, padding: PaddingSpec,
                 beta: int, profile: int, bit_count: int) -> Iterator[tuple[int, int, int]]:
    """Shared sender/receiver traversal: yields (index, bit offset, actual width)."""
    offset = 0
    for index in range(beta, int(array.size)):
        if offset == bit_count:
            return
        depth = _depth(int(array.flat[index]), domain, padding, profile)
        width = min(depth, bit_count - offset)
        if width:
            yield index, offset, width
            offset += width


def embed(array: np.ndarray, payload: bytes, domain: Domain,
          padding: PaddingSpec = PaddingSpec()) -> np.ndarray:
    """Embed B1; capacity rejection precedes the cover copy. Return only Y."""
    _validate_state(array, domain, padding)
    _payload(payload)
    schedule = _schedule(array, domain, padding)
    report = _capacity(array, domain, padding, schedule)
    profile = select_profile(report, len(payload))
    header = build_header(payload)
    result = array.copy(order="C")
    for offset, index in enumerate(schedule.positions):
        result.flat[index] = _replace(int(array.flat[index]), 1,
                                      _read_bits(header, offset, 1), domain)
    consumed = 0
    bit_count = 8 * len(payload)
    for index, offset, width in _body_chunks(array, domain, padding, schedule.beta,
                                            profile, bit_count):
        result.flat[index] = _replace(int(array.flat[index]), width,
                                      _read_bits(payload, offset, width), domain)
        consumed = offset + width
    if consumed != bit_count:
        raise IchanError("E_INTERNAL", "feasible embedding did not consume its payload")
    return result


def extract(array: np.ndarray, domain: Domain,
            padding: PaddingSpec = PaddingSpec()) -> bytes:
    """Recover B1 bytes under intact-channel assumptions; no cover/map required."""
    _validate_state(array, domain, padding)
    schedule = _schedule(array, domain, padding)
    header_bytes = bytearray(HEADER_BYTES)
    for offset, index in enumerate(schedule.positions):
        _write_bits(header_bytes, offset, 1, (int(array.flat[index]) - domain.minimum) % 2)
    header = parse_header(bytes(header_bytes))
    report = _capacity(array, domain, padding, schedule)
    if header.payload_length > report.max_payload_bytes[2]:
        raise IchanError("E_LENGTH", "declared byte length exceeds received suffix capacity")
    profile = select_profile(report, header.payload_length)
    recovered = bytearray(header.payload_length)  # only after cover-bounded validation
    bit_count = 8 * header.payload_length
    consumed = 0
    for index, offset, width in _body_chunks(array, domain, padding, schedule.beta,
                                            profile, bit_count):
        chunk = (int(array.flat[index]) - domain.minimum) % (1 << width)
        _write_bits(recovered, offset, width, chunk)
        consumed = offset + width
    if consumed != bit_count:
        raise IchanError("E_LENGTH", "truncated payload traversal")
    payload = bytes(recovered)
    if crc32(payload) != header.checksum:
        raise IchanError("E_CRC", "payload-checksum mismatch")
    return payload
