# TumorLens

**After glioblastoma surgery, follow-up MRIs are measured and a response call is made. How much of an automated call depends on where the tumour edge is drawn?**

On 350 real follow-up calls per tool from the LUMIERE dataset, moving every tumour edge in a patient's series by 1 mm changed **17%** of HD-GLIO-AUTO's calls and **28%** of DeepBraTumIA's.

<p align="center"><a href="https://drvnv2000-lab.github.io/tumorlens/"><img src="docs/hero.png" alt="TumorLens: a glass brain with a tumour and an uncertainty aura" width="100%"></a></p>

<p align="center"><a href="https://drvnv2000-lab.github.io/tumorlens/cases.html"><b>Five real cases</b></a> · <a href="https://drvnv2000-lab.github.io/tumorlens/"><b>Story and synthetic 3D walk-through</b></a> (laptop browser, WebGL2) · <a href="docs/V1_RESULTS.md"><b>Results</b></a></p>

![CI](https://github.com/drvnv2000-lab/tumorlens/actions/workflows/ci.yml/badge.svg)

## What v1 found (LUMIERE, descriptive)

Both segmentations released with LUMIERE were measured on all 638 visit folders (599 readable per tool) the RANO way: largest enhancing lesion, its largest slice, longest diameter and longest perpendicular. Calls compare with the nadir. Intervals are 95% patient-level bootstrap intervals (10,000 resamples).

| | HD-GLIO-AUTO | DeepBraTumIA |
|---|---|---|
| Calls changed by a 1 mm edge shift (350 calls, 73 patients) | 17.1% (12.4 to 22.7) | 28.3% (22.2 to 33.9) |
| Calls changed within 2 mm | 37.7% (31.4 to 44.4) | 54.6% (46.9 to 61.7) |
| Automated / expert size, median (102 visits) | 1.35 (1.22 to 1.44) | 1.38 (1.31 to 1.49) |
| Same direction as the expert, consecutive visits, volume (43 pairs, 17 patients) | 83.7% (72.2 to 97.0) | 79.1% (67.3 to 94.1) |

- **Suter et al. 2023 reproduced in method.** They reported 81.1% trend agreement for HD-GLIO volume against the expert's measurements; v1 gets 83.7% on the subset the released sheet supports. They used BraTumIA rather than DeepBraTumIA and had more expert-measured time points, so this is a like-for-like check, not an exact replication.
- **The expert-measured visits are almost all progression:** 110 visits, 49 patients, 106 PD and 4 PR. Size and direction agreement describe progression scans only.
- **The tools miss enhancing tumour the expert saw.** At 222 expert-PD follow-ups, HD-GLIO-AUTO found no enhancing tissue at 36 and DeepBraTumIA at 16 (descriptive).
- **Two problems in the released files**, both documented: the DeepBraTumIA feature table swaps the names of labels 1 and 2 ([label check](docs/LABEL_VERIFICATION.md)), and native-space HD-GLIO-AUTO masks for the 514 PIR-stored scans are rotated 180 degrees in plane relative to the scan ([alignment check](reports/v1/mask_alignment.json)). Neither changes a v1 number; both matter to anyone overlaying or comparing masks.

Limits, in full in [`docs/V1_RESULTS.md`](docs/V1_RESULTS.md): one centre; the expert measurement is free text; one automated lesion per visit; part of the size excess is the measuring convention (pixel-corner outline, convex hull across cavities); a 0.5 mm shift is below the voxel size; calls ignore confirmation, steroids, clinical status and non-enhancing disease.

## How we avoid fooling ourselves

- The analysis plan was committed before any automated measurement was compared with an expert one: [`PREREGISTRATION.md`](PREREGISTRATION.md). Every later change is a dated entry at the bottom, including one found after the results.
- Label meanings were checked against each tool's own code and outputs before analysis.
- No model is trained: the two segmentations ship with the dataset.
- Calls compare with the **nadir**, not the previous scan or the baseline, as RANO requires.
- Intervals resample patients, because visits from one patient are not independent.
- The planned test of whether fragility flags disagreement with the expert (analysis 4) was **not run**: 110 measured visits, almost all PD, cannot support it.
- Only aggregate results are committed. Patient-level measurements stay local.

## Relation to prior work

Suter et al. (2022, 2023) released LUMIERE and compared automated longitudinal measurements with expert ratings; TumorLens reuses their trend-agreement method as a check and adds boundary fragility. OncoSeg (Yu, 2026) maps expert RANO labels to RECIST-style categories; TumorLens implements bidimensional RANO directly. No OncoSeg code was used; this repository was written from scratch from the primary sources.

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

With LUMIERE in `data/raw/lumiere/`, the v1 pipeline is in [`docs/V1_RESULTS.md`](docs/V1_RESULTS.md#reproduce). Open `docs/index.html` or `docs/cases.html` through a local web server (`python -m http.server -d docs`).

## Licence

Code: MIT. Data: LUMIERE (Suter et al., Scientific Data 2022). Its data descriptor restricts use to non-commercial purposes, while the Figshare record lists CC0; TumorLens follows the stricter non-commercial reading. The case images and numbers in `docs/cases/` are derived from LUMIERE and are not covered by the MIT licence. Not a medical device; nothing here is clinical advice.
