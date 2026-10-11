# TumorLens v1: analysis plan

Committed before any automated measurement has been compared with an expert measurement.
This file is append-only: later changes are added as dated "Deviations" at the bottom, never
edited in place. Author: Dr. Varad Vaidya (PharmD). Date of this entry: 2026-10-10.

## Question

How much of an automated, measurement-driven RANO response call is attributable to where the
tumour boundary is drawn, and does that fragility, or disagreement between two segmentation
tools, identify the calls that disagree with a neuroradiologist?

## Data

LUMIERE (Suter et al., Scientific Data 2022; figshare, CC0): 91 glioblastoma patients, skull-stripped
MRI, segmentations from DeepBraTumIA and HD-GLIO-AUTO, and expert RANO ratings with
bidimensional measurements recorded in the rating-rationale text. No model is trained.

Phase 0 counts (see PHASE0.md): 397 rated follow-up visits, 149 with expert measurements
(113 after excluding "less than 3 months" and non-measurable flags). Expert measurements are
mostly attached to progression calls, so stable visits are under-represented. All claims are
limited by this.

## Measurement

For each study and each tool, take the contrast-enhancing label, find the axial slice with the
largest area, measure the longest in-plane diameter and its longest perpendicular diameter
(convex hull of the outline), and form SPD. Lesions with either diameter under 10 mm are
non-measurable. Only the largest enhancing component per study is measured as a target lesion in v1
(multiple target lesions are summed by the expert; the effect is reported, not corrected).
Label identities for both tools are confirmed from their documentation before analysis, and
that check is recorded in the repository.

## Calls

RANO bidimensional criteria as implemented in `src/tumorlens/rano.py`: PD at least +25 percent
over the nadir, PR at least -50 percent versus baseline, CR when no enhancing disease, else SD.
Confirmation windows, steroids, clinical status and non-enhancing disease are not modelled, so
these are measurement-driven calls, not clinical ratings.

## Analyses (all patient-clustered; 95% intervals from a patient-level bootstrap, 10,000 resamples)

1. **Measurement agreement.** On visits with an expert measurement: ratio of automated SPD to
   expert SPD (median and interquartile range) and Bland-Altman limits, per tool.
2. **Direction agreement.** On visits where both a nadir and a current expert SPD exist, the
   proportion where the automated and expert change from nadir have the same direction
   (Suter et al. 2023 report about 81 percent for HD-GLIO-AUTO volume; this is a sanity
   check, not a hypothesis).
3. **Fragility.** For every automated call, the smallest uniform boundary offset (0.5 mm steps,
   up to 3 mm, applied to all scans of a patient) that changes the call. Report the share of
   calls that flip within 1, 2 and 3 mm.
4. **Does fragility flag disagreement?** On visits with an expert call of PD or non-PD,
   AUROC of (a) smallest flip offset, (b) disagreement between the two tools' calls, for
   predicting disagreement with the expert call; patient-clustered bootstrap intervals.
   Flip offset is a distance-to-threshold in boundary units, so it is reported as the baseline,
   not as a new method.

## What would count as a null result

Intervals for analysis 4 that include 0.5. It would be reported as such.

## Stated limits

About 113 to 149 measured visits; expert measurements mostly on PD visits; one centre; the
expert measurement is a text field, parsed with a pattern, and unparsed rows are excluded.

## Deviations

(none yet)

### 2026-10-11 - status after the feasibility audit (replaces nothing above)

The entries below were added after the "(none yet)" placeholder above was written; the plan text above is unchanged from the 2026-10-10 commit. After exact image linkage and removal of duplicate-key collisions, the measured-visit set is 110 rows (49 patients; 106 PD, 4 PR, no SD or CR), below the roughly 150 information threshold set in PHASE0.md. The confirmatory analysis 4 (does fragility flag disagreement with the expert call) is therefore not run as a confirmatory test. Analyses 1 to 3 (measurement agreement, direction agreement, fragility) remain in v1 as descriptive analyses. No replacement primary hypothesis has been frozen.

### 2026-10-11 — data-rights and join audit; no outcome-driven changes

A reproducible audit of the released tables and local image archive found 17 exact Patient/Date keys in the rating file without an exact Patient/Timepoint match in the completeness table. No fuzzy date mapping was applied. These rows remain unresolved pending an authoritative mapping. The imaging archive contains 638 visit folders across 91 patients; each native segmentation method was readable in 599 folders. DeepBraTumIA masks frequently have a different stored axis order/affine representation from CT1. This is not treated as a segmentation failure; spatial harmonization and header-level review are required before voxelwise comparison.

The LUMIERE data descriptor states non-commercial use, while Figshare item metadata reports CC0. This project follows the stricter non-commercial condition unless the rights holders clarify the discrepancy. The Phase 0 count of 149 rationale rows with expert dimensions is retained as a feasibility count, not an eligibility guarantee. Blinded human review and the previously stated kill threshold remain in force. No analysis outcome has been inspected and no primary estimand was changed. See `docs/INITIAL_DATA_AUDIT.md` and `docs/DATA_PROVENANCE.md` for details.

### 2026-10-11 — blinded rationale-coding operations specified

Added `docs/RATIONALE_CODING_MANUAL.md` to make the preregistered measurement-driven subset curation reproducible before human adjudication. It defines blinded fields, MD/NMD/MIXED/IND rationale classes, strict-primary versus mixed-sensitivity candidates, double review and disagreement reporting. This is an operational clarification; it does not change the primary estimand or remove the sample-size/kill threshold. No segmentation-derived measurements or agreement results were inspected. The manual remains a draft until its pilot is completed and its version is frozen; any substantive revision must be dated here before full coding.

### 2026-10-11 — direct exact-key image linkage

The initial audit noted 17 rating/completeness key mismatches and left their image linkage unresolved pending clarification. A direct comparison against the actual imaging-folder names now shows exact `Patient` + timepoint matches for 605/616 rating rows; 11 rows have no exact image folder and will be excluded only from image-based analyses. This supersedes the earlier pending-linkage language: no author response is required to proceed. Patient-025's completeness/MRinfo timepoints remain disjoint from its image-folder timepoints, so analyses needing those tables must exclude that patient or use independently verifiable fields. Image/mask availability will be read from the actual files, not inferred from the conflicting completeness table. No offset or fuzzy match is used, and the primary estimand is unchanged.

### 2026-10-11 — duplicate-key audit and feasibility downgrade

A second source-table audit found 616 rating rows but only 613 unique patient/timepoint keys. Three keys contain duplicated ratings; two have conflicting expert calls, and all three have differing rationale text. The 605 exact image-linked rows therefore represent 602 unique keys, not 605 distinct visits. Excluding all three collided keys leaves 599 exact, unambiguous rating/image keys. The collision keys are retained in a local audit file and are not silently adjudicated.

Of 149 rows with explicit dimensions, 113 remain after the released early-window and non-measurable source-flag screen; exact image linkage and collision exclusion reduce this broad screen to 110 rows across 49 patients (106 PD, 4 PR, no SD or CR). A stricter string heuristic retains 56 keys (55 PD, 1 PR). These are screening counts, not human-coded eligibility. Both the broad count and response mix fail the original ~150-visit feasibility gate and do not support a confirmatory expert-call discordance or deferral analysis. The study scope is therefore downgraded to descriptive data/measurement feasibility and pipeline robustness in LUMIERE; the preregistered boundary-fragility/deferral claim is not tested as confirmatory using this release. No segmentation-derived primary outcome has been inspected. Any subsequent confirmatory study requires a separately justified cohort and a new dated protocol before outcome analysis.

### 2026-10-11 — method-specific enhancing-label correction

The initial imaging-audit implementation counted integer label 2 for both segmenters. Inspection of the included DeepBraTumIA native mask and its per-visit volume JSON showed that label 1 corresponds to `Enhancing_Core`, label 2 to necrotic/non-enhancing tissue, and label 3 to edema; HD-GLIO-AUTO's two-class map uses label 2 for contrast-enhancing tumour. The code and local inventory now use these method-specific values. Earlier local DeepBraTumIA label-2 volume outputs are superseded. This corrects the measurement implementation before any segmentation-derived response or performance outcome was inspected; it does not change the feasibility question or estimand.

The measurement utility now explicitly isolates the largest 26-connected 3D enhancing component before selecting its maximal axial slice, consistent with the v1 single-component rule. It previously selected the slice with the largest combined foreground area, which could combine separate lesions. No LUMIERE SPD or response series was calculated using the earlier behavior; the utility correction is documented for reproducibility.

### 2026-10-11 — CFB-GBM metadata-only cohort gate

A metadata-only audit of TCIA CFB-GBM Version 4 found 160 t0→t1, 112 t0→t2, and 107 t1→t2 GTV pairs with published volumetric RANO categories. Those categories are derived from the same GTV volumes and are not independent expert calls. At t0→t1, 137 pairs use a manually delineated t0 mask and generated t1 mask; 23 pairs use generated masks at both timepoints. The dataset paper reports a five-radiation-oncologist contour validation on 44 generated masks (mean Dice 0.97, HD95 1.87 mm, ASSD 0.31 mm), which validates sampled contours rather than the response labels. The CFB study is therefore scoped to geometric sensitivity of derived volumetric RANO categories, with no diagnostic or predictive accuracy claim; CR-specific inference is not supported. Only small Version 4 metadata tables were downloaded. TCIA lists the image package as 208.01 GB and requiring Aspera, while the standard public NBIA collection index did not expose CFB-GBM. Image download is gated on demonstrating a selective mask retrieval path and estimating its size. See docs/CFB_GBM_METADATA_AUDIT.md. This is a dataset selection and feasibility update, not inspection of any mask-derived perturbation result.

### 2026-10-11 — Version 4 volumetric-label reproduction and selective access check

The three RANO endpoints were recomputed from the official Version 4 GTV volume columns using the published RANO 2.0 thresholds. All 379 available labels reproduced exactly (160 t0→t1, 112 t0→t2, 107 t1→t2; zero mismatches). The TCIA Aspera package is browsable by patient/timepoint and exposes individual GTV files, but even a single-file transfer requires IBM Aspera Connect. No masks were downloaded. The local V: drive had approximately 215.8 GB free, so the 208 GB whole archive is not a safe download. Proceed with selective masks only after authorization to install the required Aspera client; see docs/CFB_GBM_METADATA_AUDIT.md. The label reproduction is a descriptive validation of the published table, not an independent endpoint analysis.

### 2026-10-11 — CFB-GBM geometric protocol frozen before mask outcomes

Added docs/CFB_GBM_PROTOCOL.md specifying the CFB-GBM Version 4 primary t0→t1 estimand, secondary intervals, signed-distance perturbation grid, category-recalculation rules, mask geometry/QC/exclusion rules, bootstrap, visual outputs, claim limits, and storage constraints. No CFB mask perturbation outcome was calculated before this protocol was written. Any later change must be dated here before further outcome analysis.

### 2026-10-11 — CFB-GBM endpoint terminology clarified before mask analysis

Updated the CFB protocol to call the outcomes dataset-derived pairwise volumetric response labels, rather than unqualified clinical RANO 2.0 categories. CFB-GBM t0 is pre-treatment, while RANO 2.0 recommends the first post-radiotherapy MRI as the reference for newly diagnosed glioma. The dataset's t0-based pairwise labels are therefore not complete clinical RANO adjudications. This pre-outcome clarification narrows terminology and claims only; the geometric sensitivity estimand and cohort are unchanged. See docs/CFB_GBM_PROTOCOL.md and docs/REFERENCES.md.

### 2026-10-11 — CFB-GBM transfer route rechecked before mask outcomes

The TCIA collection page and associated dataset processing repository were rechecked for a supported transfer path that would avoid installing Aspera. TCIA still requires IBM Aspera Connect for the image package and individual GTV file downloads; the GitHub repository contains processing scripts, not an image mirror. No supported no-install route was identified, no Aspera client was installed, and no mask transfer or perturbation analysis was started. Once client installation is authorized, transfer only the prespecified GTV masks and record their actual total size before analysis. This is an access-status update, not a protocol or outcome change.

### 2026-10-11 — label identities confirmed from documentation and the tools' own outputs

The plan requires both tools' label identities to be confirmed from documentation before analysis. Result, recorded in `docs/LABEL_VERIFICATION.md` with the aggregate check in `reports/v1/label_check.json` (script `scripts/verify_labels.py`):

- HD-GLIO-AUTO: label 2 = contrast-enhancing tumour, label 1 = non-enhancing T2/FLAIR signal abnormality. Source: the tool's own code (`scripts/run.py` in NeuroAI-HD/HD-GLIO-AUTO, commit 6acaad8, writes `volume_contrast_enhancing_tumor_mm3` from `data == 2`), repeated in the LUMIERE authors' modified copy (ysuter/gbm-data-longitudinal, commit e57c5b4). Signal check: median CT1/T1 intensity ratio 1.70 for label 2 versus 0.91 for label 1; label 2 enhances more in 424 of 424 visits.
- DeepBraTumIA: no public label documentation was found. Its own per-visit output `measured_volumes_in_mm3.json` names the compartments; in 60 of 60 sampled visits label 1 matched `Enhancing_Core`, label 2 `Necrotic_NonEnhancing` and label 3 `Edema_Compartment` exactly (to 1 mm³). Signal check: median CT1/T1 ratio 1.64 for label 1 versus 0.89 for label 2; label 1 enhances most in 501 of 529 visits (94.7%).
- Discrepancy: the released `LUMIERE-pyradiomics-deepbratumia-features.csv` names label 1 "Necrosis" and label 2 "Contrast-enhancing". Both checks above contradict that naming, so it is treated as a labelling error in the released feature table. DeepBraTumIA label 1 and HD-GLIO-AUTO label 2 are used as the contrast-enhancing compartment, as in the earlier correction entry. No segmentation-derived response or agreement outcome had been computed when this check was made.

### 2026-10-11 — analysis details fixed before any automated measurement is computed

Written after reading the expert rating text and image headers only; no automated SPD, call or agreement value exists yet. Analyses 1 to 3 run as descriptive analyses (see the status entry above); analysis 4 is not run.

Measurement.
- Masks: native CT1-space maps (`DeepBraTumIA-segmentation/native/segmentation/ct1_seg_mask.nii.gz`, label 1; `HD-GLIO-AUTO-segmentation/native/segmentation_CT1_origspace.nii.gz`, label 2), reoriented to the closest canonical (RAS) axes with nibabel. Each tool is measured on its own grid.
- Measurement plane (deviation from "axial"): many LUMIERE CT1 series are thick-slice 2D acquisitions, some coronal or sagittal (for example 0.9 x 0.9 mm in plane, 6 mm between slices). Measuring axially on a coronal series would use 6 mm pixels. The plane is therefore the acquisition plane: perpendicular to the axis with the coarsest spacing when that spacing is at least 1.5 times the finest, otherwise axial. The number of non-axial visits is reported.
- Lesion: largest 26-connected 3D component of the enhancing label; its slice with the largest area in the measurement plane; longest diameter and longest perpendicular (convex hull), as in `rano.py`.
- Automated SPD for calls: the product if both diameters are at least 10 mm, otherwise 0 (non-measurable). For analysis 1 the raw product is used whatever its size, and the measurable share is reported.
- Boundary offsets: -3 to +3 mm in 0.5 mm steps, applied in 3D to the enhancing mask with a Euclidean distance transform in mm (grow: distance to mask at most d; shrink: distance inside mask greater than d), then measured as above.

Expert values.
- Visit set: the 110 audited rows (dimension in the rationale, released early-window and non-measurable flags clear, exact image folder, no duplicate key).
- Expert SPD: every "a mm x b mm" pair in the rationale (a missing second "m" accepted), multiplied and summed. Visits with more than one pair are reported separately, because v1 measures one automated lesion.

Calls (analysis 3).
- Series: each expert "Post-Op" row starts a series as its baseline; later rows rated CR, PR, SD or PD follow until the next "Post-Op" row. "Pre-Op", "None" and "Post-Op/PD" rows are left out, and "Post-Op/PD" ends a series. A series needs a baseline with a readable mask for that tool.
- Rule clarified in `rano.py` (previously untested case): when the nadir SPD is 0 (no measurable disease), a measurable lesion is PD. CR needs no enhancing voxel at all; SPD 0 with some enhancing voxels is SD unless another rule applies. Confirmation, steroids, clinical status and non-enhancing disease remain unmodelled.
- Fragility: for each automated follow-up call, the smallest absolute offset (same offset for every scan in the series) that changes it; shares flipping within 1, 2 and 3 mm, per tool.

Direction agreement (analysis 2).
- As planned: within a patient's series, on each expert-measured visit that has an earlier expert-measured visit, sign of (current - minimum of earlier expert SPDs) versus the same quantity from the automated SPD at the same visits.
- Suter-matched comparison: Suter et al. 2023 computed trend agreement from the slope between consecutive follow-ups, automated enhancing volume against expert SPD (81.1 percent for HD-GLIO volume). Here: consecutive expert-measured visits in the same series, sign of change in expert SPD versus sign of change in automated enhancing volume (and automated SPD). Suter et al. used BraTumIA, not DeepBraTumIA, and had expert measurements at more time points than the released sheet, so this is a like-for-like method on a smaller subset, not an exact replication. Ties count as agreement only when both changes are zero.

Statistics. Patient-level bootstrap, 10,000 resamples, percentile 95 percent intervals, seed 20261011. Analysis 1: median and IQR of automated/expert SPD ratio; Bland-Altman bias and 95 percent limits on SPD in mm². Visits where a tool has no readable mask or no enhancing voxel are counted and excluded from that tool's ratio.
