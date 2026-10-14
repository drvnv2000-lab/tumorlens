# Initial LUMIERE feasibility audit

> **Background to v1.** The LUMIERE data audit that preceded v1; its counts carry into v1. Current results: [`V1_RESULTS.md`](V1_RESULTS.md). Index of all documents: [`README.md`](README.md).

**Release inspected:** LUMIERE v202211. **Purpose:** data readiness and integrity only. These counts are not clinical performance results and do not establish a publishable primary endpoint.

## Rating tables

- 616 released rating rows across 91 patients.
- Rating counts as released: PD 253; Post-Op 124; Pre-Op 92; SD 97; PR 20; CR 27; Post-Op/PD 1; `None` 2.
- 149 rationale strings matched a simple explicit-dimensions pattern. A text heuristic placed 57 rows in a stricter target-measurement review queue. Both counts are screening summaries; neither means a visit is measurement-driven or eligible.
- The completeness file has 638 rows. Seventeen rating rows across 11 patients do not have an exact patient/timepoint match. An exact join of ratings to actual image-folder names links 605 of 616 rows, representing 602 unique rating keys. Three keys contain duplicate rating rows; two have conflicting expert calls and all three have differing rationales. Excluding those collision keys leaves 599 unique rating keys linked to image folders. The collision report is local at `results/lumiere-audit/rating_key_collisions.csv`. The 11 unmatched rows and 3 collision keys are excluded from scan-level expert-linked analyses unless resolved. The join uses exact keys only and never guesses offsets.
- The 113 explicit-dimensions rows remaining after source early-window/non-measurable flags reduce to 111 rows with exact image folders and 110 unambiguous keys after collision exclusion, across 49 patients. This remains a regex-and-source-flag screen, not human-confirmed eligibility. These 110 rows contain 106 PD and 4 PR ratings, with no SD or CR. The stricter target-measurement text heuristic yields 56 exact, unambiguous keys (55 PD, 1 PR). The data therefore cannot support a balanced or confirmatory expert-call discordance/deferral claim. Independent rationale review is required before measurement-agreement estimates.
- The dataset's official preparation repository says all timing is relative to the first pre-operative MRI and calculated by floor division of elapsed days by seven; same-week studies can receive ordering suffixes. The completeness table and image folders disagree for participant key only: eight keys appear in each source, with no overlap. Use the image folders themselves to determine image and mask availability; do not filter these files through the conflicting completeness keys. Exclude participant key only from analyses that require the mismatched completeness/MRinfo keys unless those inputs can be joined independently. The audit CLI regenerates local inventories at `results/lumiere-audit/unmatched_visit_keys.csv`, `results/lumiere-audit/completeness_imaging_key_mismatches.csv`, and `results/lumiere-audit/rating_rows_without_image_folder.csv`.

## Imaging and masks

- 638 `Patient-*/week-*` folders across 91 patients.
- CT1 is present and readable in 632 visit folders.
- Each released native segmentation method has a readable mask in 599 folders.
- An identical stored shape and affine match to CT1 was found in 235 DeepBraTumIA masks and 599 HD-GLIO-AUTO masks. Many DeepBraTumIA differences reflect axis ordering/orientation; this flag is not an image-quality verdict. Resample to a pre-specified reference grid and validate spatial correspondence before voxelwise comparison or visualization.
- The corrected imaging audit computes method-specific enhancing-mask volume as voxel count times the absolute affine determinant: DeepBraTumIA label 1 and HD-GLIO-AUTO label 2. The DeepBraTumIA mapping is checked against the included per-scan `Enhancing_Core` volume JSON; the HD-GLIO-AUTO map follows its two-class label definition. A volume inventory is not expert 2D SPD or a RANO response call. Earlier local outputs that treated label 2 as enhancing for both methods are superseded and must not be used.

## Required before a primary analysis

1. Preserve the 17 rating/completeness key mismatches, 3 duplicate rating-key collisions, and participant key's eight-versus-eight table/folder conflict in the cohort flow. Directly join ratings to image folders by exact key; do not count duplicate keys as distinct visits. Exclude 11 rating rows without a folder and all three collision keys from scan-level expert-linked analyses unless resolved. Do not guess missing mappings.
2. Blindedly adjudicate measurement-driven, non-measurement-driven and indeterminate rationales using a written coding manual; measure inter-rater agreement.
3. Reconcile segmentation label semantics, orientation and spatial alignment. Validate a sample against the image headers and published measurement definitions.
4. Extract expert bidimensional measurements from rationale text under independent double review, or define a defensible volumetric endpoint and label it as such.
5. The preregistered ~150-measurement feasibility gate is not met even by the broad heuristic screen (110 unambiguous folder-linked rows and 56 under the stricter text screen, both heavily response-imbalanced). Do not run a confirmatory selective-risk comparison on this cohort. Restrict this release to descriptive feasibility, pipeline validation, and explicitly exploratory analyses; a revised research question requires a dated preregistration deviation and independent human review.

The detailed patient-level review queue and mask inventory are generated locally under `results/` and are intentionally absent from the portable source archive.
