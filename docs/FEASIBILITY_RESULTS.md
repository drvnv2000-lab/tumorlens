# LUMIERE feasibility results

> **Background to v1.** This audit found the confirmatory expert-referenced analysis infeasible, which is why v1 is a descriptive methods study. Current results: [`V1_RESULTS.md`](V1_RESULTS.md). Index of all documents: [`README.md`](README.md).

**Status:** completed descriptive source-table and local-file feasibility audit; not a clinical validation study.
**Dataset release:** LUMIERE v202211.
**Audit run:** 2026-10-11 with TumorLens 0.1.0.

## Main finding

The planned expert-referenced confirmatory analysis is not feasible from the released rationale measurements alone. The initial regex finds 149 rows with explicit dimensions. Applying the dataset's early-window and non-measurable flags leaves 113; exact image-folder linkage and removal of three duplicate patient/timepoint collision keys leaves 110 screened rows across 49 patients. These rows include 106 PD and 4 PR ratings, with no SD or CR. A stricter free-text heuristic leaves 56 exact, unambiguous keys (55 PD, 1 PR). These are automated screen counts only: no blinded human rationale adjudication has been completed, and they must not be described as a validated eligible cohort.

The originally preregistered information gate was approximately 150 measurements. The largest conservative screen falls below that gate and is markedly response-imbalanced. TumorLens therefore does not estimate confirmatory deferral performance or claim that a deferral rule detects expert-call discordance in LUMIERE. The defensible current contribution is a transparent data-readiness and measurement-pipeline feasibility report, with the existing synthetic viewer presented only as an illustration.

## Source-table audit

| Audit item | Count | Interpretation |
|---|---:|---|
| Rating rows / patients | 616 / 91 | Source-table rows, not all image-linked visits |
| Unique rating patient/timepoint keys | 613 | Three keys have repeated rows |
| Duplicate keys / rows involved | 3 / 6 | Two keys contain conflicting expert calls; all three have different rationales |
| Rating rows with exact image-folder key | 605 | Row count; includes duplicate-key rows |
| Unique exact image-linked keys | 602 | Before collision exclusion |
| Unique exact-linked keys after collision exclusion | 599 | Appropriate unambiguous scan-level denominator |
| Rating rows without an exact image-folder key | 11 | No fuzzy or offset mapping applied |
| Rating rows without exact completeness-table key | 17 | Separate mismatch from image-folder matching |
| Completeness keys / image folders in participant key | 8 / 8 | No key overlap; derive file availability from the image tree |

The three collision keys are reported in the local, patient-level `results/lumiere-audit/rating_key_collisions.csv`. The portable project contains code to regenerate that file, but it does not contain collision keys or any other patient-level outputs.

## Measurement-text screening

| Screen | Rows/keys | Patients | Expert calls |
|---|---:|---:|---|
| Explicit dimensions regex | 149 rows | 64 | Mostly PD; not an eligibility label |
| Plus released early-window/non-measurable flags | 113 rows | — | Broad source-flag screen |
| Plus exact image key and collision exclusion | 110 keys | 49 | PD 106; PR 4; SD 0; CR 0 |
| Stricter free-text target-measurement heuristic, exact key and collision exclusion | 56 keys | — | PD 55; PR 1 |

The stricter screen requires detected explicit dimensions and target-lesion language, and excludes several detected competing rationale phrases. String rules can miss or misread free text, so it is only a review queue. The rationale coding manual specifies blinded independent human review before any measurement-agreement estimate.

## Imaging inventory and limitations

The local inventory contains 638 image visit folders across 91 patients. CT1 is readable in 632 folders; each released mask is readable in 599 folders. Stored shape and affine identity with CT1 occurs in 235 DeepBraTumIA and 599 HD-GLIO-AUTO masks. The contrast-enhancing values differ by method: label 1 for DeepBraTumIA (checked against the included `Enhancing_Core` volume JSON) and label 2 for HD-GLIO-AUTO (two-class map). An earlier local audit counted DeepBraTumIA label 2 as enhancement; those outputs are superseded and must not be used. A differing grid may represent orientation conventions, not failed segmentation; voxelwise comparisons require documented spatial harmonization and visual/header QC. The dataset guide says the native-space files have different preparation histories across segmentation methods. No patient-level contour perturbation or response outcome is reported in this feasibility document.

## Reproduction

Run from the project root after installing the locked environment:

```powershell
tumorlens lumiere-audit --ratings data/raw/lumiere/LUMIERE-ExpertRating-v202211.csv --completeness data/raw/lumiere/LUMIERE-datacompleteness.csv --imaging-root data/raw/lumiere/Imaging --out results/lumiere-audit
tumorlens imaging-audit --imaging-root data/raw/lumiere/Imaging --out results/lumiere-imaging-audit
```

The first command writes patient-level output locally; keep `results/` private and out of the source archive. The aggregate cohort-flow figure is [`lumiere-feasibility.svg`](lumiere-feasibility.svg).

## Revised manuscript position

Use a descriptive title such as **“Data Readiness and Measurement Feasibility for Expert-Referenced Tumour Response Analysis in LUMIERE.”** Present the feasibility gate, key-collision audit, class imbalance, and image-grid constraints as the results. Do not present the original boundary-fragility/deferral question as answered. To make a confirmatory study possible, obtain an independent cohort with sufficiently many adjudicated longitudinal measurements across response classes, freeze a separate protocol, and validate the measurement pipeline before outcome analysis.

LUMIERE is publicly downloadable, but its data descriptor states non-commercial use. TumorLens follows that restriction and does not redistribute the MRI data or patient-level derivatives. Public availability alone is not treated as permission for commercial use.
