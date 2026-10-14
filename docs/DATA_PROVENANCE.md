# Data provenance and handling

## Primary source: LUMIERE

Suter et al. released a single-centre longitudinal glioblastoma MRI collection with 91 patients, 638 study dates and 2,487 images. The collection includes MRI, two automated segmentation outputs, expert ratings with free-text rationale, MRI completeness, acquisition metadata and demographic/pathology tables. The source paper states the data may only be used for non-commercial purposes.

The Figshare API reports CC0 for individual collection items, while the data descriptor states non-commercial use. **Treat the more restrictive non-commercial condition as controlling until the rights holders clarify the apparent conflict.** Do not redistribute the MRI archive, volumes or other derived images, and do not use this project commercially without written permission. The one exception is the 15 viewer cases in [`cases/`](cases/DATA-LICENCE.md): single 2D slices at the measured level, with LUMIERE's own identifiers and the per-visit measurements, published for non-commercial research display and documented there.

The [official preparation repository](https://github.com/ysuter/gbm-data-longitudinal) documents that timepoints are elapsed weeks from the first pre-operative MRI, calculated with floor division by seven. Same-week scans may have ordering suffixes. In this local v202211 release, 17 expert-rating rows across 11 patients have no exact `Patient` + `Date` to completeness `Patient` + `Timepoint` match. An exact join from rating rows directly to image-folder names succeeds for 605 of 616 rows, but these represent only 602 distinct rating keys. Three keys contain duplicate rows (two with different expert calls and all three with differing rationales); excluding those keys leaves 599 unique, unambiguous linked keys. Eleven rating rows have no exact folder. participant key has eight completeness timepoint keys and eight image-folder keys, with no overlap. TumorLens uses exact rating-to-image folder joins and derives image/mask availability from the files themselves; it does not use the conflicting completeness table to discard otherwise directly matched scans. Rows without exact image folders and collision keys are excluded from scan-level expert-linked analyses unless resolved. Analyses using completeness/MRinfo keys must exclude or separately resolve participant key. The local CLI regenerates mismatch and collision inventories; patient-level output is excluded from the portable source archive.

The explicit-dimensions regex finds 149 rating rows; applying the released early-window/non-measurable flags leaves 113. Exact-folder linkage and exclusion of collided keys leave 110 rows across 49 patients (106 PD, 4 PR, no SD/CR). A stricter automated free-text screen leaves 56 exact, unambiguous keys (55 PD, 1 PR). These are heuristic review counts, not human-adjudicated measurement eligibility. They fall below the preregistered ~150 feasibility gate and are too response-imbalanced for confirmatory expert-call discordance or deferral claims.

Files inventoried for this project:

| Source file | Figshare item | Approx. bytes | Role |
|---|---:|---:|---|
| `LUMIERE-readme.pdf` | 21266241 | 189,228 | File/label documentation |
| `LUMIERE-datacompleteness.csv` | 21195430 | 23,646 | Visit/modality/mask availability |
| `LUMIERE-MRinfo.csv` | 21195562 | 363,872 | Acquisition metadata |
| `LUMIERE-ExpertRating-v202211.csv` | 21195556 | 31,133 | Expert calls and rationale |
| `Imaging-v202211.zip` | 21249516 | 32,565,467,707 | NIfTI images and segmentations |
| `LUMIERE-Demographics_Pathology.csv` | 21195559 | 5,108 | Patient-level metadata |
| `LUMIERE-pyradiomics-hdglioauto-features.csv` | 21187030 | 13,471,846 | Published derived features; exploratory only |
| `LUMIERE-pyradiomics-deepbratumia-features.csv` | 21187033 | 21,835,161 | Published derived features; exploratory only |

Source collection: [Figshare collection](https://springernature.figshare.com/collections/The_LUMIERE_Dataset_Longitudinal_Glioblastoma_MRI_with_Expert_RANO_Evaluation/5904905). Data descriptor: [Suter et al., Scientific Data (2022)](https://www.nature.com/articles/s41597-022-01881-7). Closest measurement study: [Suter et al., Frontiers in Radiology (2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10513769/).

## Local copy

The source owner has the complete downloaded release locally at `V:\1. Work\Project 2 (TumorLens)\TumorLens\data\raw\lumiere\`, with the archive extracted to `Imaging/`. Do not edit the source files. For another machine, obtain the release from the Figshare collection above, place it in `data/raw/lumiere/`, and record SHA-256 hashes plus retrieval date in a private local provenance record. The portable project archive excludes raw files and patient-level derived outputs.

The released segmentation maps use method-specific class numbers. In DeepBraTumIA's native mask, label 1 is enhancing core; this mapping was checked against the per-visit `measured_volumes_in_mm3.json` field `Enhancing_Core`. Label 2 is necrotic/non-enhancing, and label 3 is edema. In HD-GLIO-AUTO's two-class map, label 2 is contrast-enhancing. Do not apply one integer label across both methods. The corrected local imaging audit records these label identities explicitly.

## Derived outputs

Keep patient-level outputs local. Publish only aggregates after checking the dataset license, source terms and re-identification risk. Do not publish representative images, slices, segmentations or downloadable meshes by default. Any public release needs a separate data/license review.

## Exclusions

- No third-party model source, model weights, copied implementation or project history is included.
- The supplied visual prototype is synthetic and is kept separate from the evidence pipeline.
- Do not infer a RANO call from a segmentation dataset that lacks the clinical/timepoint inputs required by the relevant criteria.
