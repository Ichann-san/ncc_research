# ICHAN-DH Gate Progress and BASMEDSecure Comparison

Status date: 2026-09-10  
Manuscript name: `ICHAN-DH`  
Repository codename: `ICHAN-Secure`

Gate 2 normative source: [`mathematical_specification.md`](mathematical_specification.md)  
Approved design record: [`plans/2026-09-04-gate2-guarded-synchronization-design.md`](plans/2026-09-04-gate2-guarded-synchronization-design.md)
Adversarial review: [`gate2_adversarial_review_2022_2026.md`](gate2_adversarial_review_2022_2026.md)

## How progress is measured

Gate progress records researcher acceptance, not effort spent or probability of correctness. Gates 1–3 were explicitly approved in the conversation. The researcher subsequently accepted progression from the prepared Gate 4 package to the Colab algorithm notebook; that approval is recorded here on 2026-09-10. The operative B1 contract remains controlling. Acceptance does not imply tests were run, every proof was independently verified, or code is correct.

No Python module or notebook has been executed by the assistant. All implementation and experimental statuses therefore remain unverified.

## Gate dashboard

| Gate | Acceptance progress | State | Evidence completed | Remaining decision or evidence |
|---|---:|---|---|---|
| 1. Scope and evidence architecture | 100% | **Accepted** | Approach A; two-workflow design; proposal framework; claim categories; seven approval gates; ICHAN-DH naming and bounded claims | Reopen only if scope, title, or evidence standard changes |
| 2. Mathematical specification and proof ledger | 100% researcher accepted | **Accepted; B1 reconciliation documented** | Operative B1 equations, pseudocode, seven dependency proofs, byte-capacity distinction, CRC wire contract, and conditional CT file boundary; original candidate retained as historical | Implementation, codec/serialization checks, and independent researcher proof-by-proof verification remain distinct evidence obligations |
| 3. Flowcharts | 100% researcher accepted | **Accepted** | Separate embedding, extraction, and future-evaluation Mermaid scripts; equation traceability; four-role static review; explicit researcher approval | Rendering remains untested; reopen only for a contract/flow change |
| 4. Canonical package | 100% researcher accepted | **Accepted for progression; execution unverified** | B1 core, disclosed baseline, metrics, CT I/O, exports and package metadata written; source-level file-boundary corrections incorporated and statically reviewed | Imports, dependency resolution, and runtime evidence remain deferred to researcher-run checks |
| 5. Algorithm notebook | 0% accepted | **Initial bounded Colab notebook written** | 22 unexecuted cells, 14 named check groups, source/environment recording, synthetic diagnostics and CT subset, run guide, explicit pending obligations | Complete static review, then researcher execution, debugging, remaining in-scope campaign implementation, and explicit acceptance |
| 6. Analysis notebook and dataset protocol | 0% accepted | Planned | Candidate 2022-2026 datasets, matched-comparison principles, metrics, and patient-level split rules are documented | Create `02_ichan_analysis.ipynb`; freeze manifests and payload protocol; run matched datasets; visualize capacity, distortion, failures, runtime, and uncertainty |
| 7. Result freeze and claim audit | 0% accepted | Planned | Claim/evidence categories and publication tracks are defined | Freeze verified tables/figures; audit every claim; assign final venue only after evidence exists; authorize proposal/manuscript writing |

Four of seven gates are researcher-accepted: **57.1%** by gate count. Gate 5 remains open. This is not scientific completion, implementation correctness, or publication readiness.

## Progress compared with BASMEDSecure

| Gate | BASMEDSecure baseline evidenced in the local paper/code | Current ICHAN-DH advance | Honest current gap |
|---|---|---|---|
| 1 | The local work combines an adaptive-LSB idea with broad security/reversibility language, but the supplied prototype and evaluated claims do not share an explicit evidence boundary | Separates reproduction from correction; distinguishes mathematical, implementation, experimental, external-source, and researcher evidence; narrows CRC32 and publication claims | Governance is improved, but it does not itself improve embedding performance |
| 2 | Fixed 8-bit labels, three cases, sequential replacement, and an external depth sequence are present; no complete formal correctness argument resolves sender/receiver state, native DICOM range, framing, padding, or cover recovery | Approved B1 explicitly reconstructs header carriers, body depths and profile; preserves declared padding membership under the model; separates raw slots from byte payload capacity | Proof is conditional on the intact array and receiver state; the DICOM corollary requires later file-boundary evidence; no measured superiority |
| 3 | The printed algorithm requires interpretation, and the local source disagrees internally about the key container and receiver state | Three researcher-accepted flows specify traversal, rejection ordering, file publication, and later evaluation | Diagram rendering remains untested; acceptance is design evidence only |
| 4 | One 8-bit demonstration file is available. At line 72, `key_array` is `{}`, but lines 106 and 109 call `.append()`, so the embedding path fails as supplied. DICOM I/O is not implemented | Canonical source implements shared B1 traversal, disclosed map-based reproduction, stored-range metrics, and restricted CT loading/derived publication with explicit failure outcomes | Source-level corrections are not execution evidence: imports, dependency resolution, round trips, runtime and measured advantage remain unverified |
| 5 | The demonstration uses one seeded random `uint8` matrix and prints equality/PSNR/SSIM; it has no fixed assertion campaign | An initial notebook now implements named checks for a bounded `ICHAN-TV1.1` subset, with literal expectations, a small-domain oracle, source/environment provenance and synthetic CT examples | Notebook cells are unexecuted; advanced obligations remain pending; no measured improvement or researcher-signed execution record exists |
| 6 | Evaluation in the supplied code fixes `data_range=255` and uses a single simulated matrix; no patient-level or external-dataset protocol is encoded | Matched-cover/payload comparison, native-range metrics, patient grouping, external heterogeneity, and side-information accounting are planned | No dataset has been acquired or analyzed, and no result or superiority claim is valid |
| 7 | The supplied paper's conclusions still require independent reproduction against the corrected interpretation | Claim-freeze rules prevent placeholders or planned metrics from becoming findings | ICHAN-DH has no verified results and is not ready for venue submission |

## Current risk movement

The scale follows the existing research brief: Low, Moderate, High, and Critical indicate impact on a stated research claim, not clinical patient risk.

| Risk area | BASMEDSecure grade | ICHAN-DH current grade | Target after relevant gates | Reason |
|---|---|---|---|---|
| Executability | Critical | High evidence gap | Reassess after user-run Gate 5 checks | Canonical replacement code is now written, but no import, installation, or test has been run |
| Exact extraction | Critical/High | Moderate residual design risk / High implementation evidence gap | Reassess after user-run Gate 5 checks | B1 design is accepted and manually reviewed; no implementation has been run |
| Native DICOM domain | High | Moderate bounded design risk / High interface evidence gap | Reassess after Gates 4–5 | B1 resolves the declared-padding invariant in the model; CT decoder, metadata and serialization behavior remain unverified |
| Side-information efficiency | Moderate | Moderate evidence risk | Reassess after Gate 6 | B1 has no external depth map, but its variable reserved span and fixed-profile opportunity cost must be measured separately from 136 header bits |
| Security overclaim | High | Low claim risk; no technical security provided | Low if wording remains bounded | CRC32 is limited to payload-checksum mismatch detection with a parsable header; confidentiality/authentication remain absent |
| Evaluation/generalization | High | High evidence gap | Moderate after Gate 6; reassess at Gate 7 | A stronger protocol exists on paper, but no real-DICOM experiment has run |
| Clinical safety | Not established | Not established | Outside current internal-correctness campaign | Neither project may claim diagnostic preservation without task/ROI or reader evidence |

## Improvement-level snapshot

| Improvement | Planned level | Current evidence status |
|---|---|---|
| Explicit reproduction corrections and claim boundaries | I1-I2 | Frozen and documented |
| Direct native-domain classification | I2 | Equations translated to canonical code; unexecuted |
| Self-describing payload frame and pre-mutation capacity checks | I3 | Shared core implementation written; unexecuted |
| Receiver-reconstructible adaptive embedding without uncounted external map | I3 | B1 dependency proofs and flowcharts prepared and manually reviewed; implementation unverified |
| Conservative native stored-value DICOM support | I3 | CT-only contract and padding-preservation argument specified; file-interface premises remain to be tested |
| Matched patient-level external evaluation | I2 evidence improvement | Protocol drafted; datasets not acquired or run |
| Authenticated, reversible, clinically validated, or post-quantum construction | I4 | Explicitly deferred; not part of the current correctness result |

## Current handoff

Gate 4 approval is recorded; Gate 5 preparation is authorized. Follow the [Colab run and read guide](gate5_colab_run_guide.md), with [the Gate 4 handoff](gate4_implementation_handoff.md) and [package guide](../src/ichan_secure/README.md) as interface references. The Scientist, Software Engineer, Writer, and Coordinator remain the four roles. The canonical source and legacy prototype/notebook remain unchanged by notebook preparation. No Python/import/test/notebook execution was performed. Earlier pre-acceptance Gate 2/3/4 notices are historical, not requests to repeat approval.
