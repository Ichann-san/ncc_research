# Supervisor Presentation Guide

## Meeting objective

Ask the supervisor to evaluate whether the correctness-first direction, restricted CT scope, comparison protocol, and planned evidence are sufficient for the next research stage.

Do not present ICHAN-DH as a completed security system. Its mathematical specification and source implementation are prepared, but experimental results are not yet available.

## Opening statement

> This research begins with an audit of BASMEDSecure, an adaptive LSB method that uses logistic regression to group image pixels. The audit shows that the research problem is larger than a local programming defect. A reproducible method also needs an exact receiver contract, a native CT stored-value model, explicit payload framing, padding-aware carrier selection, and bounded claims. I therefore propose ICHAN-DH as a correctness-first method. The current meeting is intended to review the research direction before dataset experimentation.

## Suggested 20-minute sequence

| Slide | Time | Content | Main message |
|---:|---:|---|---|
| 1 | 1 minute | Title and objective | This is a pre-results methodology and progress review. |
| 2 | 2 minutes | BASMEDSecure overview | Explain the three intensity groups and three adaptive LSB profiles. |
| 3 | 2 minutes | BASMEDSecure embedding and extraction | Show the Mermaid flow and identify the external key array. |
| 4 | 2 minutes | Paper-reported results | Report PSNR and SSIM only as values stated by the paper. |
| 5 | 2 minutes | Audit findings | Separate paper limitations, pseudocode ambiguity, and the local prototype defect. |
| 6 | 1 minute | Research question | State the conditional payload-recovery objective. |
| 7 | 3 minutes | ICHAN-DH method | Explain native strata, the header, guarded capacity, embedding, and extraction. |
| 8 | 2 minutes | Mathematical justification | Present the replacement block, safety guard, and P1 to P7 proof chain. |
| 9 | 1 minute | Correction matrix | Compare each BASMEDSecure limitation with its ICHAN-DH correction. |
| 10 | 1 minute | Current artifacts | Show the source package, notebooks, flowcharts, and evidence status. |
| 11 | 1 minute | Planned evaluation | Explain matched inputs, dataset grouping, metrics, and rejection evidence. |
| 12 | 2 minutes | Supervisor decisions | Ask for decisions on contribution, scope, comparison, and next milestone. |

## What to show

### BASMEDSecure

Use the [BASMEDSecure README](basmedsecure/README.md) and [flowchart](basmedsecure/assets/basmedsecure_flow.mmd).

Explain:

1. Pixels are labeled low, medium, or high using fixed intensity intervals.
2. Logistic regression is trained to predict those deterministic labels.
3. A payload-length condition selects one of three LSB profiles.
4. Embedding produces a stego image and an external key array.
5. Extraction depends on that key array.
6. The paper reports high cover-stego similarity, but does not report exact payload-recovery evidence.

### ICHAN-DH

Use the [ICHAN-DH README](ichansecure/README.md), [embedding flow](ichansecure/assets/embedding_flow.mmd), and [extraction flow](ichansecure/assets/extraction_flow.mmd).

Explain:

1. The algorithm operates on declared integer CT stored values.
2. Native-domain strata are computed with exact integer comparisons.
3. A fixed 17-byte header provides magic, version, payload length, and CRC32.
4. Header carriers avoid the declared padding set.
5. Body depths are reduced to the largest whole-block-safe depth.
6. The sender and receiver reconstruct the same body capacity and minimal feasible profile.
7. The central claim is conditional exact payload recovery.
8. The original cover is not recoverable from the stego array.

## Key comparison

| Question | BASMEDSecure | ICHAN-DH |
|---|---|---|
| How are pixels grouped? | Logistic regression predicts deterministic 8-bit labels | Direct native-domain integer rule |
| How does the receiver know bit depths? | External key array | Deterministic reconstruction |
| How is payload length known? | Implied by key-array endpoint | Explicit 64-bit length field |
| How is accidental corruption detected? | Not specified | Payload CRC32 |
| How is padding treated? | Not specified | Whole replacement blocks avoid padding |
| What recovery is claimed? | Pseudocode also lists cover-image output | Payload recovery only |
| What evidence exists now? | Paper-reported PSNR and SSIM | Specification and source, with experiments pending |

## Claims permitted now

- BASMEDSecure reports PSNR from 52.103 dB to 75.521 dB and SSIM from 0.9856 to 0.9999 in its tables.
- The supplied local BASMEDSecure prototype initializes `key_array` as a dictionary and later calls `.append`, which is a local execution defect.
- ICHAN-DH has an explicit B1 mathematical contract and a prepared source implementation.
- The proof target is conditional exact payload recovery under an intact channel and identical required metadata.
- The Gate 5 verification notebook still requires correction and researcher execution.

## Claims not permitted now

- ICHAN-DH has better PSNR, SSIM, capacity, or runtime than BASMEDSecure.
- ICHAN-DH is secure against steganalysis or active attackers.
- CRC32 provides authentication.
- The original cover image is recoverable.
- Diagnostic information is preserved.
- The method supports every DICOM object.
- GPU or quantum acceleration has been demonstrated.
- The research is ready for a specific journal quartile.

## Questions to ask the supervisor

1. Is conditional exact payload recovery, supported by a synchronized adaptive schedule, a sufficiently focused primary contribution?
2. Is the restricted CT stored-value profile appropriate for the first evidence campaign?
3. Should the initial comparison separate matched 8-bit baseline experiments from native CT characterization?
4. What level of clinical or task-based validation would be required before discussing diagnostic preservation?
5. Should the next milestone be limited to Gate 5 correction and execution before any dataset experiment begins?

## Likely questions and concise answers

### Why remove logistic regression?

The original training targets are determined directly by fixed thresholds on the same one-dimensional pixel value. Direct classification is exact, transparent, and does not add model-estimation uncertainty.

### Is ICHAN-DH reversible?

It is payload-recoverable under the stated assumptions, but it is not reversible with respect to the original cover. LSB replacement is non-injective.

### Is CRC32 a security mechanism?

No. It detects many accidental errors but does not authenticate the sender or resist intentional modification.

### Why does embedding and extraction appear repetitive?

The shared traversal is necessary. Correct extraction depends on the receiver reconstructing the same header schedule, boundary, capacity, profile, depths, bit order, and endpoint as the sender.

### Where are the results?

ICHAN-DH results are intentionally pending. The current artifacts establish the method and evidence protocol, not empirical superiority.

## Meeting close

> The immediate decision is whether the B1 method and evaluation design are scientifically adequate to proceed. If approved, the next step is to correct and execute Gate 5, preserve the complete verification record, and only then begin the matched dataset analysis.

## Optional implementation evidence

- [BASMEDSecure baseline notebook](basmedsecure/code.ipynb)
- [ICHAN-DH walkthrough notebook](ichansecure/code.ipynb)
- [Full ICHAN-DH gate workflow](ichansecure/assets/research_workflow.mmd)
