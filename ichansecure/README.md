# ICHAN-DH

## 1. Overview

ICHAN-DH is the working name of the correctness-first adaptive data-hiding method developed from the BASMEDSecure audit. Its purpose is to define a sender and receiver that make identical decisions from a restricted CT DICOM stored-value array and shared metadata, without transmitting a per-pixel embedding-depth map.

The method retains the useful idea of unequal LSB depth by intensity region, but replaces learned threshold reproduction with an exact mathematical partition and adds explicit framing, capacity checks, padding safety, receiver reconstruction, and rejection behavior.

### Research question

Can an adaptive LSB data-hiding method for CT DICOM stored values provide conditional exact payload recovery through deterministic sender-receiver synchronization while preserving declared value, stratum, and padding constraints?

### Current evidence status

| Component | Status |
|---|---|
| Frozen B1 mathematical specification | Approved for research progress |
| Internal proof chain P1 to P7 | Manually reviewed under stated assumptions |
| Embedding, extraction, and evaluation flowcharts | Approved |
| Canonical Python package | Prepared and statically reviewed |
| Presentation walkthrough notebook | Prepared and unexecuted |
| Gate 5 verification notebook | Prepared but still requires corrections and execution |
| Dataset experiment | Not started |
| Experimental results | Not available |

## 2. Scope and required data

### A. Accepted research domain

The core algorithm operates on a two-dimensional integer array of decoded stored values. Let:

- $b \in \{2,\ldots,16\}$ be `BitsStored`;
- $s \in \{0,1\}$ be `PixelRepresentation`, where 0 is unsigned and 1 is signed;
- $d_{\min}=-s2^{b-1}$;
- $d_{\max}=2^b-1-s2^{b-1}$;
- $R=d_{\max}-d_{\min}=2^b-1$.

Every accepted sample satisfies

$$
x \in D_{b,s}=\{d_{\min},d_{\min}+1,\ldots,d_{\max}\}.
$$

This is a stored-value model. It does not classify Hounsfield units or displayed intensities, and it does not apply rescale slope or rescale intercept during embedding.

### B. Restricted DICOM file profile

The prepared adapter is intentionally narrower than general DICOM support. It accepts a restricted CT profile with conditions including:

- CT Image Storage;
- monochrome, single-frame, single-channel pixels;
- 16 allocated bits and 2 to 16 stored bits;
- signedness consistent with the decoded pixel representation;
- supported transfer syntax;
- required finite rescale intercept and slope;
- explicit rejection or output handling for the frozen lossy-history, overlay, curve, signature, MAC, and pixel-dependent policies.

The exact engineering policy is recorded in `assets/reference/gate4_implementation_handoff.md` and the copied `dicom_io.py` source.

### C. Other required inputs

| Input | Meaning |
|---|---|
| $X$ | Accepted two-dimensional integer stored-value array |
| $M$ | Secret payload as bytes |
| $\Pi$ | Declared padding set: empty, singleton, or inclusive interval |
| Traversal | Row-major order, fixed for sender and receiver |
| Metadata | At minimum, $b$, $s$, and identical padding semantics |

## 3. Mathematical method

### A. Deterministic native-domain strata

Translate each sample to a nonnegative coordinate:

$$
z=x-d_{\min}, \qquad 0\le z\le R.
$$

The stratum function is

$$
g(x)=
\begin{cases}
0, & 255z\le100R,\\
1, & 100R<255z\le150R,\\
2, & 150R<255z.
\end{cases}
$$

The integer comparisons avoid floating-point boundary ambiguity. For unsigned 8-bit data, they reduce exactly to the original intervals 0 to 100, 101 to 150, and 151 to 255.

### B. Ordered adaptive profiles

The method retains three candidate profiles:

$$
D_1=(1,0,0), \qquad D_2=(2,1,0), \qquad D_3=(3,2,1).
$$

The component $D_p[k]$ is the requested number of payload bits for a sample in stratum $k$ under profile $p$.

### C. Replacement block

Replacing $r$ LSBs can produce any value in the aligned block

$$
B_r(x)=
\left[
d_{\min}+2^r\left\lfloor\frac{x-d_{\min}}{2^r}\right\rfloor,
d_{\min}+2^r\left\lfloor\frac{x-d_{\min}}{2^r}\right\rfloor+2^r-1
\right].
$$

This block is the complete set of possible post-embedding values for that sample and width. Safety must hold for the whole block, not only for the payload chunk that happens to be written.

### D. Guarded body depth

For requested depth $D_p[g(x)]$, the actual body depth is the largest safe candidate:

$$
h_p(x)=\max\left(
\{
t\in\{1,\ldots,\min(D_p[g(x)],b)\}:g(\min B_t(x))=g(\max B_t(x))=g(x),\ B_t(x)\cap\Pi=\varnothing
\}\cup\{0\}
\right).
$$

A requested depth may therefore be reduced instead of being discarded completely. This guard prevents an embedding choice from changing the receiver-relevant stratum or moving into a declared padding value.

### E. Fixed self-describing header

The header contains 17 bytes:

| Field | Width | Meaning |
|---|---:|---|
| Magic | 4 bytes | ASCII `ICHS` |
| Version | 1 byte | Protocol version 1 |
| Payload length | 8 bytes | Unsigned big-endian byte length |
| CRC32 | 4 bytes | Accidental-error detection value for the payload |

Therefore,

$$
H=17\text{ bytes}=136\text{ bits}.
$$

CRC32 is not a cryptographic authentication code and is not presented as protection against an active attacker.

### F. Header carriers and body boundary

Let $J=(j_0,j_1,\ldots,j_{135})$ be the first 136 traversal positions whose complete one-bit replacement blocks:

- remain inside the stored-value domain;
- do not intersect the padding set.

The header is written only at positions in $J$. Define

$$
\beta=j_{135}+1.
$$

The complete prefix $[0,\beta)$ is reserved. Body embedding begins at $\beta$, even if some earlier prefix positions were not used by the header. This rule makes header and body carriers disjoint and lets the receiver reconstruct the same boundary. Header carrier eligibility does not require stratum preservation. A header write may change a header pixel's stratum without affecting the body because the full prefix is excluded from body capacity and traversal.

### G. Capacity and profile selection

For profile $p$, raw suffix capacity is

$$
C_p^{\mathrm{raw}}=
\sum_{i=\beta}^{N-1}h_p(X_i).
$$

Only complete bytes are usable:

$$
C_p^{\mathrm{byte}}=\left\lfloor\frac{C_p^{\mathrm{raw}}}{8}\right\rfloor,
\qquad
C_p^{\mathrm{usable}}=8C_p^{\mathrm{byte}}.
$$

For payload length $|M|$ in bytes, select the smallest feasible profile:

$$
p^*=\min\{p\mid p\in\{1,2,3\},\ |M|\le C_p^{\mathrm{byte}}\}.
$$

If no profile is feasible, the sender rejects the operation before modifying the array.

### H. Actual bit replacement

At a body position with guarded depth $r$, let

$$
m=\min(r,\text{remaining payload bits}).
$$

If $q$ is the next $m$-bit payload chunk, the stored-value replacement is

$$
x'=d_{\min}+2^m\left\lfloor\frac{x-d_{\min}}{2^m}\right\rfloor+q.
$$

The actual width $m$ is used on the final partial carrier. This preserves byte-exact consumption without padding the logical payload.

## 4. Step-by-step algorithm

### A. Embedding

1. Validate the array, stored-value domain, payload type, and padding specification.
2. Scan for the first 136 header carriers whose complete one-bit blocks avoid padding.
3. Reject before copying if fewer than 136 carriers exist.
4. Compute $\beta$ and reserve the complete header prefix.
5. Compute guarded body capacities for all three profiles.
6. Select the smallest feasible profile.
7. Build the 17-byte header from magic, version, payload length, and CRC32.
8. Write the header bits at the positions in $J$.
9. Traverse body positions from $\beta$ and reconstruct each guarded depth from the current stored value.
10. Write payload bits with the actual-width rule.
11. Return the stego array. Inspect capacity and scheduling reports separately when evidence requires them.

See [embedding_flow.mmd](assets/embedding_flow.mmd).

### B. Extraction

1. Validate the stego array and the same metadata contract.
2. Reconstruct the first 136 safe header-carrier positions.
3. Read and parse the header.
4. Reject invalid magic, unsupported version, impossible length, or insufficient capacity before allocating the payload buffer.
5. Reconstruct $\beta$, the selected profile, and every guarded body depth.
6. Read exactly the declared number of payload bits.
7. Reconstruct the payload bytes.
8. Compare the computed CRC32 with the header value.
9. Return the payload only when all checks succeed.

See [extraction_flow.mmd](assets/extraction_flow.mmd).

### C. Evaluation

The evaluation workflow uses matched cover-payload pairs and separates:

- payload correctness;
- image-array distortion;
- embedding capacity;
- side-information overhead;
- rejection behavior;
- runtime and memory;
- restricted DICOM load-write-read behavior.

See [evaluation_flow.mmd](assets/evaluation_flow.mmd).

## 5. Internal correctness argument

The B1 proof chain is conditional and has seven principal obligations.

| Proof | Statement |
|---|---|
| P1 | Header carrier eligibility remains invariant after a one-bit safe replacement |
| P2 | A guarded body replacement preserves the original stratum and avoids padding |
| P3 | For every candidate profile $p$, the guarded depth recomputed from the stego sample equals the depth computed from the corresponding cover sample |
| P4 | Capacity and minimal feasible profile selection are exact |
| P5 | Sender and receiver consume the same bit sequence and recover the exact payload |
| P6 | DICOM payload recovery is conditional on a lossless, faithful stored-array round trip and preserved required metadata |
| P7 | The method is non-injective with respect to the original cover and therefore is not cover-reversible |

### Conditional payload-recovery theorem

For an accepted array $X$, payload $M$, domain metadata $(b,s)$, and padding specification $\Pi$, assume:

1. embedding succeeds;
2. the receiver obtains the intact stego stored-value array;
3. the receiver uses identical $(b,s,\Pi)$ metadata and traversal;
4. no required DICOM representation information is altered;
5. the header and body have not been corrupted.

Then the extraction algorithm returns the exact payload:

$$
\mathrm{Extract}(\mathrm{Embed}(X,M),b,s,\Pi)=M.
$$

This theorem concerns payload recovery. It does not imply recovery of $X$.

## 6. Results

No experimental ICHAN-DH results are available at the current research gate.

The following table is intentionally unfilled until the researcher executes the designated researcher-run notebooks and preserves the outputs.

| Dataset or fixture | Payload rate | Exact recovery | BER | PSNR | SSIM | Runtime | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Controlled array fixtures |  |  |  |  |  |  | Pending |
| Restricted synthetic CT fixture |  |  |  |  |  |  | Pending |
| Approved public CT cohort |  |  |  |  |  |  | Not started |

Expected values derived from mathematics or source inspection must not be entered as measured results.

## 7. Corrections introduced relative to BASMEDSecure

| BASMEDSecure limitation | ICHAN-DH correction | Improvement level |
|---|---|---|
| Learned reproduction of deterministic thresholds | Exact native-domain integer partition | High methodological clarity |
| External per-position key array | Receiver-reconstructed header and body schedule | High protocol improvement |
| No explicit endpoint | 64-bit payload byte length in a fixed header | High correctness improvement |
| No payload corruption indicator | CRC32 with a deliberately narrow accidental-error claim | Medium reliability improvement |
| 8-bit metric and threshold assumptions | Declared signed or unsigned 2-bit to 16-bit stored-value domain | High domain correction |
| No padding policy | Complete replacement-block exclusion from the padding set | High padding-safety design improvement |
| Capacity without byte alignment | Raw, byte, usable, and tail capacity reported separately | Medium accounting improvement |
| Possible threshold crossing after LSB changes | Whole-block stratum-preservation guard | High synchronization improvement |
| Unclear failure behavior | Named validation and rejection conditions | High reproducibility improvement |
| Cover-image output implied by extraction | Explicit non-reversibility proposition | High claim correction |

These levels describe the importance of the design change. They are not measured effect sizes.

## 8. Code notebook

Open [code.ipynb](code.ipynb) from this directory. It imports the copied canonical package from `assets/source/ichan_secure` and provides a concise walkthrough of:

1. stored-value domain declaration;
2. deterministic classification;
3. header construction;
4. header-carrier scheduling;
5. guarded capacity;
6. embedding;
7. extraction;
8. conditional equality inspection;
9. metric calculation;
10. a restricted DICOM interface template.

The notebook is a presentation artifact, not the complete Gate 5 verification record. It is delivered without outputs and must not be presented as experimental evidence before researcher execution.

## 9. Limitations and claim boundaries

ICHAN-DH currently does not establish:

- original-cover recovery;
- encryption or payload confidentiality;
- cryptographic integrity or authentication;
- robustness after compression, filtering, rescaling, or lossy transfer;
- resistance to steganalysis;
- clinical or diagnostic preservation;
- compatibility with all DICOM objects or transfer syntaxes;
- superior capacity, distortion, or runtime relative to BASMEDSecure;
- quantum advantage or quantum-computing execution.

The current contribution is a more explicit internal-correctness contract and a prepared implementation for a restricted CT profile.

## 10. Research workflow after this presentation

1. Apply the outstanding Gate 5 notebook corrections.
2. Execute the controlled verification notebook in the recorded environment.
3. Review every failure and preserve the complete output record.
4. Obtain supervisor approval for the dataset protocol.
5. Create the Gate 6 analysis notebook.
6. Run matched BASMEDSecure and ICHAN-DH experiments where domain comparability is valid.
7. Analyze payload recovery, distortion, capacity, map cost, rejection behavior, and runtime.
8. Limit the paper claims to the evidence that survives review.

The full gate diagram is available as [research_workflow.mmd](assets/research_workflow.mmd).

## 11. Reference map

| Artifact | Location |
|---|---|
| Operative mathematical specification | `assets/reference/mathematical_specification.md` |
| Proof and evidence ledger | `assets/reference/proof_ledger.md` |
| Gate progress and current comparison | `assets/reference/gate_progress.md` |
| Research process | `assets/reference/research_workflow.md` |
| Implementation handoff | `assets/reference/gate4_implementation_handoff.md` |
| Verification notebook handoff | `assets/reference/gate5_notebook_handoff.md` |
| Canonical copied source | `assets/source/ichan_secure/` |
| Full prepared verification notebook | `assets/reference/01_ichan_algorithm_verification.ipynb` |
