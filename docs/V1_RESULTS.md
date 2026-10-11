# TumorLens v1 results: LUMIERE (descriptive)

Date: 2026-10-11. Rules: [`PREREGISTRATION.md`](../PREREGISTRATION.md), plan of 2026-10-10 plus the dated deviations of 2026-10-11, all committed before any automated measurement was computed (commits 21dbedf and 2b9a1db precede the results commit). Numbers: [`reports/v1/v1_results.json`](../reports/v1/v1_results.json); tables generated from it: [`reports/v1/v1_tables.md`](../reports/v1/v1_tables.md). Patient-level measurements stay local and are not published.

## What was done

Both released segmentations (DeepBraTumIA, HD-GLIO-AUTO) were measured on every LUMIERE visit folder: 638 folders, 599 with readable masks for each tool. Each enhancing mask was measured the RANO way (largest 3D lesion, its largest slice, longest diameter and longest perpendicular) at 13 boundary offsets from -3 to +3 mm. No model was trained or run; the masks ship with the dataset.

## Headline findings

1. **The expert-measured visits are almost all progression.** 110 visits from 49 patients carry an expert bidimensional measurement: 106 PD, 4 PR, no SD or CR. Every agreement number below describes progression scans, not response assessment in general.
2. **Automated SPD runs larger than the expert's.** Median automated/expert ratio 1.38 (95% CI 1.31 to 1.49) for DeepBraTumIA and 1.35 (1.22 to 1.44) for HD-GLIO-AUTO on 102 visits. Limits of agreement are wide (about -1,600 to +2,500 mm²). When the expert summed several lesions and v1 measured one, the ratio falls below 1 (0.81 and 0.91, n = 15).
3. **Direction agreement is in the range Suter et al. reported.** On 43 consecutive expert-measured pairs (17 patients), HD-GLIO-AUTO volume agrees with the expert's direction of change in 83.7% (72.2 to 97.0), against 81.1% in Suter et al. 2023. DeepBraTumIA volume: 79.1% (67.3 to 94.1). The preregistered change-from-nadir version: 88.4% (HD-GLIO-AUTO) and 81.4% (DeepBraTumIA). Intervals are wide because there are only 17 patients.
4. **Automated calls are fragile to where the edge is drawn.** Moving every boundary in a series by the same 1 mm changes 17.1% (12.4 to 22.7) of HD-GLIO-AUTO calls and 28.3% (22.2 to 33.9) of DeepBraTumIA calls; within 2 mm, 37.7% and 54.6%.
5. **The tools often see no enhancing tumour where the expert called progression.** Of 222 expert-PD follow-ups with a readable mask, HD-GLIO-AUTO found no enhancing voxel (automated CR) in 36 and DeepBraTumIA in 16. This is descriptive, not a preregistered analysis.
6. **Two problems in the released files.** The DeepBraTumIA feature table names label 1 "Necrosis" and label 2 "Contrast-enhancing"; the tool's own volume file and the contrast signal show the reverse ([label check](LABEL_VERIFICATION.md)). And for the 514 visits whose CT1 is stored in PIR orientation, the native-space HD-GLIO-AUTO mask is rotated 180 degrees in plane relative to CT1 (median Dice with DeepBraTumIA 0.00 as stored, 0.74 after the rotation; [`reports/v1/mask_alignment.json`](../reports/v1/mask_alignment.json)). The rotation was found after the results; it changes no number above, because each tool is measured on its own grid, but it matters for any overlay or voxelwise comparison.

Full tables: [`reports/v1/v1_tables.md`](../reports/v1/v1_tables.md).

## How to read these numbers

- **Not an exact replication of Suter et al.** They used BraTumIA (not DeepBraTumIA) and had expert measurements at more time points than the released rating sheet carries. v1 uses their method (sign of change between consecutive measured follow-ups, automated volume against expert SPD) on the subset the release supports.
- **Part of the size excess is the measuring convention.** v1 measures the outline through pixel corners. On disc phantoms at 1 mm pixels this inflates SPD by 9 to 14 percent for 12 to 30 mm lesions (4 to 9 percent at 0.5 mm). The convex hull of a lesion also spans any cavity inside an enhancing rim, which a reader would not measure. Neither was corrected after seeing results.
- **The 0.5 mm offset is below the voxel size.** Most masks are on 1 mm grids, where a 0.5 mm grow or shrink changes no voxel. The near-zero flip share at 0.5 mm reflects that, not stability. The first real step is 1 mm (one voxel layer).
- **Calls are measurement-driven.** No confirmation scans, steroids, clinical status or non-enhancing disease. The baseline is the expert's post-operative scan, not a post-radiotherapy scan, and a post-operative baseline with no measurable disease makes any later measurable lesion PD. Those rules are in the preregistration and add to fragility.
- **Agreement between automated and expert calls was not a planned analysis** and is shown only as context. Analysis 4 (does fragility flag disagreement with the expert) was not run: 110 measured visits, almost all PD, cannot support it.

## Limits

One centre (Bern), 91 patients, 2008 to 2013. The expert measurement is free text parsed by a pattern (all 110 rows parsed). One automated lesion per visit, while 17 expert visits sum several. DeepBraTumIA was trained on pre-operative scans. Bootstrap intervals resample patients (10,000 resamples) but do not account for the choice of measured set.

## Reproduce

```bash
python scripts/verify_labels.py data/raw/lumiere reports/v1/label_check.json
python scripts/run_v1_measure.py data/raw/lumiere/Imaging results/v1/measurements.csv --workers 4
python scripts/run_v1_analysis.py results/v1/measurements.csv data/raw/lumiere results/lumiere-audit reports/v1
python scripts/check_mask_alignment.py data/raw/lumiere/Imaging reports/v1/mask_alignment.json
python scripts/build_viewer_cases.py data/raw/lumiere results/v1/measurements.csv docs/cases
```

On Windows set `OPENBLAS_NUM_THREADS=1` for the measurement step. The audit folder comes from `tumorlens audit` (see `docs/INITIAL_DATA_AUDIT.md`).
