# Dataset Boundary and Manifest Plan

Do not commit private clinical data, credentials, access tokens, or direct patient identifiers to this project.

## Planned sources

| Stage | Source | Intended role |
|---|---|---|
| Loader development | pydicom example files | Interface and metadata debugging only |
| Development collection | TCIA LIDC-IDRI | Patient-level CT development experiments |
| External validation | TCIA TCGA-LUAD CT subset | Patient-separated external validation |
| Optional modality shift | PhysioNet MIMIC-CXR | Credentialed radiograph evaluation under its data-use terms |

Dataset counts, versions, access dates, licences, acknowledgments, and exclusions must be verified when the data are actually acquired.

## Manifest fields

Use one row per image instance and keep only identifiers permitted by the dataset licence:

```text
dataset
collection_version
access_date
subject_id
study_uid
series_uid
sop_instance_uid
modality
rows
columns
samples_per_pixel
photometric_interpretation
bits_allocated
bits_stored
high_bit
pixel_representation
rescale_slope
rescale_intercept
transfer_syntax_uid
split
selection_reason
exclusion_reason
local_relative_path
```

## Split invariant

All instances belonging to one patient remain in exactly one split. Slices from the same patient must never be divided between development and validation. Aggregate image metrics to the patient level before drawing study-level uncertainty conclusions.

## Payload privacy

Use synthetic or pseudonymized payloads. The analysis manifest records payload-generation rule, byte length, bits per pixel, and random seed—not real patient records.
