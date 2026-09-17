# BASMEDSecure and ICHAN-DH Presentation Package V1

This repository presents two connected stages of a data-hiding study for medical images:

1. **BASMEDSecure**, the published logistic-regression-guided adaptive LSB method that motivates the investigation.
2. **ICHAN-DH**, the proposed correctness-first method for restricted CT DICOM stored values.

The package is designed for a research-supervisor discussion. It explains the research direction, mathematical method, implementation artifacts, evidence boundaries, and remaining work. It is not a completed experimental report.

## Central research objective

The objective is to transform an underspecified adaptive data-hiding concept into a deterministic, receiver-reconstructible, and testable protocol for CT DICOM stored values, while making every correctness and security claim explicit.

## Read this first

| Order | Document | Purpose |
|---:|---|---|
| 1 | [Supervisor briefing](SUPERVISOR_BRIEFING.md) | Follow the speaking order and identify the decisions to request. |
| 2 | [BASMEDSecure presentation](basmedsecure/README.md) | Understand the original method, reported results, and observed limitations. |
| 3 | [ICHAN-DH presentation](ichansecure/README.md) | Understand the proposed mathematical correction and restricted CT scope. |
| 4 | [Research workflow](ichansecure/assets/research_workflow.mmd) | Review the complete gate sequence and current research position. |
| 5 | [BASMEDSecure notebook](basmedsecure/code.ipynb) | Inspect the disclosed repaired baseline workflow when implementation detail is needed. |
| 6 | [ICHAN-DH notebook](ichansecure/code.ipynb) | Inspect the concise implementation walkthrough when implementation detail is needed. |

## Evidence labels

For individual equations, pixel calculations, and explicitly defined percentage comparisons, read the [pixel-level comparison of reference DE, BASMEDSecure, and ICHAN-DH](comparison/README.md). It includes editable Mermaid diagrams and a complete one-byte analytical example, not experimental results.

The presentation uses the following labels to prevent planned work from being presented as completed evidence.

| Label | Meaning |
|---|---|
| **Paper report** | A statement reported by BASMEDSecure and not independently reproduced here. |
| **Repository observation** | A fact obtained by static inspection of the supplied files. |
| **Mathematical claim** | A result derived under explicit assumptions in the ICHAN-DH specification. |
| **Prepared artifact** | Code, a notebook, or a diagram that exists but has not necessarily been executed. |
| **Planned experiment** | A test that still requires researcher execution and recorded outputs. |

## Side-by-side summary

| Dimension | BASMEDSecure | ICHAN-DH |
|---|---|---|
| Image domain | Described and evaluated mainly as 8-bit grayscale intensity data | Integer CT stored values with declared `BitsStored` and signedness |
| Pixel grouping | Logistic regression trained on deterministic intensity labels | Direct deterministic native-domain partition |
| Embedding profiles | 1/0/0, 2/1/0, or 3/2/1 bits by predicted class | Same ordered profiles, reduced by a safety guard when required |
| Receiver state | External per-position key array | Header and body schedule reconstructed from the stego array and metadata |
| Payload endpoint | Implied by the key array | Explicit 64-bit payload length in a fixed 17-byte header |
| Integrity indicator | Not specified | CRC32 for accidental-error detection only |
| Padding handling | Not specified | Explicit padding set excluded from safe replacement blocks |
| Main correctness target | Not formally stated | Conditional exact payload recovery |
| Cover recovery | Claimed by extraction pseudocode but not supported by LSB replacement | Explicitly not claimed |
| Current evidence | Paper-reported PSNR and SSIM; local reproduction unexecuted | Proof specification and source prepared; experimental results pending |

## Repository structure

```text
presentation/
|-- README.md
|-- SUPERVISOR_BRIEFING.md
|-- basmedsecure/
|   |-- README.md
|   |-- code.ipynb
|   `-- assets/
|       |-- basmedsecure_flow.mmd
|       |-- provenance/
|       `-- source/
`-- ichansecure/
    |-- README.md
    |-- code.ipynb
    `-- assets/
        |-- embedding_flow.mmd
        |-- extraction_flow.mmd
        |-- evaluation_flow.mmd
        |-- research_workflow.mmd
        |-- reference/
        `-- source/
```

The `provenance` folder preserves the supplied BASMEDSecure paper, draw.io JSON, local prototype, and legacy notebook. The `source` folders contain the code imported by the presentation notebooks. The `reference` folder contains the detailed ICHAN-DH specifications and gate records.

Copied provenance and reference artifacts are preserved byte for byte and may retain their original punctuation. All newly authored presentation prose and diagrams follow the no-em-dash rule.

## Notebook use in Google Colab

Upload or clone the complete repository before opening either notebook. Do not upload only `code.ipynb`, because each notebook imports its corresponding `assets/source` tree.

In a fresh Colab runtime, change the working directory to the selected track before running its cells. Replace the placeholder repository name with the actual clone directory.

```python
%cd /content/<repository-name>/presentation/basmedsecure
```

or

```python
%cd /content/<repository-name>/presentation/ichansecure
```

Use a separate fresh runtime for each notebook. The current implementation is CPU-based NumPy code. Selecting a T4 runtime does not establish or provide GPU acceleration.

## Current research status

- Gates 1 to 4 have established the frozen scope, B1 mathematical contract, accepted flowcharts, and canonical source package.
- Gate 5 has a prepared verification notebook, but it has not been executed and its latest static-review corrections remain pending.
- Gate 6 dataset analysis and Gate 7 interpretation have not started.
- No empirical superiority, clinical safety, confidentiality, authentication, robustness, or publication-tier claim is made.

## Research workflow

The study follows two controlled workflows.

### Workflow A: reproducible baseline

1. Preserve the original paper and local artifacts.
2. State all operational assumptions needed to run the method.
3. Implement the disclosed repaired BASMEDSecure baseline.
4. Record the required external map and its overhead.
5. Evaluate it only on matched 8-bit inputs and identical payloads.

### Workflow B: correctness-first proposal

1. Define the stored-value domain and padding semantics.
2. Build a self-describing payload header.
3. Reserve safe header carriers.
4. Compute guarded adaptive body capacity.
5. Embed and extract through identical deterministic traversal.
6. Verify internal correctness on controlled fixtures.
7. Evaluate distortion, payload recovery, overhead, rejection behavior, and runtime on approved datasets.

The complete diagram is available in [Mermaid format](ichansecure/assets/research_workflow.mmd).

## Presentation rule

Present BASMEDSecure as the starting point, ICHAN-DH as the proposed correction, and all numerical ICHAN-DH outcomes as pending until the notebooks have been executed and their outputs have been reviewed.
