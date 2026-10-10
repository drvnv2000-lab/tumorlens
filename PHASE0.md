# Phase 0: what the LUMIERE rating sheet supports

Source: `LUMIERE-ExpertRating-v202211.csv` (figshare, CC0), counted with a short script on 10 Oct 2026.
Expert measurements are only available as text inside the "Rating rationale" column
(for example `Target L.: 1 12mm x 13mm`), parsed with the pattern `NN mm x NN mm`.

| Quantity | Count |
|---|---:|
| Patients / study dates | 91 / 616 |
| Follow-up visits with a RANO rating (SD, PD, PR, CR) | 397 (79 patients) |
| Of these, with expert target-lesion measurements in the text | 149 (64 patients) |
| Same, excluding "less than 3 months" and non-measurable flags | 113 |
| Patients with 2 or more measured visits | 37 (122 visits) |

Measurements by rating: PD 129 of 253, SD 16 of 97, PR 4 of 20, CR 0 of 27.

## Reading

1. Expert measurements exist almost only for progression calls. A study of SD versus PD calls
   cannot be built from LUMIERE measurements alone, because stable visits are rarely measured.
2. 113 to 149 usable measured visits is at or below the pre-set kill threshold of about 150. LUMIERE is therefore
   descriptive here (reproduce Suter et al. 2023, calibrate the measurement code) and the
   deferral analysis needs an external set.
3. Still to check: whether MU-Glioma-Post overlaps with BraTS 2024 training data, its download size,
   and the number of automated-versus-expert disagreements.
