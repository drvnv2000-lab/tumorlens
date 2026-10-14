# LUMIERE expert-rationale coding manual (draft v1)

> **Archived (pre-v1).** Draft for a human rationale review that was not run; v1 uses the parser audit described in [`V1_RESULTS.md`](V1_RESULTS.md). Kept for the audit trail. Current results: [`V1_RESULTS.md`](V1_RESULTS.md). Index of all documents: [`README.md`](README.md).

**Purpose:** identify visits whose released free-text rationale supports a measurement-driven analysis, independently of automated segmentations and calls. This document operationalizes the existing TumorLens protocol; it does not replace the preregistered endpoint or convert text coding into clinical adjudication.

**Status:** ready for two independent human reviewers to pilot. Do not use the heuristic review queue as labels. Freeze this manual before reviewers see model or segmentation results.

## 1. Unit and source fields

The unit is one row from `LUMIERE-ExpertRating-v202211.csv`. Retain the source row in a restricted local crosswalk. For the blinded review sheet, replace `Patient` + `Date` with a random review ID and show only:

- the exact source `Rating rationale` text;
- the source `LessThan3Months` flag;
- the source `NonMeasurableLesions` flag.

Hide patient and visit identifiers, the expert rating, imaging and acquisition fields, segmentation-derived measurements, algorithm calls, and all model results. Shuffle review rows independently for each reviewer. A blank source flag means “not marked in this field”; it is not evidence that the corresponding clinical condition was absent.

Rows with unresolved rating/completeness keys can still be coded from their rating rationale. Link a rating to an image only when its patient and visit key exactly match an image-folder name; otherwise keep its scan link unresolved. Never attach a nearby scan or infer an offset.

## 2. Primary rationale class

Assign exactly one class from the text and flags shown to the reviewer:

| Code | Class | Rule |
|---|---|---|
| `MD` | Measurement-driven | The rationale explicitly ties the assessment to one or more target lesions and their measured size/dimensional change. No separate non-measurement criterion is stated as independently sufficient for the assessment. |
| `NMD` | Non-measurement-driven | The rationale clearly bases the assessment on another stated criterion and contains no usable target-lesion measurement basis. Examples include a new lesion, T2/FLAIR progression, non-measurable disease, an early post-treatment window, postoperative status, or an explicitly described treatment effect. |
| `MIXED` | Mixed basis | A target-lesion measurement is explicitly used, and the rationale also states another active criterion that could independently determine the assessment. |
| `IND` | Indeterminate | The rationale is absent, unclear, internally conflicting, or gives numbers without enough context to tell whether they are target-lesion measurements used in the assessment. |

Do not infer a rationale class from the expert rating alone. A dimensions pattern found by software is only a prompt for review; it does not establish that the dimensions belong to a target lesion or drove the rating.

## 3. Required component codes

In addition to the primary class, record each field as `YES`, `NO`, or `UNCLEAR` and cite a short text span where applicable:

- `explicit_target_measurement`: target lesion is identified and quantitative size is stated;
- `two_perpendicular_dimensions`: two dimensions for a lesion are explicit;
- `multiple_targets_or_sum`: rationale explicitly describes multiple target lesions or a sum;
- `new_lesion_basis`;
- `t2_flair_basis`;
- `nonmeasurable_basis`;
- `early_window_basis`;
- `postoperative_basis`;
- `treatment_effect_or_pseudoprogression_basis`;
- `other_nonmeasurement_basis` (copy the short evidence span and describe it).

These are text-evidence codes, not clinical truth labels. Do not silently convert missing evidence to `NO` when the text is too vague; use `UNCLEAR`.

## 4. Analysis eligibility derived after coding

Keep rationale class, measurement availability, and source exclusion flags as separate variables. Do not overwrite the original rationale or flags.

- **Strict primary candidate:** class `MD`, explicit target measurement is `YES`, and neither source exclusion flag is marked `x`.
- **Sensitivity-only candidate:** class `MIXED`, explicit target measurement is `YES`, and neither source exclusion flag is marked `x`.
- **Not a measurement candidate:** class `NMD`, or either source exclusion flag is marked `x`.
- **Unresolved:** class `IND`, an unclear exclusion flag, or an unresolved join where imaging is required.

This candidate status is not the final analysis cohort. Check the registered sample-size/kill threshold, measurement completeness, visit joins, and the frozen measurement protocol before constructing the analysis manifest. Report strict and sensitivity counts by patient and visit, and by expert-call category only after coding is locked.

## 5. Review and adjudication

1. Two reviewers independently code every rating row from the blinded sheet. Do not discuss individual cases during the independent pass.
2. Before full coding, pilot a reproducible random set of 30 rows using seed `20261011`. Clarify wording only; do not inspect outcomes or segmentation comparisons. Freeze and version this manual before continuing. If any coding rule changes, discard the pilot labels and recode those rows under the frozen version.
3. Report raw agreement and unweighted Cohen’s kappa for the four-class primary code, plus the class confusion matrix. Because visits cluster within patients, provide a patient-clustered bootstrap interval for agreement statistics where estimable. Report component-code agreement separately.
4. Resolve disagreements in a recorded adjudication meeting led by a third reviewer if available. If no third reviewer is available, both coders document their evidence and the final rationale. Unresolved cases remain `IND`; never force consensus.
5. Preserve both original reviewer sheets, adjudicated sheet, manual version, date, and a change log. Store patient-level review files locally; do not put them in the portable source archive.

## 6. Required output columns

Use one row per source rating in the restricted local adjudication file:

`review_id, reviewer_id, manual_version, rationale_text, less_than_3_months_source_flag, nonmeasurable_source_flag, rationale_class, explicit_target_measurement, two_perpendicular_dimensions, multiple_targets_or_sum, new_lesion_basis, t2_flair_basis, nonmeasurable_basis, early_window_basis, postoperative_basis, treatment_effect_or_pseudoprogression_basis, other_nonmeasurement_basis, evidence_span, reviewer_note, adjudication_status`

Maintain a separate access-restricted crosswalk from `review_id` to the source patient/timepoint key. Join to imaging only after source-key conflicts are resolved or explicitly excluded under the frozen protocol.

An empty header-only sheet is provided at `examples/rationale_adjudication_template.csv`. It contains no source patient data.
