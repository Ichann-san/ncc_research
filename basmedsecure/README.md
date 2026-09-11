# BASMEDSecure

## 1. Research overview

BASMEDSecure is presented in the supplied paper as a logistic-regression-based data-hiding framework for patient records. Its central idea is to classify grayscale pixels into three intensity groups and assign a different least significant bit (LSB) embedding depth to each group. The intended trade-off is higher payload capacity with limited visual distortion [1, Sections I and III].

This presentation separates three evidence objects:

1. **Published method:** the algorithm and numerical results reported in `BASMEDSecure.pdf`.
2. **Supplied local prototype:** `basmedcesure_original.py`, which contains implementation defects and is preserved only as provenance.
3. **Disclosed repaired baseline:** the bounded implementation imported by `code.ipynb` for later reproducibility work.

The repaired baseline is not described as the exact published software. It adds operational decisions that the paper does not fully specify.

### Research objective reported by the paper

The paper aims to hide patient information in medical images by combining:

- deterministic intensity labels;
- multinomial logistic regression;
- adaptive LSB replacement;
- an external key array that records how many bits were written at each visited position.

### Evidence status

| Item | Status |
|---|---|
| Paper method and paper tables | Available as reported evidence |
| Original draw.io flowchart | Preserved as JSON and normalized into Mermaid |
| Supplied local Python prototype | Statically inspected; not executed |
| Disclosed repaired baseline | Prepared; not executed in this presentation |
| Independent reproduction of paper metrics | Not available |
| Independent payload-recovery measurement | Not available |

## 2. Required data and state

### A. Embedding inputs

The method requires:

| Input | Role | Important condition |
|---|---|---|
| Cover image | Carrier for the hidden data | Treated by the paper as grayscale values in the range 0 to 255 |
| Secret data | Payload to be converted into bits | Capacity must be checked in bits |
| Pixel labels | Low, medium, or high intensity | Generated from fixed thresholds and predicted by logistic regression |
| Traversal order | Defines the pixel sequence | Must be identical during interpretation of the key array |

### B. Extraction inputs

Extraction requires both the stego image and the external key array. The key entry for a visited position specifies whether zero, one, two, or three LSBs contribute to the payload.

The key array is therefore required receiver state. Its storage or transmission cost must be counted separately from the payload hidden in the image.

### C. Intensity labels

For an 8-bit grayscale value $x \in \{0,1,\ldots,255\}$, the paper constructs the target label [1, p. 3]

$$
y(x)=
\begin{cases}
0, & 0 \le x \le 100,\\
1, & 101 \le x \le 150,\\
2, & 151 \le x \le 255.
\end{cases}
$$

The paper then trains logistic regression using the pixel value as the feature and this threshold-generated label as the target. Because the target is already a deterministic function of the feature, the classifier is learning boundaries that are known before training.

## 3. Method

### A. Pixel classification

1. Read the grayscale cover image.
2. Flatten the image into an ordered pixel vector.
3. Generate low, medium, and high training labels from the fixed thresholds.
4. Train or apply multinomial logistic regression.
5. Predict one label for each pixel.
6. Count predicted pixels in the three classes as $P_0$, $P_1$, and $P_2$.

### B. Capacity model

The maximum capacity reported by the paper is [1, Eq. (1)]

$$
C_{\max}=3P_0+2P_1+P_2 \quad \text{bits}.
$$

Three ordered embedding profiles are used:

| Profile | Low class | Medium class | High class | Selection condition |
|---:|---:|---:|---:|---|
| 1 | 1 bit | 0 bits | 0 bits | $L \le P_0$ |
| 2 | 2 bits | 1 bit | 0 bits | $P_0 < L \le 2P_0+P_1$ |
| 3 | 3 bits | 2 bits | 1 bit | $L > 2P_0+P_1$, subject to $L \le C_{\max}$ |

Here, $L$ is the payload length in bits. A complete implementation must reject $L>C_{\max}$ before modifying the image.

### C. LSB replacement

For a pixel value $x$, an intended depth $r$, and a payload chunk $q \in \{0,\ldots,2^r-1\}$, LSB replacement is

$$
x'=2^r\left\lfloor\frac{x}{2^r}\right\rfloor+q.
$$

The final visited pixel may receive fewer bits than the nominal profile depth. The disclosed repaired baseline records the actual width used at each visited position.

### D. Embedding procedure

1. Convert the secret bytes to an MSB-first bit sequence.
2. Predict all pixel classes.
3. Compute the profile capacities and select the lowest feasible profile.
4. Traverse pixels in row-major order.
5. Obtain the nominal depth from the selected profile and predicted class.
6. Reduce the depth when fewer payload bits remain.
7. Replace the selected LSBs.
8. Append the actual width to the external key array, including zero-width visited positions.
9. Stop exactly when all payload bits have been consumed.
10. Return the stego image and key array.

### E. Extraction procedure

1. Receive the stego image and external key array.
2. Traverse the key array and image in the same order.
3. For a key value $r>0$, read the $r$ least significant bits from the corresponding pixel.
4. Append the bits in the same order used during embedding.
5. Stop at the end of the key array.
6. Reassemble complete bytes and return the payload.

The normalized workflow is available as [Mermaid source](assets/basmedsecure_flow.mmd). The original downloaded diagram is preserved as [draw.io JSON](assets/provenance/BASMEDSecure.json).

## 4. Results reported by BASMEDSecure

### A. Embedding results

The paper evaluates individual 512 by 512 images using payloads from 1 kb to 100 kb [1, Section IV]. It reports:

- PSNR values from 52.103 dB to 75.521 dB across its table;
- SSIM values from 0.9856 to 0.9999 across its table;
- a general decrease in PSNR and SSIM as payload size increases.

These values are **paper reports**. They have not been independently reproduced in this project. The paper uses $MAX_I=255$ for PSNR, which is suitable only for the declared 8-bit range and is not automatically valid for native 12-bit or 16-bit CT stored values.

### B. Extraction results

The paper provides extraction pseudocode guided by the key array [1, Algorithm II]. However, it does not provide a payload-recovery table with bit error rate, exact byte equality, malformed-input behavior, or failure counts. Image similarity alone does not demonstrate successful data extraction.

### C. Interpretation boundary

High PSNR or SSIM supports only a narrow statement about similarity between the tested cover and stego arrays. It does not by itself establish:

- exact payload recovery;
- diagnostic preservation;
- resistance to steganalysis;
- confidentiality or authentication;
- robustness to compression, rescaling, transfer-syntax changes, or other processing;
- generalization to an independently defined patient cohort.

## 5. Observed weaknesses and flaws

### A. Methodological weaknesses

| Level | Observation | Consequence |
|---|---|---|
| High | The target label is generated directly from fixed intensity thresholds, then logistic regression is trained to reproduce it | The learning stage adds estimation uncertainty without creating new information |
| High | The receiver requires an external key array | The scheme is not self-describing, and effective overhead may be substantial |
| High | The extraction pseudocode outputs a cover image although LSB replacement does not preserve overwritten cover bits | Exact original-image recovery is not supported by the stated method |
| High | The extraction pseudocode tests secret-data length although secret data is not listed as an extraction input | The receiver contract is incomplete or internally inconsistent |
| High | No framing field defines payload length or validates the payload | Endpoint handling and malformed-input behavior are underspecified |
| High | DICOM padding, signed stored values, `BitsStored`, and transfer syntax are not integrated into the algorithm | The 8-bit image model cannot be assumed to represent general CT DICOM data |
| Medium | Capacity is presented without the key-array cost | Net communication capacity is overstated if side information is transmitted |
| Medium | Dataset provenance, preprocessing, exclusions, and patient-level grouping are incomplete | Reproducibility and generalization cannot be evaluated reliably |
| Medium | Only PSNR and SSIM are reported | Extraction correctness and security claims remain unsupported |
| Medium | Diagnostic suitability is inferred from image similarity without expert or task-based validation | Clinical preservation is not established |
| Medium | Security terminology is broader than the implemented mechanism | LSB hiding alone does not provide confidentiality, integrity, or authentication |

### B. Pseudocode ambiguity

The third profile is selected by an `else` branch after the first two capacity checks. A correct implementation must still reject any payload larger than $3P_0+2P_1+P_2$. Without this guard, the algorithm can terminate after exhausting pixels with an incomplete payload.

The flowchart JSON also contains inconsistent wording and conditions. The Mermaid version normalizes the paper's intended capacity expressions while preserving the three-profile decision structure.

### C. Supplied prototype defect

Static inspection of the supplied local file identifies a direct execution defect:

```python
key_array = {}
...
key_array.append(bits_to_embed)
```

The object is initialized as a dictionary but later used as a list. This is a defect in the supplied prototype. It must not be attributed to the paper unless the published implementation is shown to contain the same code.

### D. Threat and risk interpretation

| Threat level | Example | Current protection |
|---|---|---|
| Low | Accidental visual inspection | Small LSB changes may be difficult to notice |
| Medium | File conversion or pixel modification | No robustness guarantee is established |
| High | Statistical steganalysis | No detection study is reported |
| High | Key-array loss or corruption | Extraction can fail because the receiver depends on the map |
| Critical | Unauthorized disclosure of patient information | No encryption mechanism is part of the stated embedding algorithm |
| Critical | Malicious payload modification | No authentication mechanism is specified |

## 6. Disclosed repaired baseline

The presentation notebook uses a bounded baseline with the following explicit decisions:

- unsigned 8-bit arrays only;
- fresh multinomial logistic-regression fitting for every cover;
- scikit-learn version fixed by the research package;
- explicit capacity rejection;
- actual final chunk width recorded;
- ordered visited-prefix key array;
- exact key-driven payload extraction;
- no claim of cover reversibility or DICOM support.

This baseline exists to support a fair future comparison. It does not correct the wider scientific limitations of the paper.

## 7. Code notebook

Open [code.ipynb](code.ipynb) from this directory. Run it only after installing the dependencies declared in the notebook. The notebook imports the preserved repaired baseline from `assets/source/ichan_secure` and demonstrates:

1. environment setup;
2. a deterministic 8-bit synthetic cover;
3. baseline embedding;
4. key-array inspection;
5. payload extraction;
6. exact byte comparison;
7. distortion and map-overhead reporting.

The notebook is delivered without execution outputs. Any displayed value becomes evidence only after the researcher runs the notebook and preserves the resulting environment and output record.

## 8. Files and provenance

| File | Purpose |
|---|---|
| `assets/provenance/BASMEDSecure.pdf` | Supplied paper |
| `assets/provenance/BASMEDSecure.json` | Downloaded draw.io flowchart source |
| `assets/provenance/basmedcesure_original.py` | Supplied local prototype, preserved unchanged |
| `assets/provenance/basmedsecure_legacy.ipynb` | Historical mixed research notebook, preserved unchanged |
| `assets/source/ichan_secure/baseline.py` | Disclosed repaired baseline imported by the presentation notebook |
| `assets/basmedsecure_flow.mmd` | Clean Mermaid representation for draw.io import |

## 9. Presentation conclusion

BASMEDSecure provides a useful adaptive-capacity starting point and reports high cover-stego similarity. The main research gap is not merely a programming error. The larger gap is the absence of a complete receiver contract, native CT-domain policy, side-information accounting, payload correctness evidence, and bounded security claims. These limitations motivate ICHAN-DH.

## 9. References

[1] B. A. Salim, T. Ahmad, D. K. Ginting, A. B. Habtie, N. Jean De La Croix, and M. S. Hossen, "BASMEDSecure: A Logistic Regression-Based Data Hiding Framework for Securing Patient Records," supplied six-page manuscript PDF, pp. 1-6. Available in `assets/provenance/BASMEDSecure.pdf`.

[2] `assets/provenance/basmedcesure_original.py`, supplied local prototype, preserved without modification.

[3] `assets/source/ichan_secure/baseline.py`, disclosed repaired uint8 baseline prepared for this research comparison.
