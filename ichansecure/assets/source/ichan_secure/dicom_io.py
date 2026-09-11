"""Conservative CT-only DICOM boundary for the ICHAN-DH B1 protocol.

This module operates on decoded *stored values*.  It never applies modality,
VOI, or display transforms.  Acceptance is deliberately narrower than general
DICOM support and is not a claim of complete CT IOD conformance.

Normative/API references used for this Gate 4 implementation:

* DICOM PS3.3, CT Image Module and common image metadata (current edition)
  https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.8.2.html
  https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.7.6.html
* DICOM PS3.4, CT Image Storage SOP Class UID (current edition)
  https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_b.5.html
* pydicom 3.0.2 pixel decoding and writing APIs
  https://pydicom.github.io/pydicom/stable/guides/user/working_with_pixel_data.html
  https://pydicom.github.io/pydicom/stable/reference/generated/pydicom.pixels.utils.set_pixel_data.html

No file-interface evidence is implied until the Gate 5 fixtures are executed.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from io import BytesIO
from numbers import Integral
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np

try:
    import pydicom
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.encaps import parse_basic_offsets, parse_fragments
    from pydicom.pixels import get_decoder
    from pydicom.sequence import Sequence as DicomSequence
    from pydicom.tag import Tag
    from pydicom.uid import (
        CTImageStorage,
        ExplicitVRLittleEndian,
        ImplicitVRLittleEndian,
        PYDICOM_IMPLEMENTATION_UID,
        RLELossless,
        UID,
        generate_uid,
    )
except ImportError as exc:  # pragma: no cover - exercised by packaging checks
    raise ImportError(
        "ichan_secure.dicom_io requires the optional dependency "
        "pydicom==3.0.2"
    ) from exc

if str(pydicom.__version__) != "3.0.2":
    raise ImportError("ichan_secure.dicom_io is frozen to pydicom==3.0.2")

from .core import (
    Domain,
    IchanError,
    PaddingSpec,
    embed,
    extract,
    validate_array,
)


# Explicit version-1 source allowlist.  Big-endian, deflated, JPEG, JPEG-LS,
# JPEG 2000 and HTJ2K inputs remain outside the evidence campaign.
_NATIVE_TRANSFER_SYNTAXES = frozenset(
    (str(ImplicitVRLittleEndian), str(ExplicitVRLittleEndian))
)
_RLE_TRANSFER_SYNTAX = str(RLELossless)
SUPPORTED_TRANSFER_SYNTAXES = frozenset(
    (*_NATIVE_TRANSFER_SYNTAXES, _RLE_TRANSFER_SYNTAX)
)

_SIGNATURE_TAGS = (Tag(0xFFFA, 0xFFFA), Tag(0x4FFE, 0x0001))
_PIXEL_DATA_KEYWORDS = frozenset(
    ("PixelData", "FloatPixelData", "DoubleFloatPixelData")
)
_UNSUPPORTED_PIXEL_DEPENDENCIES = frozenset(
    (
        "FramePixelDataPropertiesSequence",
        "HistogramSequence",
        "IconImageSequence",
        "MaskSubtractionSequence",
        "ModalityLUTSequence",
        "PaletteColorLookupTableSequence",
        "PixelDataProviderURL",
        "PixelIntensityRelationship",
        "PixelIntensityRelationshipSign",
        "PixelValueTransformationSequence",
        "RealWorldValueMappingSequence",
        "StoredValueColorRangeSequence",
        "VOILUTSequence",
        "EncryptedAttributesSequence",
    )
)
_ENCAPSULATION_ONLY_KEYWORDS = (
    "ExtendedOffsetTable",
    "ExtendedOffsetTableLengths",
    "EncapsulatedPixelDataValueTotalLength",
)
_SERIES_EXTREMA = (
    "SmallestPixelValueInSeries",
    "LargestPixelValueInSeries",
)
_IMAGE_EXTREMA = (
    "SmallestImagePixelValue",
    "LargestImagePixelValue",
)
_FILE_META_PROVENANCE = (
    "SourceApplicationEntityTitle",
    "SendingApplicationEntityTitle",
    "ReceivingApplicationEntityTitle",
    "PrivateInformationCreatorUID",
    "PrivateInformation",
)

# These preflight limits bound declared/encoded input sizes; they are neither
# algorithmic capacity claims nor hard bounds on a decoder's peak RAM usage.
MAX_DECLARED_PIXEL_BYTES = 256 * 1024 * 1024
MAX_DICOM_FILE_BYTES = 512 * 1024 * 1024


@dataclass(frozen=True)
class DecoderMetadata:
    """Non-PHI decoder provenance needed to reproduce the stored-value load."""

    pydicom_version: str
    transfer_syntax_uid: str
    transfer_syntax_name: str
    backend: str
    decoding_plugin: str
    raw: bool
    allow_excess_frames: bool


@dataclass(frozen=True)
class LoadedDicom:
    """Accepted CT snapshot and the immutable B1 receiver state derived from it."""

    dataset: Dataset = field(repr=False)
    array: np.ndarray = field(repr=False)
    domain: Domain
    padding: PaddingSpec
    source_path: Path = field(repr=False)
    decoder: DecoderMetadata


class DicomWriteError(IchanError):
    """Write failure with an explicit publication/cleanup outcome.

    Paths are attributes rather than message text so routine exception logging
    does not disclose source-derived filenames.  If ``destination_published``
    is true, the verified destination exists even though temporary cleanup
    failed and the caller must treat that outcome as committed.
    """

    def __init__(
        self,
        message: str,
        *,
        destination_published: bool,
        destination_path: Path | None = None,
        temporary_path: Path | None = None,
    ) -> None:
        self.destination_published = destination_published
        self.destination_path = destination_path
        self.temporary_path = temporary_path
        super().__init__("E_DICOM", message)


def _reject(message: str) -> None:
    raise IchanError("E_DICOM", message)


def _integer(value: object, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        _reject(f"{name} must be one scalar integer")
    return int(value)


def _required_integer(dataset: Dataset, keyword: str) -> int:
    if keyword not in dataset:
        _reject(f"missing required {keyword}")
    return _integer(getattr(dataset, keyword), keyword)


def _required_text(dataset: Dataset, keyword: str) -> str:
    if keyword not in dataset:
        _reject(f"missing required {keyword}")
    value = getattr(dataset, keyword)
    if isinstance(value, Sequence) and not isinstance(value, str):
        _reject(f"{keyword} must have one value")
    text = str(value).strip()
    if not text:
        _reject(f"{keyword} must not be empty")
    return text


def _required_uid(dataset: Dataset, keyword: str) -> str:
    text = _required_text(dataset, keyword)
    uid = UID(text)
    if not uid.is_valid:
        _reject(f"{keyword} is not a valid UID")
    return text


def _multi_text(value: object, name: str) -> tuple[str, ...]:
    if isinstance(value, str):
        values = value.split("\\")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values = [str(item) for item in value]
    else:
        _reject(f"{name} must be a text value sequence")
    return tuple(item.strip() for item in values)


def _iter_datasets(dataset: Dataset) -> Iterator[tuple[Dataset, bool]]:
    """Yield every nested Dataset and whether it is the top-level object."""

    stack: list[tuple[Dataset, bool]] = [(dataset, True)]
    while stack:
        current, is_root = stack.pop()
        yield current, is_root
        nested: list[Dataset] = []
        for element in current:
            if element.VR == "SQ" and element.value:
                nested.extend(item for item in element.value if isinstance(item, Dataset))
        stack.extend((item, False) for item in reversed(nested))


def _audit_elements(dataset: Dataset) -> None:
    """Apply the bounded version-1 element audit.

    Standard patient, study, series, geometry, acquisition, rescale and scalar
    window metadata are preserved.  This is not an audit of every public DICOM
    element: private/unknown elements, overlays/curves and the enumerated
    unhandled pixel-dependent structures are rejected.
    """

    for current, is_root in _iter_datasets(dataset):
        for element in current:
            tag = element.tag
            keyword = element.keyword
            if tag.is_private:
                _reject(f"private element {tag} is outside the Gate 4 audit profile")
            if not keyword or element.VR == "UN":
                _reject(f"unknown element {tag} is outside the Gate 4 audit profile")
            if 0x5000 <= tag.group <= 0x50FF or 0x6000 <= tag.group <= 0x60FF:
                _reject(f"curve or overlay element {tag} is unsupported")
            if keyword in _UNSUPPORTED_PIXEL_DEPENDENCIES:
                _reject(f"unsupported pixel-dependent attribute {keyword}")
            if keyword in _PIXEL_DATA_KEYWORDS and not (
                is_root and keyword == "PixelData"
            ):
                _reject(f"nested or noninteger pixel data {keyword} is unsupported")


def _validate_file_meta(dataset: Dataset) -> str:
    file_meta = getattr(dataset, "file_meta", None)
    if not isinstance(file_meta, FileMetaDataset):
        _reject("DICOM File Meta Information is required")

    transfer_syntax = _required_uid(file_meta, "TransferSyntaxUID")
    if transfer_syntax not in SUPPORTED_TRANSFER_SYNTAXES:
        _reject("source Transfer Syntax UID is outside the explicit allowlist")

    media_class = _required_uid(file_meta, "MediaStorageSOPClassUID")
    media_instance = _required_uid(file_meta, "MediaStorageSOPInstanceUID")
    if media_class != _required_uid(dataset, "SOPClassUID"):
        _reject("Media Storage SOP Class UID disagrees with SOP Class UID")
    if media_instance != _required_uid(dataset, "SOPInstanceUID"):
        _reject("Media Storage SOP Instance UID disagrees with SOP Instance UID")
    return transfer_syntax


def _validate_ct_metadata(dataset: Dataset, transfer_syntax: str) -> tuple[Domain, int, int]:
    if _required_uid(dataset, "SOPClassUID") != str(CTImageStorage):
        _reject("only CT Image Storage is supported")
    if _required_text(dataset, "Modality") != "CT":
        _reject("Modality must be CT")
    if _required_integer(dataset, "SamplesPerPixel") != 1:
        _reject("SamplesPerPixel must be 1")
    if _required_text(dataset, "PhotometricInterpretation") != "MONOCHROME2":
        _reject("PhotometricInterpretation must be MONOCHROME2")
    if "PlanarConfiguration" in dataset:
        _reject("PlanarConfiguration must be absent for one sample per pixel")

    rows = _required_integer(dataset, "Rows")
    columns = _required_integer(dataset, "Columns")
    if rows <= 0 or columns <= 0:
        _reject("Rows and Columns must be positive")
    frames = 1 if "NumberOfFrames" not in dataset else _integer(
        dataset.NumberOfFrames, "NumberOfFrames"
    )
    if frames != 1:
        _reject("exactly one two-dimensional frame is supported")

    bits_allocated = _required_integer(dataset, "BitsAllocated")
    bits_stored = _required_integer(dataset, "BitsStored")
    high_bit = _required_integer(dataset, "HighBit")
    representation = _required_integer(dataset, "PixelRepresentation")
    if bits_allocated != 16:
        _reject("CT Gate 4 requires BitsAllocated equal to 16")
    if not 2 <= bits_stored <= 16:
        _reject("BitsStored must be within the B1 range 2..16")
    if bits_stored > bits_allocated or high_bit != bits_stored - 1:
        _reject("BitsStored, BitsAllocated and HighBit are inconsistent")
    if representation not in (0, 1):
        _reject("PixelRepresentation must be 0 or 1")

    if "PixelData" not in dataset:
        _reject("integer PixelData is required")
    if "FloatPixelData" in dataset or "DoubleFloatPixelData" in dataset:
        _reject("floating-point pixel data is unsupported")

    if "ImageType" not in dataset:
        _reject("CT ImageType is required")
    image_type = _multi_text(dataset.ImageType, "ImageType")
    if len(image_type) < 2 or image_type[0] not in ("ORIGINAL", "DERIVED"):
        _reject("ImageType must identify ORIGINAL or DERIVED pixel data")
    if image_type[1] not in ("PRIMARY", "SECONDARY"):
        _reject("ImageType must identify PRIMARY or SECONDARY examination data")

    # CT Image Module Type 1 values.  They are retained but never applied by B1.
    for keyword in ("RescaleIntercept", "RescaleSlope"):
        text = _required_text(dataset, keyword)
        try:
            numeric = float(text)
        except (TypeError, ValueError):
            _reject(f"{keyword} must be numeric")
        if not np.isfinite(numeric):
            _reject(f"{keyword} must be finite")

    lossy = None
    if "LossyImageCompression" in dataset:
        lossy = _required_text(dataset, "LossyImageCompression")
        if lossy not in ("00", "01"):
            _reject("LossyImageCompression must be 00 or 01 when present")
        if lossy == "01":
            _reject("objects with lifetime lossy-compression history are unsupported")
    lossy_details = tuple(
        keyword
        for keyword in ("LossyImageCompressionRatio", "LossyImageCompressionMethod")
        if keyword in dataset
    )
    if lossy_details and lossy != "01":
        _reject("lossy-history detail conflicts with an absent or nonlossy flag")

    expected_bytes = rows * columns * 2
    if expected_bytes > MAX_DECLARED_PIXEL_BYTES:
        _reject("declared frame exceeds the fixed Gate 4 size limit")
    pixel_element = dataset["PixelData"]
    if transfer_syntax in _NATIVE_TRANSFER_SYNTAXES:
        if pixel_element.VR != "OW" or pixel_element.is_undefined_length:
            _reject("native 16-bit PixelData must use definite-length OW encoding")
        try:
            encoded_bytes = len(dataset.PixelData)
        except (TypeError, ValueError):
            _reject("native PixelData does not expose a definite byte length")
        if encoded_bytes != expected_bytes:
            _reject("native PixelData byte length disagrees with Rows and Columns")
    else:
        if pixel_element.VR != "OB" or not pixel_element.is_undefined_length:
            _reject("RLE Lossless PixelData must use undefined-length OB encoding")
        if (
            "ExtendedOffsetTable" in dataset
            or "ExtendedOffsetTableLengths" in dataset
            or "EncapsulatedPixelDataValueTotalLength" in dataset
        ):
            _reject("RLE auxiliary offset or length tables are outside the Gate 4 profile")
        try:
            encoded_value = dataset.PixelData
            encoded_bytes = len(encoded_value)
        except (TypeError, ValueError):
            _reject("RLE PixelData does not expose a definite encoded byte length")
        # Enforce the byte cap before any parser can allocate an offset list.
        if encoded_bytes > MAX_DECLARED_PIXEL_BYTES:
            _reject("encoded RLE PixelData exceeds the fixed Gate 4 size limit")
        if not isinstance(encoded_value, (bytes, bytearray)) or encoded_bytes < 16:
            _reject("RLE PixelData has an invalid encapsulated byte value")

        try:
            item_tag = b"\xfe\xff\x00\xe0"
            delimiter = b"\xfe\xff\xdd\xe0\x00\x00\x00\x00"
            if encoded_value[:4] != item_tag:
                _reject("RLE PixelData does not begin with a Basic Offset Table")
            bot_length = int.from_bytes(encoded_value[4:8], "little")
            if bot_length not in (0, 4):
                _reject("single-frame RLE Basic Offset Table length must be 0 or 4")

            fragment_start = 8 + bot_length
            if encoded_bytes < fragment_start + 8:
                _reject("single-frame RLE PixelData is missing its frame fragment")
            if encoded_value[fragment_start : fragment_start + 4] != item_tag:
                _reject("RLE frame fragment has an invalid item tag")
            fragment_length = int.from_bytes(
                encoded_value[fragment_start + 4 : fragment_start + 8], "little"
            )
            if fragment_length < 2 or fragment_length % 2:
                _reject("RLE frame fragment length must be positive and even")
            fragment_end = fragment_start + 8 + fragment_length
            if fragment_end > encoded_bytes:
                _reject("RLE frame fragment length exceeds PixelData")
            trailing_bytes = encoded_bytes - fragment_end
            if trailing_bytes not in (0, len(delimiter)) or (
                trailing_bytes == len(delimiter)
                and encoded_value[fragment_end : fragment_end + len(delimiter)]
                != delimiter
            ):
                _reject("single-frame RLE PixelData contains extra fragment data")

            stream = BytesIO(encoded_value)
            basic_offsets = parse_basic_offsets(stream)
            # parse_basic_offsets() leaves the stream positioned at the first
            # actual fragment; parsing the complete value would incorrectly
            # count the Basic Offset Table item as a frame fragment.
            fragment_count, _ = parse_fragments(stream)
        except Exception as exc:
            if isinstance(exc, IchanError):
                raise
            raise IchanError("E_DICOM", "invalid RLE encapsulation") from exc
        if basic_offsets not in ([], [0]):
            _reject("single-frame RLE Basic Offset Table must be empty or contain zero")
        # DICOM RLE encodes each frame in exactly one fragment.  Requiring one
        # fragment prevents a declared one-frame object from hiding extra frames.
        if fragment_count != 1:
            _reject("single-frame RLE Lossless PixelData must contain one fragment")

    return Domain(bits_stored, representation), rows, columns


def _parse_padding(dataset: Dataset, domain: Domain) -> PaddingSpec:
    expected_vr = "SS" if domain.pixel_representation else "US"
    value_element = dataset.data_element("PixelPaddingValue")
    limit_element = dataset.data_element("PixelPaddingRangeLimit")
    if value_element is None and limit_element is not None:
        _reject("PixelPaddingRangeLimit requires PixelPaddingValue")

    value: int | None = None
    limit: int | None = None
    if value_element is not None:
        if value_element.VR != expected_vr:
            _reject("PixelPaddingValue VR disagrees with PixelRepresentation")
        value = _integer(value_element.value, "PixelPaddingValue")
    if limit_element is not None:
        if limit_element.VR != expected_vr:
            _reject("PixelPaddingRangeLimit VR disagrees with PixelRepresentation")
        limit = _integer(limit_element.value, "PixelPaddingRangeLimit")

    padding = PaddingSpec(value=value, range_limit=limit)
    padding.validate(domain)
    return padding


def _decoder_metadata(transfer_syntax: str, plugin: str) -> DecoderMetadata:
    uid = UID(transfer_syntax)
    return DecoderMetadata(
        pydicom_version=str(pydicom.__version__),
        transfer_syntax_uid=transfer_syntax,
        transfer_syntax_name=uid.name,
        backend="pydicom.pixels",
        decoding_plugin=plugin or "pydicom native",
        raw=True,
        allow_excess_frames=False,
    )


def _decode_stored_values(
    dataset: Dataset,
    transfer_syntax: str,
    domain: Domain,
    rows: int,
    columns: int,
) -> tuple[np.ndarray, DecoderMetadata]:
    plugin = ""
    if transfer_syntax == _RLE_TRANSFER_SYNTAX:
        decoder = get_decoder(transfer_syntax)
        if "pydicom" not in decoder.available_plugins:
            _reject("the built-in pydicom RLE Lossless decoder is unavailable")
        plugin = "pydicom"

    try:
        dataset.pixel_array_options(
            raw=True,
            decoding_plugin=plugin,
            allow_excess_frames=False,
        )
        decoded = dataset.pixel_array
    except MemoryError:
        _reject("insufficient memory while decoding PixelData")
    except Exception as exc:
        raise IchanError("E_DICOM", "supported PixelData decoding failed") from exc

    if not isinstance(decoded, np.ndarray) or np.ma.isMaskedArray(decoded):
        _reject("decoder did not return an unmasked NumPy array")
    if decoded.ndim != 2 or decoded.shape != (rows, columns):
        _reject("decoded frame shape disagrees with Rows and Columns")
    if decoded.size != rows * columns or decoded.dtype.kind not in ("i", "u"):
        _reject("decoded sample count or integer interpretation is invalid")
    expected_kind = "i" if domain.pixel_representation else "u"
    if decoded.dtype.kind != expected_kind or decoded.dtype.itemsize != 2:
        _reject("decoded dtype disagrees with the declared 16-bit signedness")

    # Return an independent native-endian C-order snapshot, as required by C21.
    dtype = np.dtype(np.int16 if domain.pixel_representation else np.uint16)
    try:
        snapshot = np.array(decoded, dtype=dtype, order="C", copy=True)
    except MemoryError:
        _reject("insufficient memory while copying decoded stored values")
    validate_array(snapshot, domain)
    snapshot.setflags(write=False)
    return snapshot, _decoder_metadata(transfer_syntax, plugin)


def _validate_actual_extrema(dataset: Dataset, array: np.ndarray) -> None:
    actual = (int(array.min()), int(array.max()))
    expected_vr = "SS" if _required_integer(dataset, "PixelRepresentation") else "US"
    for keyword, expected in zip(_IMAGE_EXTREMA, actual):
        element = dataset.data_element(keyword)
        if element is not None:
            if element.VR != expected_vr:
                _reject(f"{keyword} VR disagrees with PixelRepresentation")
            if _integer(element.value, keyword) != expected:
                _reject(f"{keyword} disagrees with the decoded stored values")


def _read_path(path: str | os.PathLike[str]) -> Path:
    try:
        resolved = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise IchanError("E_DICOM", "source path is not a readable existing file") from exc
    if not resolved.is_file():
        _reject("source path is not a regular file")
    return resolved


def load_dicom(path: str | os.PathLike[str]) -> LoadedDicom:
    """Load one accepted CT object as an immutable stored-value snapshot.

    The returned ``dataset`` remains mutable for pydicom interoperability, while
    ``array`` is an independent read-only copy.  Repr output suppresses both and
    the source path so accidental logging does not expose patient data or paths.
    """

    source_path = _read_path(path)
    try:
        with source_path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > MAX_DICOM_FILE_BYTES:
                _reject("DICOM file exceeds the fixed Gate 4 size limit")
            # No deferred elements: the accepted Dataset is one complete input
            # snapshot and the writer never silently reloads a changed source.
            dataset = pydicom.dcmread(stream, defer_size=None, force=False)
            after = os.fstat(stream.fileno())
            identity_before = (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            )
            identity_after = (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            )
            if identity_before != identity_after:
                _reject("source file changed while it was being read")
    except IchanError:
        raise
    except MemoryError:
        _reject("insufficient memory while reading the DICOM object")
    except Exception as exc:
        raise IchanError("E_DICOM", "DICOM File Format parsing failed") from exc

    transfer_syntax = _validate_file_meta(dataset)
    _audit_elements(dataset)
    _audit_elements(dataset.file_meta)
    domain, rows, columns = _validate_ct_metadata(dataset, transfer_syntax)
    padding = _parse_padding(dataset, domain)
    array, decoder = _decode_stored_values(
        dataset, transfer_syntax, domain, rows, columns
    )
    _validate_actual_extrema(dataset, array)
    return LoadedDicom(
        dataset=dataset,
        array=array,
        domain=domain,
        padding=padding,
        source_path=source_path,
        decoder=decoder,
    )


def _remove_recursive_signatures(dataset: Dataset) -> None:
    # Materialize first so deleting a parent signature sequence cannot alter the
    # traversal.  DICOM permits the Digital Signatures Macro in sequence items.
    for current, _ in tuple(_iter_datasets(dataset)):
        for tag in _SIGNATURE_TAGS:
            if tag in current:
                del current[tag]


def _remove_if_present(dataset: Dataset, keywords: Sequence[str]) -> None:
    for keyword in keywords:
        if keyword in dataset:
            del dataset[keyword]


def _preserves_padding_membership(
    source: np.ndarray,
    candidate: np.ndarray,
    padding: PaddingSpec,
) -> None:
    """Require exact Pi-membership preservation without one full-size mask."""

    if padding.value is None:
        return
    upper = padding.value if padding.range_limit is None else padding.range_limit
    block_size = 1_048_576
    try:
        for start in range(0, int(source.size), block_size):
            stop = min(start + block_size, int(source.size))
            source_block = source.flat[start:stop]
            candidate_block = candidate.flat[start:stop]
            source_mask = (source_block >= padding.value) & (source_block <= upper)
            candidate_mask = (
                (candidate_block >= padding.value) & (candidate_block <= upper)
            )
            if not np.array_equal(source_mask, candidate_mask):
                _reject("stego array changes declared pixel-padding membership")
    except MemoryError:
        _reject("insufficient memory while validating pixel-padding membership")


def _prepare_derived_dataset(loaded: LoadedDicom, stego: np.ndarray) -> Dataset:
    if not isinstance(stego, np.ndarray):
        raise IchanError("E_DOMAIN", "stego must be a NumPy array")
    validate_array(stego, loaded.domain)
    if stego.shape != loaded.array.shape:
        raise IchanError("E_DOMAIN", "stego shape must match the source frame")
    _preserves_padding_membership(loaded.array, stego, loaded.padding)
    source_receiver_state = _receiver_metadata_state(loaded.dataset)

    dtype = np.dtype(np.int16 if loaded.domain.pixel_representation else np.uint16)
    try:
        encoded = np.ascontiguousarray(stego, dtype=dtype)
        derived = copy.deepcopy(loaded.dataset)
    except MemoryError:
        _reject("insufficient memory while preparing the derived object")

    try:
        derived.set_pixel_data(
            encoded,
            photometric_interpretation="MONOCHROME2",
            bits_stored=loaded.domain.bits_stored,
            generate_instance_uid=False,
        )
    except Exception as exc:
        raise IchanError("E_DICOM", "setting derived integer PixelData failed") from exc

    new_instance_uid = generate_uid()
    new_series_uid = generate_uid()
    derived.SOPInstanceUID = new_instance_uid
    derived.SeriesInstanceUID = new_series_uid

    source_type = _multi_text(loaded.dataset.ImageType, "ImageType")
    derived.ImageType = ["DERIVED", "SECONDARY", *source_type[2:]]
    derived.DerivationDescription = (
        "ICHAN-DH research tooling: stored-value research modification; "
        "no algorithm-embedding, security, or clinical-safety claim."
    )
    reference = Dataset()
    reference.ReferencedSOPClassUID = str(CTImageStorage)
    reference.ReferencedSOPInstanceUID = str(loaded.dataset.SOPInstanceUID)
    derived.SourceImageSequence = DicomSequence([reference])

    # Content Date and Time are Type 2C in the General Image Module.  Always
    # emitting their permitted zero-length Type 2 values avoids retaining a
    # false source-pixel creation timestamp while preserving the conditional
    # element presence required by temporally related Series.  Instance-level
    # creation fields are optional and are removed rather than copied stale.
    _remove_if_present(
        derived,
        (
            "InstanceCreationDate",
            "InstanceCreationTime",
            "InstanceCreatorUID",
        ),
    )
    derived.ContentDate = ""
    derived.ContentTime = ""
    _remove_if_present(derived, _ENCAPSULATION_ONLY_KEYWORDS)
    _remove_if_present(derived, _SERIES_EXTREMA)
    _remove_if_present(derived, ("DataSetTrailingPadding",))
    _remove_recursive_signatures(derived)

    # Image extrema are Type 3 but, when emitted, must be actual full-image
    # extrema.  Recompute both so the pair cannot remain partially stale.
    extrema_vr = "SS" if loaded.domain.pixel_representation else "US"
    extrema = (
        (Tag(0x0028, 0x0106), int(encoded.min())),
        (Tag(0x0028, 0x0107), int(encoded.max())),
    )
    for tag, value in extrema:
        if tag in derived:
            del derived[tag]
        derived.add_new(tag, extrema_vr, value)

    if not isinstance(getattr(derived, "file_meta", None), FileMetaDataset):
        derived.file_meta = FileMetaDataset()
    derived.file_meta.FileMetaInformationVersion = b"\x00\x01"
    derived.file_meta.MediaStorageSOPClassUID = str(CTImageStorage)
    derived.file_meta.MediaStorageSOPInstanceUID = new_instance_uid
    derived.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    derived.file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
    implementation_version = "PYDICOM_" + str(pydicom.__version__).replace(".", "_")
    derived.file_meta.ImplementationVersionName = implementation_version[:16]
    _remove_if_present(derived.file_meta, _FILE_META_PROVENANCE)
    derived.preamble = b"\x00" * 128

    if _receiver_metadata_state(derived) != source_receiver_state:
        _reject("derived preparation changed required receiver metadata")
    if _parse_padding(derived, loaded.domain) != loaded.padding:
        _reject("derived preparation changed the receiver padding state")
    _validate_actual_extrema(derived, encoded)
    return derived


def _same_file(source: Path, destination: Path) -> bool:
    if source == destination:
        return True
    if destination.exists():
        try:
            return os.path.samefile(source, destination)
        except OSError:
            return False
    return False


def _destination_path(
    source: Path,
    destination: str | os.PathLike[str],
    overwrite: bool,
) -> Path:
    if not isinstance(overwrite, bool):
        _reject("overwrite must be a boolean")
    try:
        supplied = Path(destination).expanduser()
        target = supplied if supplied.is_absolute() else Path.cwd() / supplied
        target = target.absolute()
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise IchanError("E_DICOM", "destination path is invalid") from exc
    if not target.parent.is_dir():
        _reject("destination directory must already exist")
    if os.path.lexists(target) and target.is_symlink():
        _reject("symbolic-link destinations are unsupported")
    if _same_file(source, target):
        _reject("source and destination must be distinct files")
    if target.exists() and not overwrite:
        _reject("destination exists and overwrite was not authorized")
    if target.exists() and not target.is_file():
        _reject("destination is not a regular file")
    return target


def _optional_element_state(dataset: Dataset, keyword: str) -> tuple[str, Any] | None:
    element = dataset.data_element(keyword)
    if element is None:
        return None
    value = element.value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        normalized: Any = tuple(str(item) for item in value)
    else:
        normalized = str(value)
    return element.VR, normalized


def _receiver_metadata_state(dataset: Dataset) -> tuple[Any, ...]:
    """State that B1 extraction reconstructs or the output must preserve."""

    padding_value = dataset.data_element("PixelPaddingValue")
    padding_limit = dataset.data_element("PixelPaddingRangeLimit")
    return (
        _required_uid(dataset, "SOPClassUID"),
        _required_text(dataset, "Modality"),
        _required_integer(dataset, "Rows"),
        _required_integer(dataset, "Columns"),
        _required_integer(dataset, "SamplesPerPixel"),
        _required_text(dataset, "PhotometricInterpretation"),
        _required_integer(dataset, "BitsAllocated"),
        _required_integer(dataset, "BitsStored"),
        _required_integer(dataset, "HighBit"),
        _required_integer(dataset, "PixelRepresentation"),
        None if padding_value is None else (padding_value.VR, int(padding_value.value)),
        None if padding_limit is None else (padding_limit.VR, int(padding_limit.value)),
        _optional_element_state(dataset, "RescaleIntercept"),
        _optional_element_state(dataset, "RescaleSlope"),
        _optional_element_state(dataset, "RescaleType"),
        _optional_element_state(dataset, "LossyImageCompression"),
        _optional_element_state(dataset, "LossyImageCompressionRatio"),
        _optional_element_state(dataset, "LossyImageCompressionMethod"),
    )


def _verify_derived_roundtrip(
    candidate: LoadedDicom,
    expected_dataset: Dataset,
    expected_array: np.ndarray,
    source_instance_uid: str,
) -> None:
    if candidate.decoder.transfer_syntax_uid != str(ExplicitVRLittleEndian):
        _reject("derived candidate is not Explicit VR Little Endian")
    if candidate.domain != Domain(
        int(expected_dataset.BitsStored), int(expected_dataset.PixelRepresentation)
    ):
        _reject("derived candidate changed the receiver domain")
    if candidate.padding != _parse_padding(expected_dataset, candidate.domain):
        _reject("derived candidate changed the receiver padding state")
    if _receiver_metadata_state(candidate.dataset) != _receiver_metadata_state(
        expected_dataset
    ):
        _reject("derived candidate changed required receiver metadata")
    if not np.array_equal(candidate.array, expected_array):
        _reject("decoded derived pixels differ from the intended stego array")

    if str(candidate.dataset.SOPInstanceUID) != str(expected_dataset.SOPInstanceUID):
        _reject("derived SOP Instance UID did not round trip")
    if str(candidate.dataset.SeriesInstanceUID) != str(expected_dataset.SeriesInstanceUID):
        _reject("derived Series Instance UID did not round trip")
    if str(candidate.dataset.file_meta.MediaStorageSOPInstanceUID) != str(
        candidate.dataset.SOPInstanceUID
    ):
        _reject("derived file-meta and dataset instance UIDs disagree")
    image_type = _multi_text(candidate.dataset.ImageType, "ImageType")
    if len(image_type) < 2 or image_type[:2] != ("DERIVED", "SECONDARY"):
        _reject("derived ImageType did not round trip")
    if _required_text(candidate.dataset, "DerivationDescription") != _required_text(
        expected_dataset, "DerivationDescription"
    ):
        _reject("derived description did not round trip")
    for keyword in ("ContentDate", "ContentTime"):
        if _optional_element_state(candidate.dataset, keyword) != (
            _optional_element_state(expected_dataset, keyword)
        ):
            _reject(f"derived {keyword} policy did not round trip")

    references = getattr(candidate.dataset, "SourceImageSequence", None)
    if not isinstance(references, Sequence) or len(references) != 1:
        _reject("derived source reference did not round trip")
    reference = references[0]
    if (
        _required_uid(reference, "ReferencedSOPClassUID") != str(CTImageStorage)
        or _required_uid(reference, "ReferencedSOPInstanceUID")
        != source_instance_uid
    ):
        _reject("derived source reference is inconsistent")

    if any(keyword in candidate.dataset for keyword in _SERIES_EXTREMA):
        _reject("single-instance writer retained unverified series extrema")
    _validate_actual_extrema(candidate.dataset, candidate.array)
    for current, _ in _iter_datasets(candidate.dataset):
        if any(tag in current for tag in _SIGNATURE_TAGS):
            _reject("invalidated signature or MAC material remains")


def _cleanup_temporary(path: Path | None) -> OSError | None:
    if path is None or not path.exists():
        return None
    try:
        path.unlink()
    except OSError as exc:
        return exc
    return None


def _write_loaded_dicom(
    loaded: LoadedDicom,
    destination_path: str | os.PathLike[str],
    stego: np.ndarray,
    *,
    overwrite: bool,
) -> Path:
    destination = _destination_path(
        loaded.source_path, destination_path, overwrite
    )
    derived = _prepare_derived_dataset(loaded, stego)
    expected = np.ascontiguousarray(
        stego,
        dtype=np.int16 if loaded.domain.pixel_representation else np.uint16,
    )

    temporary: Path | None = None
    failure: Exception | None = None
    published = False
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        temporary = Path(name)
        os.close(descriptor)
        derived.save_as(
            temporary,
            implicit_vr=False,
            little_endian=True,
            enforce_file_format=True,
            overwrite=True,
        )
        candidate = load_dicom(temporary)
        _verify_derived_roundtrip(
            candidate,
            derived,
            expected,
            str(loaded.dataset.SOPInstanceUID),
        )

        if overwrite:
            os.replace(temporary, destination)
        else:
            # A same-directory hard link provides an atomic no-clobber publish:
            # if another writer created destination, this operation fails rather
            # than replacing it.  Unsupported filesystems fail closed.
            os.link(temporary, destination)
        published = True
    except Exception as exc:
        failure = exc

    cleanup_failure = _cleanup_temporary(temporary)
    if failure is not None:
        if cleanup_failure is not None:
            raise DicomWriteError(
                "derived write failed and temporary-file cleanup also failed",
                destination_published=published,
                destination_path=destination if published else None,
                temporary_path=temporary,
            ) from failure
        if isinstance(failure, IchanError):
            raise failure
        raise IchanError(
            "E_DICOM",
            "derived serialization, verification, or atomic publication failed",
        ) from failure
    if cleanup_failure is not None:
        raise DicomWriteError(
            "derived destination was published, but temporary-file cleanup failed",
            destination_published=published,
            destination_path=destination if published else None,
            temporary_path=temporary,
        ) from cleanup_failure
    if not published:
        raise IchanError("E_INTERNAL", "derived destination was not published")
    return destination


def write_derived_dicom(
    source_path: str | os.PathLike[str],
    destination_path: str | os.PathLike[str],
    stego: np.ndarray,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a verified derived CT object without modifying the source file."""

    loaded = load_dicom(source_path)
    return _write_loaded_dicom(
        loaded, destination_path, stego, overwrite=overwrite
    )


def embed_dicom(
    source_path: str | os.PathLike[str],
    destination_path: str | os.PathLike[str],
    payload: bytes,
    *,
    overwrite: bool = False,
) -> Path:
    """Embed into one loaded snapshot, verify a derived file, then publish it."""

    loaded = load_dicom(source_path)
    stego = embed(loaded.array, payload, loaded.domain, loaded.padding)
    return _write_loaded_dicom(
        loaded, destination_path, stego, overwrite=overwrite
    )


def extract_dicom(path: str | os.PathLike[str]) -> bytes:
    """Extract a B1 payload from accepted received CT stored values."""

    loaded = load_dicom(path)
    return extract(loaded.array, loaded.domain, loaded.padding)


__all__ = [
    "DecoderMetadata",
    "LoadedDicom",
    "DicomWriteError",
    "MAX_DECLARED_PIXEL_BYTES",
    "MAX_DICOM_FILE_BYTES",
    "SUPPORTED_TRANSFER_SYNTAXES",
    "embed_dicom",
    "extract_dicom",
    "load_dicom",
    "write_derived_dicom",
]
