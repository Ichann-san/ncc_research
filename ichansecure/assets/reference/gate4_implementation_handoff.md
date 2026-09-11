# Gate 4 Implementation Handoff

Date: 2026-09-06  
Status: **four-role static review complete; researcher accepted progression to Gate 5 in the conversation; acceptance recorded on 2026-09-10; runtime behavior remains unverified**  
Authority: [operative B1 mathematical contract](mathematical_specification.md#iii-approved-b1-contract-for-gate-3) and [accepted Gate 3 flows](gate3/README.md)  
Execution boundary: no project Python module, notebook, import, test, package installation, DICOM round trip, or experiment was executed for this handoff.

## A. Scope and package boundary

Gate 4 translates the approved B1 state machine into one package intended for import under [`src/ichan_secure`](../src/ichan_secure). The implementation remains a research artifact that has completed four-role static review and was accepted by the researcher for progression to Gate 5. Importability and behavior still require researcher-run evidence. It does not establish authentication, confidentiality, steganographic undetectability, robustness, cover reversibility, clinical preservation, complete DICOM conformance, performance improvement, or generalization.

The current package separates four responsibilities:

| Module | Implemented responsibility | Deliberate boundary |
|---|---|---|
| [`core.py`](../src/ichan_secure/core.py) | B1 stored-value domain, padding state, header schedule, raw/byte capacity, framing, embedding, and extraction | Pure two-dimensional integer-array protocol; no file I/O or security primitive |
| [`baseline.py`](../src/ichan_secure/baseline.py) | Disclosed, repaired unsigned 8-bit BASMEDSecure reproduction | Requires an external ordered depth map; not B1, DICOM support, or cover recovery |
| [`metrics.py`](../src/ichan_secure/metrics.py) | Stored-value distortion, payload-recovery, and direct map-cost records | Descriptive metrics only; no security or clinical interpretation |
| [`dicom_io.py`](../src/ichan_secure/dicom_io.py) | Restricted CT loading, decoder provenance, derived-object construction, decode-after-save verification, and conditional publication | CT Image Storage only; not general DICOM support or complete CT IOD conformance |
| [`__init__.py`](../src/ichan_secure/__init__.py) | Small public B1 array interface | Optional DICOM, baseline, and SSIM dependencies are not loaded by the core import |

Dependency declarations are in [`pyproject.toml`](../pyproject.toml). NumPy is required; pydicom, scikit-learn, and scikit-image are separated into optional groups. The reproduction baseline is pinned to scikit-learn 1.7.2 so its fitted-model behavior is not silently changed by a later dependency release. This pin is an implementation reproducibility decision, not evidence that the baseline has executed successfully. See the official [`LogisticRegression` reference](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html) and [scikit-image metrics reference](https://scikit-image.org/docs/stable/api/skimage.metrics.html).

## B. Interface-to-proof traceability

| Implemented interface | Contract or proof owner | Implementation obligation represented | Evidence still required |
|---|---|---|---|
| `Domain`, `validate_array` | B1.1; B1-P5 | Enforce `BitsStored` 2--16, signedness, two-dimensional integer arrays, observed range, and a dtype that represents the complete declared domain | Accepted/rejected domain matrix and signed/unsigned boundary cases |
| `PaddingSpec` | B1.3--B1.5; B1-P1--P3 | Preserve absent/singleton/range state; reject reversed or incomplete metadata; test aligned blocks against the declared padding set | Empty, singleton, range-edge, reversed, and out-of-domain cases |
| `classify_value`, `classify` | B1.2 | Compute normalized stored-code strata using exact integer comparisons | Exhaustive small domains and threshold-boundary vectors |
| `replacement_block`, `guarded_depth`, `replace_bits` | B1.3, B1.5, B1.9; B1-P2--P3 | Define aligned blocks, select the largest safe depth, and replace rank-code bits without embedding an implicit padding check in the low-level primitive | Block endpoints, signed extrema, stratum thresholds, and caller-guard checks |
| `header_schedule`, `HeaderSchedule` | B1.4; B1-P1 | Return the first 136 eligible row-major carriers `J` and variable suffix boundary `beta` | Empty-padding reduction, skipped carriers, `beta=N`, and insufficient-carrier rejection |
| `capacity`, `CapacityReport`, `select_profile` | B1.6--B1.7; B1-P4, B1-P7 | Separate raw slots, usable byte capacity, tail bits, fixed-profile reserved-prefix opportunity cost, and minimal byte-feasible profile | Raw capacities 7/8/9, equal profiles, exact fit, one-byte overflow, and original-cover cost interpretation |
| `crc32`, `build_header`, `parse_header`, `frame`, `unframe` | B1.8 | Implement the 17-byte `ICHS` version-1 header and payload-only, zlib-compatible CRC-32 wire value | Golden vectors, offsets, byte order, malformed fields, truncated frame, and mismatch rejection |
| `embed` | B1.4--B1.9; B1-P1--P5; [embedding flow](gate3/01_embedding.mmd) | Reject capacity before copying, write header bits only at `J`, traverse the body from `beta`, advance over zero-depth positions, and return only the stego array | Exact/partial chunks, immutable cover, range/padding invariants, and no-map round trips |
| `extract` | B1.4--B1.10; B1-P1--P5; [extraction flow](gate3/02_extraction.mmd) | Reconstruct `J`, `beta`, capacity, and profile; bound the untrusted length before allocation; recover exactly `8L` bits; compare the payload checksum | Sender/receiver profile grid, malformed header, oversized length, checksum mismatch, and exact payload equality |
| `load_dicom`, `LoadedDicom`, `DecoderMetadata` | B1-P6; Section III-F; Gate 3 input branches | Restrict input to CT Image Storage; validate file-meta identity, one 16-bit-allocated MONOCHROME2 frame, stored-value metadata, padding, extrema, lifetime-lossy state, bounded element audit, transfer-syntax allowlist, and declared/encoded preflight limits; return an independent read-only array plus receiver state and decoder provenance | Accepted/rejected CT fixtures for every branch, decoder availability, signed/unsigned arrays, padding variants, exact extrema, limit boundaries, and recorded provenance |
| `write_derived_dicom`, `DicomWriteError` | B1-P6; Section III-F; [embedding output boundary](gate3/01_embedding.mmd) | Reload and validate the source, require exact source/stego padding-membership agreement, preserve receiver reconstruction state, prepare a separate derived object, serialize and decode-verify in the destination directory, and publish conditionally; distinguish a prepublication failure from a committed destination followed by cleanup failure | Source/destination alias cases, padding-membership rejection, receiver-state equality, authorized overwrite/no-clobber paths, serialization failures, cleanup failures before/after publication, round-trip equality, and metadata inspection |
| `embed_dicom`, `extract_dicom` | B1-P5--P6; Gate 3 embedding/extraction flows | Compose the CT boundary with the canonical array `embed` or `extract` functions without exposing a separate DICOM-specific embedding algorithm | End-to-end accepted-file fixtures and all conditional-corollary premises |
| `embed_baseline`, `extract_baseline`, `BaselineResult` | Historical C03--C20 and disclosed Workflow 1 repairs | Fit once per unsigned `uint8` cover, expose target/predicted counts and fit state, use byte-feasible predicted-label capacity, and retain the ordered external map including zero and final partial widths | Dependency/version, class-absence, convergence, profile-boundary, map-validation, and recovery cases |
| `distortion_metrics`, `recovery_metrics`, `direct_map_cost` | Historical C23--C24 under the B1 domain; [future evaluation flow](gate3/03_evaluation.mmd) | Use the declared stored-value span, disclose unavailable SSIM/BER states, and distinguish direct four-symbol map cost from a complete serialized cost | Controlled arrays, declared SSIM parameters, dependency behavior, empty/mismatched payloads, and map accounting |

`IchanError` carries a stable rejection `code` and no partial payload/stego result. Concrete exception-to-notebook presentation remains a Gate 5 concern. `CapacityReport.reserved_raw_slots` is meaningful only for the original cover used to compute the report; header carriers need not preserve their strata, so it must not be recomputed from a stego array and interpreted as the original prefix opportunity cost.

## C. State and claim boundaries

- `embed` returns a stego array and no external per-pixel depth map. It is not side-information-free: extraction still requires the same domain, shape, traversal convention, protocol constants, and immutable `PaddingSpec`.
- `extract` is intended to provide exact payload recovery only under the intact-array assumptions in B1-P5. It does not recover the original cover.
- CRC-32 covers the payload body only. `E_CRC` means payload-checksum mismatch, not authentication failure, tamper proof, or complete corruption detection.
- `replace_bits` is intentionally a low-level rank-code operation. Callers must establish the padding/stratum guard before using it as an embedding transformation.
- The baseline's `direct_map_bits` and `direct_map_cost` report `2V` bits for a direct four-symbol map. They do not report Python object memory, map entropy, protection, endpoint framing, or complete wire size.
- MSE, PSNR, SSIM, modified fraction, and maximum stored-value change are descriptive numerical measures. They cannot establish security, robustness, or diagnostic preservation.

### CT file-interface profile represented in source

`dicom_io.py` narrows the current input profile to CT Image Storage with `Modality=CT`, one two-dimensional `MONOCHROME2` frame, one sample per pixel, `BitsAllocated=16`, `BitsStored` 2--16, consistent `HighBit` and signedness, integer Pixel Data, and required rescale fields that are validated but never applied. Its explicit transfer-syntax allowlist contains Implicit VR Little Endian, Explicit VR Little Endian, and RLE Lossless. JPEG-family, big-endian, deflated, and other encodings are outside this version's source profile. The adapter rejects `LossyImageCompression="01"`; absence of that attribute is not evidence that a file has never undergone lossy processing.

The bounded element audit rejects private or unknown elements, `UN` values, curve/overlay groups, nested or noninteger pixel data, and an enumerated set of unsupported pixel-dependent structures. It does not establish that every public DICOM element has been audited. The source applies a 512-MiB file-size preflight limit (`MAX_DICOM_FILE_BYTES`) and a 256-MiB declared native-frame or encoded-RLE-payload limit (`MAX_DECLARED_PIXEL_BYTES`). These checks do not bound decoder peak memory. They are conservative research restrictions, not DICOM requirements, and must be counted as eligibility exclusions in later evaluation.

For RLE Lossless input, byte-level preflight first applies the encoded-size cap, then restricts the Basic Offset Table length to zero or four bytes and validates the extent of exactly one frame fragment before invoking the pydicom parsers. Parser-level checks consume the Basic Offset Table before counting actual fragments, accept only an empty offset list or the single offset zero, reject auxiliary offset/length tables, and require exactly one actual fragment for the declared one-frame object. Decoding additionally disables excess-frame acceptance. These are source-level rejection rules whose accepted and rejected paths still require fixtures.

`LoadedDicom.array` is an independent native-endian, C-order, read-only NumPy snapshot. `LoadedDicom.dataset` remains mutable for pydicom use, so callers must not treat the wrapper as an immutable or privacy-sanitized copy of the full dataset. The `repr` suppression of the dataset, array, and path reduces accidental display but does not establish de-identification or data protection.

Before constructing a derived object, the direct writer compares source and supplied-stego padding membership in bounded blocks. The derived-output path then deep-copies the accepted source dataset, replaces integer Pixel Data, verifies preservation of receiver-relevant domain, padding, rescale, and loss-history state, assigns new instance and project-policy series identities, marks the image `DERIVED`/`SECONDARY`, records a source reference, and removes source-instance creation fields. Its derivation description identifies research tooling and explicitly avoids treating file generation as evidence for algorithm embedding, security, or clinical safety. It emits `ContentDate` and `ContentTime` as permitted zero-length values rather than retaining source-pixel timestamps. It also removes encapsulation-only fields, series extrema, trailing padding, and recursively located signature/MAC attributes. Image extrema are recreated from the candidate array with the signed or unsigned VR required by `PixelRepresentation`.

The writer serializes canonical Explicit VR Little Endian output to a uniquely named same-directory temporary file, reloads that file through the same restricted loader, and compares decoded pixels and receiver state before checking identities, source reference, zero-length content-time policy, extrema, and signature removal. It then attempts an overwrite-authorized replacement or no-clobber hard-link publication. A `DicomWriteError` exposes `destination_published`, `destination_path`, and `temporary_path`; when `destination_published=True`, the verified destination exists and must be treated as committed even though temporary-file cleanup failed. Filesystem atomicity and cleanup behavior remain conditional on platform/filesystem support and require later fixtures; crash durability and network-filesystem guarantees are not claimed.

The DICOM module imports only when pydicom 3.0.2 is available. Its code-level design is informed by the current [DICOM CT Image Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.8.2.html), [DICOM common image metadata](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.7.6.html), [CT Image Storage table](https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_b.5.html), and pydicom [pixel-data guide](https://pydicom.github.io/pydicom/stable/guides/user/working_with_pixel_data.html) and [`set_pixel_data` reference](https://pydicom.github.io/pydicom/stable/reference/generated/pydicom.pixels.utils.set_pixel_data.html). These references justify the implementation contract; they are not substitutes for file-level evidence.

## D. Static corrections and later evidence

The following rows describe source corrections observed by inspection. "Later fixture" is an evidence requirement, not a reported result.

| Concern closed in source | Static implementation state | Required Gate 5 fixture |
|---|---|---|
| Direct-writer padding guard | `_preserves_padding_membership` compares source and candidate membership in the declared padding set before derived-object construction, using bounded blocks rather than one full-image mask | Reject a same-shape candidate that changes membership; accept candidates that preserve absent, singleton, and range-padding membership |
| Loss-history detail without a matching flag | Ratio or method fields are rejected when `LossyImageCompression` is absent or is not `"01"`; the `"01"` lifetime-lossy state is itself outside the accepted profile | Cover absent/`"00"`/`"01"` flags with absent and present ratio/method combinations |
| Source-to-derived receiver state | Preparation and post-reload checks compare the domain-defining fields, padding VR/values, rescale fields, and loss-history fields needed by the restricted receiver | Mutate each receiver-state field independently and demonstrate deterministic rejection; retain unchanged-state round trips |
| RLE framing and preflight limits | The encoded cap and fixed-size Basic Offset Table/fragment-extent checks precede parser calls. Basic offsets are then parsed separately from actual fragments; only `[]` or `[0]` is accepted, auxiliary offset/length tables are rejected, and one actual fragment is required. File and declared/encoded-size limits are preflight limits, not decoder-memory guarantees | Exercise empty/zero/nonzero Basic Offset Tables, malformed lengths/extents, extra fragments, auxiliary tables, exact/over-limit boundaries, and decoder-resource failure |
| Publication followed by cleanup failure | `DicomWriteError.destination_published` distinguishes a verified committed destination from a failure before publication; destination and temporary paths are structured attributes rather than routine message text | Inject failures before publication and during cleanup after no-clobber publication; assert destination existence and the reported committed state |
| Derived content timestamps | Source instance-creation fields are removed; `ContentDate` and `ContentTime` are emitted as zero-length values and compared after reload | Use source objects with present, absent, and populated time fields; inspect the reloaded derived metadata |
| Image extrema truth and VR | Existing image extrema are validated against decoded stored values and against signed/unsigned VR; derived extrema are recreated from the candidate array using `SS` or `US` according to `PixelRepresentation`. Unverified series extrema are removed | Cover signed/unsigned exact extrema, stale values, wrong VR, partial source pairs, and post-reload derived values; inspect absence of series extrema |

## E. Review state

| Role | Current result |
|---|---|
| Scientist | **PASS for researcher review:** no remaining Critical or High static blocker within Gate 4 scope after final source re-read |
| Software Engineer | **PASS:** no remaining Gate 4 static blocker in `dicom_io.py` after the final D-08--D-10 corrections; residual file, decoder-resource, and filesystem conditions are deferred to fixtures |
| Writer | **PASS:** interfaces, terminology, status language, and claim boundaries are synchronized with the stable source and substantive reviews |
| Coordinator | **PASS:** no remaining static blocker identified; package links and unchanged legacy-source hashes were checked without importing or executing project code |

Gate 4 establishes source-level traceability and static consistency with the frozen B1 contract. No Python module, notebook, DICOM fixture, decoder, serializer, metric, or filesystem publication path was executed; therefore, these verdicts are not runtime, interoperability, performance, clinical-safety, or empirical evidence. Those claims remain contingent on researcher inspection and the Gate 5 execution campaign.

## F. Gate handoff

Gate 3 is researcher-accepted and authorized this implementation work. The researcher subsequently accepted Gate 4 progression and selected Colab for execution; this conversational approval is recorded on 2026-09-10. Gate 5 preparation is now authorized. See the [Colab run guide](gate5_colab_run_guide.md) for the notebook handoff. No researcher-run fixed-test record has been supplied to the assistant, and no runtime success is inferred from this approval.

The Gate 5 decision must therefore distinguish three facts:

1. source files may implement the approved contract;
2. static review may find the source structurally consistent with that contract; and
3. only later execution can establish importability and observed behavior.

Any behavior-changing defect returns to Gate 2 and its downstream diagrams under the approved change-control rule. A code-only correction that preserves the contract remains in Gate 4 and must be covered by the later Gate 5 checks.
