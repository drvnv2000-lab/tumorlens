# CFB-GBM Version 4 metadata audit

Audit date: 2026-10-11  
Purpose: decide whether the public CFB-GBM cohort can support a longitudinal, contour-robustness study before downloading imaging data.

## Source and rights

The source is the CFB-GBM collection on The Cancer Imaging Archive (TCIA), Version 4, updated 2026-09-11. The collection page lists the image and segmentation archive as 208.01 GB, 3,981 images, and CC BY 4.0. Only the small Version 4 metadata tables listed below were retrieved for this audit. No MRI, CT, or segmentation image files were downloaded.

- Collection page: https://www.cancerimagingarchive.net/collection/cfb-gbm/
- Dataset paper: Leclercq et al., CFB-GBM v2.0: An Augmented Longitudinal Dataset for Multi-Modal Glioblastoma Segmentation, Radiomics, and RANO Progression Tracking, MELBA 2026, https://doi.org/10.59275/j.melba.2026-dd48
- Data citation: Moreau et al. (2025), CFB-GBM cohort, Version 4, TCIA, https://doi.org/10.7937/v9pn-2f72

The downloaded source tables are in data/raw/cfb_gbm/metadata/. They are source material and must not be altered. The current TCIA page notes that Version 4 corrected the RANO tables to use enhancing-tumour measurements.

## Counts from the retrieved Version 4 tables

There are 264 patient records in the clinical, treatment, and CT-availability tables. The MRI availability table has 554 patient-timepoint rows. The GTV availability table has 533 rows with gtv=1: 261 at t0, 160 at t1, and 112 at t2. The gtv_type field distinguishes 191 manually delineated baseline contours from 342 generated contours in the available-mask rows.

| Pair | GTV pairs and published RANO labels | CR | PR | SD | PD |
|---|---:|---:|---:|---:|---:|
| t0 to t1 | 160 | 1 | 16 | 105 | 38 |
| t0 to t2 | 112 | 0 | 18 | 64 | 30 |
| t1 to t2 | 107 | 0 | 6 | 71 | 30 |

All labeled pairs have corresponding GTV-availability entries at both endpoints. For t0-to-t1, 137 pairs use a manually delineated t0 mask and a generated t1 mask; 23 use generated masks at both times. The t0-to-t2 split is 97 manual/generated and 15 generated/generated. Every t1-to-t2 pair uses generated masks at both times. Thus the public RANO categories are deterministic labels derived from the same GTV volumes being assessed; they are not independent expert RANO calls.

The dataset paper reports that generated contours were validated by five radiation oncologists on 44 sampled contours, with mean Dice 0.97, mean HD95 1.87 mm, and mean ASSD 0.31 mm. This is segmentation-contour validation, not independent validation of the longitudinal RANO category labels.

## Scientific fit and claim boundary

The dataset can support a focused methods study of volumetric RANO category stability under controlled GTV boundary perturbations. The strongest primary pair is t0 to t1 (160 patients; 38 PD versus 122 non-PD), with t0-to-t2 and t1-to-t2 as secondary interval analyses. CR-specific inference is not supportable because there is only one CR at t0-to-t1 and none in the other pairs.

The primary analysis must be framed as a controlled geometric sensitivity analysis, not diagnostic accuracy, prediction accuracy, or agreement with an independent clinical reference. A defensible plan is to perturb each endpoint mask with signed-distance-based 3D dilation/erosion in millimetres, recalculate volume changes and RANO 2.0 classes using the published thresholds, and report patient-level class-flip rates and uncertainty intervals. Prespecify how zero-volume masks, empty erosions, connected components, voxel spacing, and mixed manual/generated source masks are handled. Report separate results for t0-manual/t1-generated versus generated/generated pairs; do not pool away that provenance difference.

A reproducibility check should first recompute unperturbed volume-change percentages and labels from the official Version 4 GTV volume columns and verify exact agreement with the published TSV. This can be completed from the retrieved metadata before any image download. Image-based perturbation is gated on verified geometry, voxel spacing, and representative visual QC.

## Retrieval constraint and next gate

The standard public NBIA Search API did not return CFB-GBM from its collection index, while TCIA lists the image package as requiring IBM Aspera Connect. Therefore, this audit does not establish a safe mask-only download path. Do not fetch the full 208 GB archive just to test the study.

Next, verify whether TCIA's Aspera manifest or a documented sample package permits retrieval of selected patient/timepoint GTV masks. Record the exact selected-mask byte size before transfer and confirm adequate free space on V:. If selective retrieval is not supported, pause image-based work and decide whether the metadata-only volume-threshold sensitivity analysis is worth pursuing as a narrower project. Do not describe that proxy analysis as millimetre-based contour robustness.

## Provenance files retrieved

- CFB-GBM_clinical_data_v03_20260619.tsv (264 rows)
- CFB-GBM_treatment_data_v02_20260129.tsv (264 rows)
- CFB-GBM_treatment_imaging_availability_v03_20260619.tsv (536 rows)
- CFB-GBM_ct_availability_v02_20260129.tsv (264 rows)
- CFB-GBM_mri_availability_v02_20260129.tsv (554 rows)
- CFB-GBM_rano_criteria_v04_20260909.tsv (165 rows)
- CFB-GBM_column_descriptions_v03_20260619.tsv (39 rows)

## Reproducibility and file-level access check (2026-10-11)

Using the official RANO 2.0 thresholds stated in the dataset paper (CR: no measurable tumour; PR: volume reduction at least 65%; PD: volume increase at least 40%; otherwise SD), published labels were recomputed from the Version 4 t0/t1/t2 GTV volume columns. The rounded source volumes reproduced all 160 t0→t1, 112 t0→t2, and 107 t1→t2 published labels (379/379; zero mismatches).

The public TCIA Aspera package landing page is browsable by patient and timepoint and exposes individual GTV files with per-file download controls. For example, a participant at t0 lists 1_t0_gtv.nii.gz (111.87 KB). This confirms the archive is not limited to an all-or-nothing 208 GB transfer. However, the individual download action requires IBM Aspera Connect; no mask transfer was started and no imaging files were downloaded. V: had about 215.8 GB free during the audit, which is insufficient to retain a 208 GB archive with safe working headroom. The plan remains a selective mask-only transfer, with image QC limited to a small prespecified sample if possible.

## Aggregate figure

The aggregate-only, publication-format cohort readiness figure is available in PDF, SVG, and 360-dpi PNG form under docs/CFB_GBM_METADATA_REPRODUCIBILITY/figures/. It visualizes longitudinal GTV availability, published derived RANO category composition, and the manual/generated mask-source mix. The figure states that these categories are derived from the same GTV volumes and are not independent expert response calls.

## Clinical endpoint boundary

The dataset paper places t0 about one week before radiochemotherapy and t1/t2 at later follow-ups. RANO 2.0 recommends the first post-radiotherapy scan as the reference for treatment response in newly diagnosed glioma. Consequently, these Version 4 t0-based pairwise labels are dataset-derived volumetric response labels using RANO 2.0 thresholds; they are not complete clinical RANO 2.0 calls. The robustness study will analyze sensitivity of the released labels, not validate clinical response assessment.

## Transfer route recheck (2026-10-11)

The current [TCIA collection page](https://www.cancerimagingarchive.net/collection/cfb-gbm/) identifies the 208 GB NIfTI image package as requiring IBM Aspera Connect. The TCIA page exposes a public Faspex package link. Aspera Connect 4.2.19 is installed, but the Codex in-app browser available for this session renders Faspex only as an offline loading shell; the package file listing and selective transfer controls are unavailable there. No image transfer has started. The associated [dataset processing repository](https://github.com/AurelienCD/CFB-GBM) publishes processing scripts, not a mirror of the MRI or segmentation files. Do not repeat the completed Connect installation step or fetch the collection-wide package. Resume from the package link in a browser with the Connect integration available, select only paths listed in the local 449-file manifest, and verify the transferred file list and total size before analysis. The current session does not expose such a browser.
