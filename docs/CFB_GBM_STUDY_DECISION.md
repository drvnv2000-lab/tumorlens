# CFB-GBM study decision

**Decision date:** 2026-10-11  
**Status:** Original primary question retired before outcome analysis.

## Why the threshold-flip question is not the paper question

The CFB-GBM pairwise response categories are calculated from the same t0/t1 GTV volumes that the proposed perturbation changes. Therefore, a category flip rate mainly describes how close those derived volume ratios are to the 40% and 65% cutoffs. It is a useful software sensitivity check, but it is not an independent test of clinical uncertainty, expert disagreement, or patient outcome. Keep it descriptive and label it as a same-data arithmetic sensitivity analysis.

The previous `cfb-robustness` run was interrupted before it wrote patient-level or aggregate outcomes. No flip-rate estimate from that run is available or should be reported.

## Why survival does not rescue this cohort

The official [TCIA CFB-GBM collection page](https://www.cancerimagingarchive.net/collection/cfb-gbm/) states that inclusion was restricted to deceased patients. The clinical table's `survival (weeks)` field is defined as time between death and the t0 MRI. This is a time-to-death measure for a deceased-only cohort, with no alive/censored comparison group. Associations within this selected cohort cannot validate general prognosis or a clinical response rule.

The official [RANO 2.0 paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10860967/) recommends the first post-radiotherapy MRI as the reference scan in newly diagnosed glioma. CFB-GBM's t0 scan is pre-treatment. Its provided pairwise labels are dataset-derived volumetric labels; they are not independent expert adjudications or complete clinical RANO 2.0 calls.

## Appropriate use of the downloaded files

The 437 GTV masks and 12 T1-Gd images are retained for reproducibility and software quality checks. They can support:

- Exact reproduction of the released volume-derived labels.
- Geometry, file-integrity, and overlay-QC validation.
- Descriptive sensitivity of mask volumes and derived labels to explicitly stated boundary offsets.

They do not support diagnostic accuracy, clinical uncertainty detection, prospective response prediction, or unbiased survival validation. The existing protocol and manuscript draft remain in the repository as an audit trail, marked superseded before outcomes.

## Gate for a paper-quality primary question

Before any new primary endpoint is frozen, audit a candidate public cohort for all of the following:

1. An outcome independent of the tumor-volume measurements, with event and censoring status and dates.
2. A defined imaging landmark before the outcome interval begins.
3. Clinically reviewed reference measurements or a defensible independent reference standard.
4. Adequate sample size, covariates, and license/usage terms for the planned analysis.
5. An exact, auditable imaging-to-clinical linkage with no fuzzy identifier matching.

UPENN-GBM has passed a first metadata feasibility check: 475 exact-linked baseline records have an event/censor time and an automatic tumor segmentation. However, only 146 of these have a corrected mask, and 145 of those are deaths; the pathology-scored follow-up scans have no released tumor masks. The official dataset paper reports survival from surgery, not from the preoperative scan. A 2026 preprint already studies segmentation robustness and survival modelling on this cohort. These issues leave novelty, selection bias, and outcome timing unresolved. See the [metadata audit](UPENN_GBM_FEASIBILITY.md). UPENN-GBM remains a candidate, not a selected confirmatory cohort.

## Project claim boundary

Until an independent cohort and reference outcome pass the gate above, describe TumorLens as a research prototype with a synthetic 2D measurement demo and an exploratory 3D contour-sensitivity workflow. Do not describe the current CFB-GBM work as a clinically validated uncertainty method or a completed confirmatory paper.
