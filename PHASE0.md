# Phase 0: what the LUMIERE rating sheet supports

Source: `LUMIERE-ExpertRating-v202211.csv` (figshare, CC0), counted with a short script on 10 Oct 2026.
Expert measurements are only available as text inside the "Rating rationale" column
(for example `Target L.: 1 12mm x 13mm`), parsed with the pattern `NN mm x NN mm`.

| Quantity | Count |
|---|---:|
| Patients / study dates | 91 / 616 |
| Follow-up visits with a RANO rating (SD, PD, PR, CR) | 397 (79 patients) |
| Of these, with expert target-lesion measurements in the text | 149 (64 patients) |
| Same, excluding "less than 3 months" and non-measurable flags | 113 rows before image linkage/collision review |
| Same, with exact image folder and excluding duplicate rating-key collisions | 110 keys across 49 patients |
| Patients with 2 or more visits in that screened set | 26 |

For the broad 110-key screen: PD 106, PR 4, SD 0, CR 0. A stricter text heuristic requiring explicit target-lesion language and no detected competing criterion retains 56 keys (55 PD, 1 PR). Neither screen replaces blinded human rationale coding.

## Reading

1. Expert measurements exist almost only for progression calls. A study of SD versus PD calls
   cannot be built from LUMIERE measurements alone, because stable visits are rarely measured.
2. After exact image linkage and exclusion of duplicate-key collisions, the broad screened set is 110 rows, below the preregistered feasibility gate of about 150. The stricter automated text screen is 56 rows. LUMIERE cannot support the planned confirmatory deferral analysis; use it for descriptive feasibility and measurement-pipeline work, and seek an independent cohort before testing deferral.
3. The calls are highly imbalanced (no SD/CR in the broad screened set), making expert-call discordance comparisons unsuitable for a confirmatory claim even if confidence intervals are calculated.
4. Any external cohort candidate needs a fresh license, overlap, event-count, and protocol assessment before inclusion.
