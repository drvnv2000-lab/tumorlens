# Curated analysis manifest

> **Archived (pre-v1).** Manifest format for the early CLI workflow; v1 does not use it. Kept for the audit trail. Current results: [`V1_RESULTS.md`](V1_RESULTS.md). Index of all documents: [`README.md`](README.md).

The normalized manifest is one row per patient visit. Keep source ratings and derived calls in separate columns. Never overwrite the original CSVs.

| Column | Required | Meaning |
|---|---|---|
| `patient_id` | yes | Dataset pseudonymous patient key |
| `visit_id` | yes | Original timepoint key |
| `visit_order` | yes | Numeric chronological order within patient |
| `measurement_driven` | yes | Human-adjudicated inclusion flag; true/false |
| `eligibility_reason` | yes | Decision and rationale for primary cohort eligibility |
| `expert_call` | yes | Released expert call, normalized to CR/PR/SD/PD where applicable |
| `automated_call` | yes | Frozen threshold-only algorithmic call |
| `baseline_spd_mm2` | yes for primary | Baseline sum of products of diameters |
| `nadir_spd_mm2` | yes for primary | Smallest valid prior SPD under the pre-specified rule |
| `current_spd_mm2` | yes for primary | Current SPD for the method being assessed |
| `threshold_margin_fraction` | yes for analysis | Normalized distance to nearest active threshold (0 is on boundary) |
| `segmentation_spread_fraction` | yes for analysis | Normalized spread among the frozen method outputs |
| `measurement_method` | yes | Method/source used for the current value |
| `rule_set` | yes | Versioned threshold calculation used for automated call |
| `rationale_group` | yes | Human-coded category (`MD`, `NMD`, `MIXED`, `IND`) under [`RATIONALE_CODING_MANUAL.md`](RATIONALE_CODING_MANUAL.md) |
| `new_lesion` | yes | Explicit curated flag; unknown must not be silently false |
| `less_than_3_months` | recommended | Source criterion/timing indicator if available |
| `mask_paths` | recommended | Local-only paths; do not publish patient paths |

Use empty fields for unknown values and document why a row is not analysable. The analysis CLI expects the required score columns and patient/expert/model calls. `examples/manifest_synthetic.csv` is illustrative only and must never be included in scientific analysis.
