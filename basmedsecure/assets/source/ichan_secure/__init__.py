"""Canonical ICHAN-DH B1 array interface (repository codename: ichan_secure).

Optional DICOM, baseline and SSIM functions live in their respective modules;
importing the core interface does not load their optional libraries.
"""

from .core import (
    CapacityReport, Domain, Header, HeaderSchedule, IchanError, PaddingSpec,
    build_header, capacity, classify, classify_value, crc32, embed, extract,
    frame, guarded_depth, header_schedule, parse_header, replace_bits,
    replacement_block, select_profile, unframe, validate_array,
)

__version__ = "0.1.0"
__all__ = [
    "CapacityReport", "Domain", "Header", "HeaderSchedule", "IchanError", "PaddingSpec",
    "build_header", "capacity", "classify", "classify_value", "crc32", "embed", "extract",
    "frame", "guarded_depth", "header_schedule", "parse_header", "replace_bits",
    "replacement_block", "select_profile", "unframe", "validate_array",
]
