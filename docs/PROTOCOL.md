# TumorLens analysis protocol — archived operational plan

> **Status: superseded for confirmatory research.** This plan operationalizes the LUMIERE
> expert-reference/deferral question. The dataset feasibility gate failed and that claim was
> retired before outcome analysis. Do not read the steps below as an active analysis protocol.
> v1 is a descriptive LUMIERE study: [`V1_RESULTS.md`](V1_RESULTS.md). The CFB-GBM and UPENN-GBM
> cohorts were considered and not pursued. Index of all documents: [`README.md`](README.md).

**Controlling preregistration:** [`../PREREGISTRATION.md`](../PREREGISTRATION.md), including its append-only deviations. This document makes the preregistered boundary-fragility study operational. It does not replace the registered estimands or report outcome results.

## Main question

How much can small, uniform changes to the enhancing-tumour boundary alter automated bidimensional RANO-style calls, and can that fragility or disagreement between the released segmentation methods identify calls that disagree with the available expert reference?

## Analysis order

1. Reproduce measurement and response calculations on controlled geometric phantoms and compare the implementation with published/source definitions.
2. Audit source files, visit keys, segmentation label semantics, affine/axis conventions and missingness.
3. Blindly curate the measurement-supported subset under [`RATIONALE_CODING_MANUAL.md`](RATIONALE_CODING_MANUAL.md), without seeing segmentation disagreement or result metrics. Preserve measurement-based, mixed, non-measurement-based and indeterminate visits separately.
4. Freeze a patient-level manifest, rule version, protocol hash and exclusion flow before calculating any primary comparisons.
5. Estimate boundary flip margins and method agreement. Compare calls against expert labels only on the prespecified subset; describe how sparse and response-imbalanced that subset is.
6. Treat selective risk–coverage comparison from `tumorlens analyze` as exploratory. Do not use it to replace the preregistered boundary-fragility endpoint.

## Estimands and reference

- **Boundary fragility:** smallest absolute uniform contour offset (millimetres), applied to all visits in a patient, that changes that visit's algorithmic response call; summarize flip frequencies at the preregistered 1, 2 and 3 mm thresholds.
- **Measurement agreement:** automated SPD divided by expert SPD, plus patient-clustered Bland–Altman summaries, using visits with an independently verified expert measurement.
- **Direction agreement:** agreement in change from the nadir where both expert and method-specific longitudinal values are available.
- **Expert-call discordance:** secondary/exploratory comparison against the released rating, not diagnostic truth. Report separately by method and label class. The dataset has strong ascertainment imbalance because free-text dimensions occur mostly with progression calls.
- **Deferral curves:** optional exploratory analysis of deferral scores versus threshold proximity only if cohort size and event counts support stable patient-level intervals. No statistical guarantee is implied.

## RANO and segmentation rules

Keep `src/tumorlens/rano.py` as the preregistered bidimensional measurement/call implementation. `src/tumorlens/response.py` provides separately named threshold-only calculations and must not silently substitute RANO 2.0 thresholds into the preregistered analysis. The full clinical criteria require timing, confirmatory scans and clinical context not represented by a contour alone.

Before comparing voxelwise masks, orient/resample each source to a documented reference grid using nearest-neighbour interpolation for labels. Preserve original NIfTI files and affine metadata. Volume is calculated from voxel count times physical voxel volume. For SPD, document the axial-plane selection, lesion correspondence, measurable-lesion rules and whether multiple target lesions are summed. The largest-connected-component convenience function cannot be assumed equivalent to the expert's sum over target lesions.

## Statistical units and reporting

Use patients as the resampling unit; all visits from a sampled patient remain together. Report participant and visit counts, response class counts, missingness, unresolved joins, measurement eligibility and confidence intervals. Do not claim external RANO validation from a dataset without comparable adjudicated clinical labels. Do not tune thresholds on evaluation outcomes.

The existing preregistration sets the planned 10,000 patient-cluster bootstrap resamples and kill threshold. The CLI default is lower for iterative feasibility work; set `--bootstrap-reps 10000` for final preregistered summaries after freezing the manifest. If the eligible set remains below the prespecified information threshold, report a descriptive feasibility/robustness study or stop the confirmatory claim.

## Feasibility gate

Current source audit identifies 17 exact rating/completeness key mismatches, 11 rating rows without an exact image-folder match, three duplicate rating keys (two with conflicting calls), and eight completeness visit keys without an image folder plus eight image-folder keys absent from completeness for participant key. Of 605 exact-linked rating rows, only 599 unique, non-collided keys remain. The broad dimension/source-flag screen yields 110 such keys; the stricter free-text screen yields 56, with 55 PD and one PR. The preregistered feasibility threshold is not met, and the screen is highly response-imbalanced. The present dataset cannot support a confirmatory deferral or expert-call discordance claim. For descriptive image analyses, link ratings directly to folders on exact patient/timepoint keys and derive availability from the files. Keep all mismatches explicit and do not use fuzzy matching or infer that differing stored voxel grids imply invalid anatomy. Follow the non-commercial LUMIERE use condition documented for the dataset.

## Interpretation boundaries

This retrospective, single-centre dataset can support measurement reproducibility and retrospective agreement analyses. It cannot establish clinical safety, patient benefit, prospective utility, or a universal uncertainty guarantee. The visual demos use synthetic inputs and are not clinical decision support.
