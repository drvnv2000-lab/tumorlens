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
