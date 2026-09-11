# Gate 5: Run and Read Guide

Prepared: 2026-09-10  
Status: researcher-run instructions; installation, notebook cells, figures, and file round trips have not been executed by the assistant.

## A. What you run

Open [`01_ichan_algorithm.ipynb`](../notebooks/01_ichan_algorithm.ipynb) in Google Colab and run its cells in order. You do not run `core.py`, `baseline.py`, `metrics.py`, or `dicom_io.py` separately: the notebook imports their functions. You do not need to run any research Python on your computer first.

The historical `basmedcesure.py` and `basmedsecure.ipynb` remain reference artifacts. Neither is a setup step or the current B1 execution entry point. The second notebook, `02_ichan_analysis.ipynb`, is not part of this handoff; dataset-wide experiments wait for Gate 6.

## B. Prepare on your computer

1. In `basmedsecure_research`, select **only** `pyproject.toml` and the `src` directory, and compress them into a ZIP using your file manager. A descriptive name is `ichan-dh-gate5-source.zip`.
2. Confirm the ZIP contains the package layout below. Do not rename `ichan_secure`, omit `__init__.py`, or upload individual modules instead of the package.
3. Open Google Colab and upload `notebooks/01_ichan_algorithm.ipynb` as the notebook. Keep the source ZIP available for the upload prompt in its setup section.

```text
ichan-dh-gate5-source.zip
  pyproject.toml
  src/
    ichan_secure/
      __init__.py
      core.py
      baseline.py
      dicom_io.py
      metrics.py
      README.md
```

**Do not include clinical data, credentials, `.venv`, caches, or unrelated projects.** Only install a source archive that you trust: package installation executes build tooling. The notebook's archive checks do not make untrusted Python code safe.

No local research output is needed. At this point you have a source ZIP and an unexecuted notebook, not experimental results.

## C. Run in Colab

Start with a fresh runtime. CPU execution is sufficient for the current NumPy/pydicom implementation. A T4 runtime can host it, but the notebook does not offload the algorithm to that GPU. Selecting a GPU runtime does not automatically use the accelerator. Colab runtimes are temporary; download important outputs before the runtime is deleted. See the [official Colab FAQ](https://research.google.com/colaboratory/faq.html).

| Order | Notebook work | Intended observable output when you execute |
|---|---|---|
| 1 | Read scope and setup instructions; upload source ZIP | Fresh working copy of the package |
| 2 | Install dependencies, then import and record the environment | Installation log, source hashes, versions, and a unique run directory |
| 3 | Domain, strata, wire format, bootstrap, and guard checks | Named check records plus intermediate values for inspection |
| 4 | Capacity, profile choice, embedding, extraction, and failure cases | Controlled round trips and expected-rejection records, not general correctness proof |
| 5 | Limits, baseline-map behavior, and metric examples | Descriptive values with explicit limits on their interpretation |
| 6 | Synthetic CT file-boundary examples | Separate source/derived fixture files and selected metadata checks |
| 7 | Review diagnostic plots and export the execution record | Downloadable evidence archive, including explicit pending obligations |

Run one code cell at a time during the first debugging session. Read the preceding mathematical explanation, inspect the output, and record any disagreement. Do not continue to interpret later outputs after an unexpected failure; they may depend on missing or stale state.

The setup uses the dependency declarations in [`pyproject.toml`](../pyproject.toml), including the frozen pydicom and scikit-learn versions. The declaration is not a complete dependency lock. Installation success and compatibility with the actual Colab Python/runtime must be observed, not assumed. If setup requests a restart, follow the notebook instructions; if the source or dependency set changes after imports, use a fresh runtime and start again.

## D. What the outputs mean

- A successful assertion records agreement for that named fixture. It is not a universal proof, dataset result, or automatic gate approval.
- An expected-rejection check succeeds only if the stated invalid input produces the specified error. An unexpected exception is a failure, not an exclusion to discard.
- A diagnostic figure illustrates synthetic stored values, capacities, or changes. It is not a publication result or a clinical image-quality assessment.
- A synthetic DICOM round trip provides evidence only for the file configuration exercised. The fixtures are not a complete CT IOD validation campaign.
- A pending case remains pending even when all implemented cases succeed. Advanced codec, metadata-mutation, resource-failure, and publication-failure obligations are tracked separately.

The notebook prepares an environment record and a verification record inside a unique run directory, together with generated diagnostics and synthetic fixtures. Inspect its final export section for the exact archive path. Save the executed notebook separately as well: its edited cells and outputs are part of your debugging record. The downloaded record alone does not capture every interactive notebook edit.

## E. If a cell fails

1. Stop normal execution and retain the error traceback and stable cell/check identifier.
2. Record the source ZIP/hash and environment information if setup reached that stage.
3. Retain the verification record already written in the run directory; follow the export instructions where the initialized state permits. If setup failed before recording began, save the installation output instead.
4. Send the relevant error and record for review. Do not alter expected values merely to obtain a successful check.
5. After a correction, use a fresh runtime for the full campaign. Keep the failed run separate; it remains part of the audit trail.

If a DICOM write raises `DicomWriteError`, inspect `destination_published`. A true value means publication occurred and cleanup failed; do not blindly retry as though no destination exists. All notebook DICOM inputs should be synthetic. The package does not de-identify patient metadata or authorize cloud use of real data.

## F. Reading order

1. [Research workflow](research_workflow.md): purpose and acceptance gates.
2. [Gate progress](gate_progress.md): current state and BASMEDSecure comparison.
3. [Mathematical specification](mathematical_specification.md): **operative B1 section first**; later candidate material is historical.
4. [Proof ledger](proof_ledger.md): assumptions and proof-to-check obligations.
5. [Gate 3 README](gate3/README.md), then embedding, extraction, and evaluation diagrams.
6. [Gate 4 handoff](gate4_implementation_handoff.md): implementation traceability and remaining interface checks.
7. [Package README](../src/ichan_secure/README.md): inputs, outputs, dependencies, and restrictions.
8. [Notebook README](../notebooks/README.md), this guide, then the algorithm notebook from the top.
9. [Data README](../data/README.md) **before Gate 6**, not as a prerequisite to synthetic Gate 5 fixtures. Its optional modality-shift source is historical/planned material, not authorization to expand the frozen CT scope.

## G. Researcher handoff

Gate 4 acceptance authorizes this notebook preparation; it does not establish runtime correctness. Gate 5 remains open until you inspect and execute the required checks, resolve failures and pending obligations, and explicitly approve the evidence. Gate 6 experiments do not begin automatically when a notebook finishes.
