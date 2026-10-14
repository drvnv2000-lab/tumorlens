# UPENN-GBM feasibility audit

> **Archived (pre-v1).** UPENN-GBM was a candidate cohort that was not pursued; v1 uses LUMIERE. Kept for the audit trail. Current results: [`V1_RESULTS.md`](V1_RESULTS.md). Index of all documents: [`README.md`](README.md).

**Audit date:** 2026-10-11  
**Status:** Metadata-only candidate audit; no UPENN imaging downloaded and no analysis outcomes calculated.

## Source files

Downloaded only the official TCIA metadata attachments to `data/raw/upenn_gbm/metadata/`:

- `UPENN-GBM_clinical_info_v1.2.csv` — SHA-256 `FD5749AE5A8D77E599E02264D961D94107752F0244E34BF0BC711A75FE0E2EC5`
- `UPENN-GBM_data_availability.csv` — SHA-256 `7A4F0EEBFA34C86A3380F2695457007936B6E24E62960B68F10FDE18A726DD89`
- `UPENN-GBM_acquisition.csv` — SHA-256 `D5C839521BA65D2176A168AAABAD1B5027DAB6123AD30EB14D5485A43DF99249`

The clinical and availability tables contain 671 scan-keyed rows. Exact `ID` matching succeeds for all 671; no fuzzy joins were used. The cohort has 611 preoperative baseline (`_11`) rows and 60 recurrence/follow-up (`_21`) rows.

## Outcome and mask availability

Among baseline rows, the availability table marks overall survival available for 452 patients, all recorded as deceased. Twenty-three additional baseline records have an Alive or Lost-to-Follow-up status and a numeric `Survival_Censor` time. Three records have “Deceased - uncertain date of death” and are not included in this strict endpoint count. The resulting metadata-only candidate is 475 exact-linked baseline records with an event/censor time and an automatic tumor segmentation marked available.

Only 146 of those 475 have a corrected tumor segmentation marked available; 145 are recorded deaths and one is censored. Thus the corrected-mask subset cannot support a reliable comparison of corrected versus automatic measurement across event and censoring groups. Most baseline KPS values are missing (127/146 among corrected-mask cases); extent of resection is available for 139/145 of the death subset. This limits adjustment and could create selection bias.

The 60 follow-up records have pathology scores (range 1–6), but neither automatic nor corrected tumor segmentation is marked available for any of them. The pathology-scored follow-up opportunity therefore cannot currently support a released-mask volume-versus-histology analysis.

The official TCIA dataset paper describes 611 preoperative baseline scans and overall-survival data for 452 patients. The official collection page notes that the NIfTI images and masks are atlas-registered and describes neuroradiologist review/correction of the released segmentation labels. See the [TCIA collection](https://www.cancerimagingarchive.net/collection/upenn-gbm/) and the [dataset paper](https://doi.org/10.1038/s41597-022-01560-7).

## Novelty and design caution

A recent 2026 preprint already examines segmentation robustness and survival-model performance in UPENN-GBM using automatic and expert-refined radiomic features. A TumorLens study using the same cohort must be clearly distinguished from that work and should not repeat a broad “robustness improves survival prediction” claim. See [the preprint record](https://arxiv.org/abs/2607.23626).

The event/censor definition must be confirmed against TCIA documentation before any model is run. The current strict count uses the explicit availability flag for the 452 event times and the numeric `Survival_Censor` field for Alive/Lost-to-Follow-up rows; ambiguous-death records are excluded. Overall survival is measured from surgery, whereas the MRI is preoperative, so the time origin does not exactly match the image date. This must be resolved or explicitly limited in any protocol.

## Decision

UPENN-GBM is a better endpoint-feasibility candidate than CFB-GBM, but the metadata alone do not establish a novel, low-bias, paper-ready primary question. No masks were selected or downloaded. Before adoption, compare the proposed estimand with the existing preprint, confirm endpoint semantics and scan-to-surgery timing, and assess whether the automatic-mask cohort supports a distinct measurement question. Do not use the 145 deceased corrected-mask cases as an unbiased survival-validation cohort.
