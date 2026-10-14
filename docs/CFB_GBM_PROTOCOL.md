# CFB-GBM geometric robustness protocol

> **Archived (pre-v1).** This protocol was retired before any mask-derived outcome was computed; see [`CFB_GBM_STUDY_DECISION.md`](CFB_GBM_STUDY_DECISION.md). Kept for the audit trail. Current results: [`V1_RESULTS.md`](V1_RESULTS.md). Index of all documents: [`README.md`](README.md).

Version: 1.1 (pre-outcome clarification)  
Date frozen: 2026-10-11  
Status: specified before any CFB-GBM mask-derived perturbation results are calculated.  
Dataset: CFB-GBM Version 4, TCIA, CC BY 4.0.

## Research question

How often does a CFB-GBM published, dataset-derived pairwise volumetric response category change when its longitudinal GTV masks are shifted by small, physically defined boundary offsets?

This is a geometric sensitivity study of labels computed from GTV volumes. The published labels are not independent expert response calls. CFB-GBM t0 imaging is pre-treatment; for newly diagnosed glioma, RANO 2.0 recommends the first post-radiotherapy MRI as the reference baseline. Therefore, the t0-to-t1 and t0-to-t2 labels in this dataset are not complete clinical RANO 2.0 adjudications. Refer to them as CFB-GBM dataset-derived pairwise volumetric response labels, or as labels derived using RANO 2.0 volumetric thresholds. The study will not estimate clinical diagnostic accuracy, prospective prediction, or benefit to patient care.

## Cohort and endpoint

Primary interval: t0 to t1. Include all 160 patients with both released GTV masks and a published t0-to-t1 category, unless a mask is corrupt, has unusable geometry, or fails prespecified image QC. Exclusions and reasons will be counted before calculating perturbation results. No patient is excluded because of their response category or effect on a result.

Secondary intervals: t0 to t2 and t1 to t2, using the 112 and 107 available pairs respectively, subject to the same file integrity and geometry checks.

Primary endpoint: patient-level proportion whose published dataset-derived category changes under at least one endpoint-specific signed-distance perturbation of ±1 mm. The primary estimate is the worst-case flip indicator among four combinations: (dilate baseline, dilate follow-up), (dilate baseline, erode follow-up), (erode baseline, dilate follow-up), and (erode baseline, erode follow-up). This deliberately allows contour errors at the two timepoints to differ.

Secondary endpoints:
- Proportion of pairs whose category changes under any allowed perturbation at radii 0.5, 1, 1.5, 2, 2.5, and 3 mm.
- Fraction of perturbation combinations that change the category.
- Change in relative volume reduction and transition matrix of published-to-perturbed category.
- Same summaries by source-mask pairing (manual/generated versus generated/generated) and by interval.
- A sensitivity analysis applying the same signed offset to both endpoint masks, to distinguish shared systematic boundary shift from independent endpoint errors.

CR-specific estimates will be descriptive only because the primary interval contains one CR.

## Mask handling and perturbations

Use the released binary GTV NIfTI masks and their own affine-derived voxel spacing. Preserve all GTV components; do not select the largest component. Perturb using a 3D Euclidean distance transform evaluated with NIfTI affine-derived voxel spacing; do not use voxel-count morphology that ignores spacing. For radius r, dilation adds background voxel centres whose physical Euclidean distance to foreground voxel centres is <= r; erosion retains foreground voxel centres whose physical distance to the nearest background voxel centre is > r. Implement with scipy.ndimage.distance_transform_edt and explicit physical-axis sampling. These are voxel-centre approximations to geometric offsets; report grid spacing and discretization limits.

Read masks without resampling. Record dimensions, affine, voxel spacing, unique values, voxel count, physical volume, and file hash. Mask values and affine must be finite, the affine nonsingular, and voxel axes orthogonal within 1e-5; the spacing-only distance transform cannot handle shear. Baseline masks must be non-empty. A follow-up mask may be empty only when its published volume is zero and its category is CR. An empty follow-up mask remains empty under perturbation because it has no defined contour surface to offset. Validate that each pair has compatible physical orientation and that the released RANO volumes agree with mask-derived unperturbed volumes within rounding tolerance. If images are used for QC, inspect the T1-Gd image and mask overlay without changing the mask.

If baseline erosion becomes empty, that perturbation combination is not evaluable and is counted as such; do not silently call it a response. If follow-up erosion becomes empty while baseline remains measurable, classify as CR under the dataset's volumetric rule. Report the number of non-evaluable perturbation combinations at each radius. No hole filling, smoothing, component removal, or contour repair is allowed.

## Label recalculation

Recalculate pairwise dataset-derived categories with the CFB-GBM paper's stated thresholds: CR if follow-up volume is zero; PR if relative volume reduction is at least 65%; PD if relative volume increase is at least 40%; otherwise SD. Apply the same rule to the original masks and verify that their categories match the Version 4 RANO table before perturbation analysis. This pairwise rule reproduces the dataset's derived labels, not a complete clinical RANO adjudication. The pre-treatment t0 reference differs from RANO 2.0's recommended post-radiotherapy reference scan for newly diagnosed glioma.

## Statistical summaries

The patient is the sampling unit. For each interval and radius, report numerator/denominator, percentage, and a two-sided 95% percentile bootstrap interval using 10,000 patient-level resamples and fixed seed 20261011. Primary interval confidence limits are descriptive uncertainty intervals; no significance claim is planned. Report source-mask strata separately and show their denominators. Do not bootstrap voxels, perturbation configurations, or repeated timepoints as independent observations.

## Visual and reporting plan

Primary figure: a multi-panel figure with cohort/mask flow, dataset-derived category-flip rate versus boundary radius with 95% patient-bootstrap intervals, and category transitions at 1 mm. Secondary figure: representative overlays selected by a fixed random seed, showing original and perturbed contours on T1-Gd images. All examples must be de-identified and labeled as research visualizations.

## Data integrity, transparency, and deviations

Preserve the downloaded TCIA source TSVs unchanged. Keep masks, image files, identifiers, and patient-level calculations out of the portable archive. Publish only aggregate tables and figures. Record software versions, input hashes, inclusion/exclusion counts, and the random seed. Any change to this protocol after calculating perturbation outcomes must be logged below with date, reason, and affected estimands before further analysis.

## Feasibility gate

The metadata audit verified 160 primary pairs and exact reproduction of 379/379 published pairwise labels. Image-based analysis proceeds only after selective transfer of the prespecified GTV masks, geometry validation, and a small outcome-independent image-overlay QC. The complete 208 GB image archive will not be downloaded for this analysis.



## Version history

Version 1.1 clarifies before image outcomes that the CFB-GBM pairwise labels are dataset-derived threshold labels and are not complete clinical RANO 2.0 adjudications, because t0 is pre-treatment while RANO 2.0 recommends a post-radiotherapy reference scan for newly diagnosed glioma. It changes terminology only; cohort, perturbation estimand, thresholds, bootstrap, and planned outputs are unchanged.

## Pre-outcome image QC sample lock (2026-10-11)

Before calculating any mask perturbation outcomes, select six patients from the 160 primary t0-to-t1 pairs with T1-Gd availability at both endpoints. Rank eligible patient IDs by the ascending SHA-256 hexadecimal digest of UTF-8 `20261011:<patient_id>` and take the first six. Retrieve their t0 and t1 T1-Gd volumes for geometry/overlay QC and the representative contour figure. Keep the selected IDs and image paths in the ignored local `results/cfb_gbm_robustness/required_qc_images.csv`; report only the sample count and seed in aggregate outputs. This pre-outcome addendum fixes the visualization sample and does not change the primary estimand or statistical analysis.


## Pre-outcome QC execution gate (2026-10-11)

The locked 12 T1-Gd/GTV overlays are generated with `tumorlens cfb-qc-overlays` into a local gallery and review template. The reviewer records each timepoint as checked and usable with reviewer initials, without access to response labels or perturbation outputs. The robustness command requires the completed review file and stops unless it contains exactly the locked patient/timepoint rows, all marked checked and usable. A zero-voxel mask is displayed without a contour and must be confirmed as the expected zero-volume follow-up. Any unusable overlay or apparent systematic misalignment stops the analysis for investigation; it is not silently excluded. This is an operational guard for the already prespecified outcome-independent QC sample and does not change the cohort, endpoint, perturbation radii, or statistical plan.