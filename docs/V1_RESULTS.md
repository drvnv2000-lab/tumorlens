# TumorLens v1 results: LUMIERE (descriptive)

Updated 2026-10-12 after two independent reviews. Rules: [`PREREGISTRATION.md`](../PREREGISTRATION.md): the plan of 2026-10-10 and dated deviations. Analyses 1 to 3 were fixed before any automated measurement (commits 21dbedf, 2b9a1db); exploratory analysis 4 and the post hoc analyses were fixed before they were run (92c659d, cd06364). Numbers: [`reports/v1/v1_results.json`](../reports/v1/v1_results.json) and the generated [`v1_tables.md`](../reports/v1/v1_tables.md); pixel-centre sensitivity in [`v1_results_pixel_centre.json`](../reports/v1/v1_results_pixel_centre.json) and [`v1_tables_pixel_centre.md`](../reports/v1/v1_tables_pixel_centre.md); run record in [`manifest.json`](../reports/v1/manifest.json). Patient-level measurements stay local.

## What this study is, and is not

It measures how **measurement-driven response calls**, made from two released segmentations with fixed study rules, depend on measurement conventions and on a **uniform boundary offset**. It is not a validation of automated clinical response assessment. The calls ignore confirmation scans, steroids, clinical status and non-enhancing disease. The baseline is the study's post-operative baseline (the expert's "Post-Op" scan), not necessarily the clinical RANO baseline. The expert is a comparator, not a perfect reference standard.

## What was done

Both released segmentations (DeepBraTumIA, HD-GLIO-AUTO) were measured on every LUMIERE visit folder: 638 folders, 599 with readable masks per tool. Each enhancing mask was measured on its largest 3D lesion, on that lesion's largest slice, as longest diameter times longest perpendicular. This was repeated at 13 uniform boundary offsets from -3 to +3 mm, with lesion selection, measurability, nadir and call recomputed at every offset. No model was trained or run.

## Findings

Intervals are 95% patient-level bootstrap intervals (10,000 resamples).

1. **The expert-measured visits are almost all progression.** 110 visits from 49 patients carry an expert bidimensional measurement: 106 PD and 4 PR. Analyses 1 and 2 describe progression scans. Analyses 3 and 4 use a different population: 350 follow-up calls per tool in 99 series from 73 patients (222 expert PD, 128 non-PD). The two sets should not be combined into one claim.
2. **Automated SPD was higher than the expert's under the study's measurement conventions.** The median automated/expert ratio was 1.38 (1.31 to 1.49) for DeepBraTumIA and 1.35 (1.22 to 1.44) for HD-GLIO-AUTO, on 102 visits. With the pixel-centre convention (post hoc) it was 1.24 (1.16 to 1.34) and 1.20 (1.07 to 1.34). Competing explanations are not separated: outline convention, the convex hull bridging cavities, one automated lesion against the expert's sum (ratio 0.81 and 0.91 at the 15 multi-lesion visits), and segmentation differences. The pooled visit-level limits of agreement are wide, about -1,600 to +2,500 mm². Limits for repeated measurements per patient (Bland and Altman 2007, post hoc) are almost the same: -1,450 to 2,022 mm² (HD-GLIO-AUTO) and -1,623 to 2,520 mm² (DeepBraTumIA).
3. **Direction agreement was numerically similar to Suter et al. 2023.** HD-GLIO-AUTO volume moved in the expert's direction in 83.7% (72.2 to 97.0) of 43 consecutive pairs from 17 patients; Suter et al. reported 81.1%. DeepBraTumIA: 79.1% (67.3 to 94.1). This is not a replication or an equivalence result. Suter et al. used BraTumIA and more expert time points, and 17 patients give wide intervals. 4 of 43 pairs had no change in the expert's measurement. These SPD comparisons use the raw automated product. Setting it to 0 when a diameter is under 10 mm, as for calls (post hoc), changes 1 HD-GLIO-AUTO visit and 0 DeepBraTumIA visits and leaves every agreement figure the same.
4. **Automated calls were sensitive to uniform boundary offsets.** A 1 mm offset changed 17.1% (12.4 to 22.7) of HD-GLIO-AUTO calls and 28.3% (22.2 to 33.9) of DeepBraTumIA calls; within 2 mm, 37.7% and 54.6%. 163 and 106 calls did not change within 3 mm; these are censored, not "3 mm". The pixel-centre convention gives 18.9% and 30.6% at 1 mm. A uniform offset is a constrained experiment. It is not a model of real segmentation error, which varies across the outline and between scans.
5. **Exploratory analysis 4: fragility weakly discriminated disagreement with the expert call.** The fragility score (minus the flip offset) gave AUROC 0.60 (0.54 to 0.67) for HD-GLIO-AUTO and 0.65 (0.58 to 0.71) for DeepBraTumIA. Tool-vs-tool disagreement gave 0.54 (0.49 to 0.59) and 0.59 (0.53 to 0.64). Excluding calls whose rationale documents T2/FLAIR progression or a new lesion (191 calls, 57 patients), the fragility score gave 0.73 for both tools. That subset is smaller and selected, so it does not show the primary analysis was wrong. Disagreement with the expert mixes measurement error with clinical judgement, so no claim about segmentation error follows. No bootstrap resample was undefined.
6. **Absence of enhancing voxels, not absence of tumour.** At 222 expert-PD follow-ups, the HD-GLIO-AUTO mask had no enhancing voxels at 36 and DeepBraTumIA at 16 (descriptive). Expert PD can rest on new lesions, T2/FLAIR progression or clinical grounds, so this does not by itself show that the tools missed enhancing tumour.
7. **Two discrepancies in the released files.** In the released DeepBraTumIA feature table, the names of labels 1 and 2 conflict with the tool's own volume file (60/60 visits) and with the contrast signal (501/529 visits); v1 uses label 1 as enhancing ([label check](LABEL_VERIFICATION.md)). Of 514 PIR-stored scans, the native-space HD-GLIO-AUTO mask is rotated 180 degrees in plane relative to CT1 in 507 (best flip, Dice gain at least 0.1). In 6 more the same flip is best but the gain is small, and 1 is undetermined. One RAS scan improves with a single-axis flip, which is a different pattern ([`mask_alignment.json`](../reports/v1/mask_alignment.json)). An earlier entry said "all 514"; it is corrected in a dated entry. Recomputing 25 sampled PIR visits with the rotation undone gave identical measurements, to 1e-14 ([`pir_invariance.json`](../reports/v1/pir_invariance.json)). The rotation matters for overlays and voxelwise comparison, not for v1's per-tool measurements.

## Checks behind the numbers

- **Expert measurements.** All 110 rationale strings were read by hand against the parsed pairs, and 110 of 110 were transcribed correctly. 6 rows are flagged by meaning: 1 measures a non-target lesion, and 5 say the target lesion became non-measurable while still giving its dimensions. Without them (post hoc), the ratios are 1.38 and 1.32, and consecutive volume agreement is 86.8% (DeepBraTumIA) and 92.1% (HD-GLIO-AUTO) on 38 pairs.
- **Call rules.** A 15-case transition table (zero baseline, zero nadir, exact thresholds, non-measurable residual, nadir from all earlier scans, PD before PR) is in `tests/test_call_rules.py`. A mask-level test confirms that the flip offset reruns the whole pipeline. 76 tests pass.
- **Reproduction.** A fresh clone of commit aa3e822 rebuilt the audit, both measurement tables and all four result files, and every file was byte-identical to the committed versions.
- **Labels.** These were checked three ways before analysis, and on 2026-10-12 directly on the native CT1-space masks that v1 measures: in 60 sampled visits the enhancing label was the brightest on CT1 in 53/54 (DeepBraTumIA label 1) and 48/48 (HD-GLIO-AUTO label 2) ([label check](LABEL_VERIFICATION.md)).
- **Expert audit table.** The hand audit is kept as a local patient-level table; counts are in [`parser_audit.json`](../reports/v1/parser_audit.json).

## Limits

- One centre (Bern), 91 patients, 2008 to 2013.
- The expert measurement is free text.
- v1 measures one automated lesion per visit, while 17 expert visits sum several.
- The pixel-corner and pixel-centre conventions differ by about one pixel per diameter. Neither is a strict bound, and neither fixes the convex hull across cavities.
- The 0.5 mm offset is below most voxel sizes, so the first effective step is 1 mm.
- The zero-nadir rule (any measurable lesion after a non-measurable nadir is PD) is a study convention that adds to sensitivity.
- DeepBraTumIA was trained on pre-operative scans.
- Bootstrap intervals resample patients but do not account for how the measured set was selected; with 17 patients in analysis 2 they are unstable.

## Reproduce

```bash
python -m tumorlens lumiere-audit --ratings data/raw/lumiere/LUMIERE-ExpertRating-v202211.csv \
  --completeness data/raw/lumiere/LUMIERE-datacompleteness.csv --imaging-root data/raw/lumiere/Imaging --out results/lumiere-audit
python scripts/verify_labels.py data/raw/lumiere reports/v1/label_check.json
python scripts/run_v1_measure.py data/raw/lumiere/Imaging results/v1/measurements.csv --workers 4
python scripts/run_v1_measure.py data/raw/lumiere/Imaging results/v1/measurements_centre.csv --workers 4 --convention centre
python scripts/run_v1_analysis.py results/v1/measurements.csv data/raw/lumiere results/lumiere-audit reports/v1
python scripts/run_v1_analysis.py results/v1/measurements_centre.csv data/raw/lumiere results/lumiere-audit reports/v1 --label pixel_centre
python scripts/check_mask_alignment.py data/raw/lumiere/Imaging reports/v1/mask_alignment.json
python scripts/check_pir_invariance.py data/raw/lumiere/Imaging results/v1/measurements.csv reports/v1/pir_invariance.json
python scripts/build_viewer_cases.py data/raw/lumiere results/v1/measurements.csv docs/cases
```

On Windows, set `OPENBLAS_NUM_THREADS=1` for the measurement steps.
