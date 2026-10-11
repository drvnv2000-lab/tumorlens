# Label verification (2026-10-11)

The analysis plan requires the contrast-enhancing label of each segmentation tool to be confirmed before any analysis. Aggregate numbers: [`reports/v1/label_check.json`](../reports/v1/label_check.json), produced by `python scripts/verify_labels.py data/raw/lumiere reports/v1/label_check.json`.

| Tool | Enhancing label | Evidence |
|---|---|---|
| HD-GLIO-AUTO | **2** (1 = non-enhancing T2/FLAIR abnormality) | Tool code: NeuroAI-HD/HD-GLIO-AUTO `scripts/run.py` (commit 6acaad8) writes `volume_contrast_enhancing_tumor_mm3` from `data == 2`; same in the LUMIERE authors' copy (ysuter/gbm-data-longitudinal, e57c5b4). Median CT1/T1 ratio 1.70 (label 2) vs 0.91 (label 1); label 2 enhances more in 424/424 visits. |
| DeepBraTumIA | **1** (2 = necrotic/non-enhancing, 3 = edema) | No public label documentation found. DeepBraTumIA's own `measured_volumes_in_mm3.json` matches label 1 to `Enhancing_Core` in 60/60 sampled visits (exact to 1 mm³). Median CT1/T1 ratio 1.64 (label 1) vs 0.89 (label 2); label 1 enhances most in 501/529 visits. |

**Discrepancy found.** The released `LUMIERE-pyradiomics-deepbratumia-features.csv` names DeepBraTumIA label 1 "Necrosis" and label 2 "Contrast-enhancing". The tool's own volume file and the contrast signal both point the other way, so v1 follows the tool's output and uses label 1 as enhancing. Where the error lies (the feature table's naming, or the mapping used to build it) is not established. Anyone using those released DeepBraTumIA features for "contrast-enhancing" tumour should check this first.

Method of the signal check: for each visit in the released pyradiomics tables, the median intensity inside each label on post-contrast T1 divided by the median on pre-contrast T1 (atlas or reference space as released). Enhancing tissue brightens after gadolinium, so its ratio is above 1.

Limits: DeepBraTumIA evidence is its own output file plus signal behaviour, not a published specification. The volume-file check used a random sample of 60 visits (seed 0).

## Native CT1-space masks (added 2026-10-12)

The checks above use the atlas-space DeepBraTumIA map and the released atlas-space features. v1 measures the native CT1-space masks, so the same 60 sampled visits were checked on those directly (`native_ct1_masks` in [`label_check.json`](../reports/v1/label_check.json)):

- The native DeepBraTumIA label volumes match DeepBraTumIA's named volumes (median ratio 1.00 for labels 1, 2 and 3).
- Median CT1 intensity relative to the brain median, on the CT1 grid: DeepBraTumIA label 1 1.47, label 2 0.78, label 3 1.00; HD-GLIO-AUTO label 2 1.49, label 1 0.99.
- The enhancing label is the brightest on CT1 in 53 of 54 visits for DeepBraTumIA (label 1) and 48 of 48 for HD-GLIO-AUTO (label 2). Visits with fewer than 20 voxels in a label are skipped, and HD-GLIO-AUTO masks of PIR-stored scans are rotated back first.
