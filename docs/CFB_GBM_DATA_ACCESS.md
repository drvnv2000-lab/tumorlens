# CFB-GBM data access and custody

**Checked:** 2026-10-11  
**Dataset:** CFB-GBM Version 4, TCIA collection `cfb-gbm`  
**DOI:** https://doi.org/10.7937/v9pn-2f72  
**License:** CC BY 4.0 (per TCIA)

## Downloaded selection

The selective public transfer is complete. The frozen local manifest contains 449 files: 437 GTV masks and 12 T1-Gd images for the locked QC sample. All 449 expected paths were verified under `data/raw/cfb_gbm/imaging/CFB-GBM/`; the destination occupies approximately 0.56 GB. No files were placed in Downloads, and the full 208 GB collection was not downloaded.

Patient-level manifests, raw images and derived patient-level outputs remain local and must be excluded from portable archives and source control. The 12 overlays received AI-only visual review; a qualified human review is still needed before submission-level image analysis.

## Research-use decision

The downloaded masks remain available for exact volume/label reproduction, software checks, geometry validation, and descriptive contour-sensitivity analysis. The original threshold-flip endpoint is not suitable as the paper's primary result because the labels are calculated from the same volumes being perturbed. CFB-GBM also includes deceased patients only, so its time-to-death field cannot support an unbiased survival-prediction validation. See [the study decision](CFB_GBM_STUDY_DECISION.md).

The old protocol and manuscript are retained as an audit trail and marked superseded before any mask perturbation outcome was calculated. The previous run was interrupted and wrote no analysis outcomes.

## Sources

- [TCIA CFB-GBM collection](https://www.cancerimagingarchive.net/collection/cfb-gbm/)
- [Supplementary generated-mask repository](https://huggingface.co/datasets/VendenIX/CFB-GBMnnUnetPredictedMasks) — not used as a substitute for the official package.
