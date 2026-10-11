"""Schema-aware, conservative audit of the public LUMIERE CSV tables."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

RATING_COLUMN = "Rating (according to RANO, PD: Progressive disease, SD: Stable disease, PR: Partial response, CR: Complete response, Pre-Op: Pre-Operative, Post-Op: Post-Operative)"
RATIONALE_COLUMN = "Rating rationale (CRET: complete resection of the enhancing tumor, PRET: partial resection of the enhancing tumor, T2-Progr.: T2-Progression, L: Lesion)"


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def rationale_flags(text: str) -> dict[str, bool]:
    s = (text or "").casefold()
    return {
        "mentions_target_lesion": bool(re.search(r"\btarget\s*l(?:esion)?\b|\btl\b", s)),
        "mentions_new_lesion": bool(re.search(r"\bnew\b.{0,35}\b(?:target|non.?target|measurable|non.?measurable)?\s*l(?:esion)?\b|\bnew\s+lesion", s)),
        "mentions_t2_progression": "t2-progr" in s or "t2 progr" in s or "t2-progression" in s,
        "mentions_nonmeasurable": "non-measurable" in s or "non measurable" in s,
        "mentions_early_window": "less than 3 months" in s or "less than three months" in s or "< 3 months" in s,
        "mentions_treatment_effect": any(x in s for x in ("pseudo-progression", "pseudoprogression", "radiation", "avastin", "bevacizumab")),
        "mentions_dimensions": bool(re.search(r"\d+(?:\.\d+)?\s*mm\s*[x×]\s*\d+(?:\.\d+)?\s*mm", s)),
    }


def audit_lumiere(
    ratings_path: str | Path,
    completeness_path: str | Path | None = None,
    imaging_root: str | Path | None = None,
) -> tuple[dict, list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    rows = read_csv(ratings_path)
    if not rows:
        raise ValueError("Ratings CSV contains no data rows.")
    missing = [c for c in ("Patient", "Date", RATING_COLUMN, RATIONALE_COLUMN) if c not in rows[0]]
    if missing:
        raise ValueError(f"Unexpected LUMIERE ratings schema; missing columns: {missing}")
    if imaging_root is not None and completeness_path is None:
        raise ValueError("An imaging root can only be audited together with the completeness CSV.")
    if imaging_root is not None and not Path(imaging_root).is_dir():
        raise ValueError(f"Imaging root is not a directory: {imaging_root}")

    review_rows: list[dict[str, str]] = []
    unmatched_visit_keys: list[dict[str, str]] = []
    imaging_key_mismatches: list[dict[str, str]] = []
    rating_image_unmatched: list[dict[str, str]] = []
    rating_key_collisions: list[dict[str, str]] = []
    rating_counts: Counter[str] = Counter()
    rows_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    patient_ids: set[str] = set()
    dimensions_n = 0
    candidate_n = 0
    for row in rows:
        rows_by_key[(row.get("Patient", ""), row.get("Date", ""))].append(row)
        rating = (row.get(RATING_COLUMN) or "").strip() or "[blank]"
        rationale = (row.get(RATIONALE_COLUMN) or "").strip()
        flags = rationale_flags(rationale)
        rating_counts[rating] += 1
        patient_ids.add(row.get("Patient", ""))
        if flags["mentions_dimensions"]:
            dimensions_n += 1
        # Candidate is deliberately a human-review queue, never final eligibility.
        candidate = flags["mentions_dimensions"] and flags["mentions_target_lesion"] and not any(
            flags[k] for k in ("mentions_new_lesion", "mentions_t2_progression", "mentions_nonmeasurable", "mentions_early_window", "mentions_treatment_effect")
        )
        candidate_n += int(candidate)
        less_than_3m_flag = (row.get("LessThan3Months") or "").strip()
        nonmeasurable_flag = (row.get("NonMeasurableLesions") or "").strip()
        source_flag_excluded = "x" in less_than_3m_flag.casefold() or "x" in nonmeasurable_flag.casefold()
        review_rows.append({
            "patient_id": row.get("Patient", ""),
            "visit_id": row.get("Date", ""),
            "expert_rating": rating,
            "rationale": rationale,
            **{k: str(v).lower() for k, v in flags.items()},
            "candidate_measurement_driven_for_review_only": str(candidate).lower(),
            "less_than_3_months_source_flag": less_than_3m_flag,
            "nonmeasurable_source_flag": nonmeasurable_flag,
            "dimension_and_source_flags_screen_only": str(flags["mentions_dimensions"] and not source_flag_excluded).lower(),
            "final_eligibility": "REQUIRES_HUMAN_ADJUDICATION",
        })

    for (patient_id, visit_id), key_rows in sorted(rows_by_key.items()):
        if len(key_rows) < 2:
            continue
        ratings = sorted({(r.get(RATING_COLUMN) or "").strip() or "[blank]" for r in key_rows})
        rationales = sorted({(r.get(RATIONALE_COLUMN) or "").strip() for r in key_rows})
        rating_key_collisions.append({
            "patient_id": patient_id,
            "visit_id": visit_id,
            "row_count": str(len(key_rows)),
            "distinct_rating_count": str(len(ratings)),
            "ratings": " | ".join(ratings),
            "distinct_rationale_count": str(len(rationales)),
            "rationales": " || ".join(rationales),
            "resolution": "exclude_key_pending_source_resolution",
        })

    summary: dict = {
        "source": Path(ratings_path).name,
        "n_rows": len(rows),
        "n_unique_patients": len(patient_ids),
        "n_unique_patient_visit_keys": len(rows_by_key),
        "n_duplicate_patient_visit_keys": len(rating_key_collisions),
        "n_rows_in_duplicate_patient_visit_keys": sum(int(r["row_count"]) for r in rating_key_collisions),
        "n_duplicate_keys_with_rating_conflict": sum(int(r["distinct_rating_count"]) > 1 for r in rating_key_collisions),
        "n_duplicate_keys_with_rationale_conflict": sum(int(r["distinct_rationale_count"]) > 1 for r in rating_key_collisions),
        "rating_counts": dict(sorted(rating_counts.items())),
        "n_rationales_with_explicit_dimensions": dimensions_n,
        "n_candidate_measurement_driven_review_queue": candidate_n,
        "eligibility_warning": "Heuristic counts are a review queue only. The rationale is free text; no visit is automatically included in the primary analysis.",
    }
    if completeness_path:
        completeness = read_csv(completeness_path)
        completeness_keys = {(c.get("Patient", ""), c.get("Timepoint", "")) for c in completeness}
        timepoints_by_patient: dict[str, set[str]] = {}
        for c in completeness:
            timepoints_by_patient.setdefault(c.get("Patient", ""), set()).add(c.get("Timepoint", ""))
        summary["completeness_source"] = Path(completeness_path).name
        summary["completeness_rows"] = len(completeness)
        summary["completeness_columns"] = list(completeness[0]) if completeness else []
        for r in rows:
            patient_id = r.get("Patient", "")
            visit_id = r.get("Date", "")
            if (patient_id, visit_id) not in completeness_keys:
                unmatched_visit_keys.append({
                    "patient_id": patient_id,
                    "rating_timepoint": visit_id,
                    "completeness_timepoints": ";".join(sorted(timepoints_by_patient.get(patient_id, set()))),
                    "resolution": "unresolved_no_exact_key",
                })
        summary["rating_rows_without_completeness_match"] = len(unmatched_visit_keys)
        summary["patients_with_unmatched_rating_keys"] = len({r["patient_id"] for r in unmatched_visit_keys})
        if imaging_root:
            root = Path(imaging_root)
            folder_keys = {
                (patient_dir.name, visit_dir.name)
                for patient_dir in root.glob("Patient-*")
                if patient_dir.is_dir()
                for visit_dir in patient_dir.glob("week-*")
                if visit_dir.is_dir()
            }
            for patient_id, visit_id in sorted(completeness_keys ^ folder_keys):
                in_completeness = (patient_id, visit_id) in completeness_keys
                imaging_key_mismatches.append({
                    "patient_id": patient_id,
                    "visit_id": visit_id,
                    "in_completeness": str(in_completeness).lower(),
                    "in_imaging_folders": str(not in_completeness).lower(),
                })
            summary["completeness_rows_without_imaging_folder"] = sum(
                key not in folder_keys for key in completeness_keys
            )
            summary["imaging_folders_without_completeness_row"] = sum(
                key not in completeness_keys for key in folder_keys
            )
            summary["patients_with_completeness_imaging_key_mismatches"] = len({
                row["patient_id"] for row in imaging_key_mismatches
            })
            rating_keys = {(r.get("Patient", ""), r.get("Date", "")) for r in rows}
            matched_unique_keys = rating_keys & folder_keys
            ambiguous_keys = { (r["patient_id"], r["visit_id"]) for r in rating_key_collisions }
            summary["unique_rating_keys_with_exact_image_folder"] = len(matched_unique_keys)
            summary["unique_exact_image_keys_excluding_collisions"] = len(matched_unique_keys - ambiguous_keys)
            candidate_keys = {
                (r["patient_id"], r["visit_id"])
                for r in review_rows
                if r["candidate_measurement_driven_for_review_only"] == "true"
            }
            summary["candidate_rows_exact_image_key_excluding_collisions"] = len(
                candidate_keys & matched_unique_keys - ambiguous_keys
            )
            dimension_screen_keys = {
                (r["patient_id"], r["visit_id"])
                for r in review_rows
                if r["dimension_and_source_flags_screen_only"] == "true"
            }
            eligible_screen_keys = dimension_screen_keys & matched_unique_keys - ambiguous_keys
            eligible_screen_rows = [
                r for r in review_rows
                if r["dimension_and_source_flags_screen_only"] == "true"
                and (r["patient_id"], r["visit_id"]) in eligible_screen_keys
            ]
            summary["dimension_rows_after_source_flag_screen_exact_folder_and_collision_exclusion"] = len(eligible_screen_rows)
            summary["patients_with_dimension_rows_after_source_flag_screen"] = len({r["patient_id"] for r in eligible_screen_rows})
            summary["expert_rating_counts_in_dimension_source_flag_screen"] = dict(sorted(Counter(r["expert_rating"] for r in eligible_screen_rows).items()))
            summary["patients_with_two_or_more_dimension_source_flag_screen_visits"] = sum(
                count >= 2 for count in Counter(r["patient_id"] for r in eligible_screen_rows).values()
            )
            unmatched_rating_keys = sorted(rating_keys - folder_keys)
            rating_image_unmatched = [
                {
                    "patient_id": patient_id,
                    "rating_timepoint": visit_id,
                    "resolution": "no_exact_image_folder_key",
                }
                for patient_id, visit_id in unmatched_rating_keys
            ]
            summary["rating_rows_with_exact_image_folder"] = sum(
                (r.get("Patient", ""), r.get("Date", "")) in folder_keys for r in rows
            )
            summary["rating_rows_without_exact_image_folder"] = sum(
                (r.get("Patient", ""), r.get("Date", "")) not in folder_keys for r in rows
            )
            summary["unique_rating_keys_without_image_folder"] = len(unmatched_rating_keys)
            summary["patients_with_rating_keys_without_image_folder"] = len({
                patient_id for patient_id, _ in unmatched_rating_keys
            })
    return summary, review_rows, unmatched_visit_keys, imaging_key_mismatches, rating_image_unmatched, rating_key_collisions


def write_audit(
    summary: dict,
    review_rows: list[dict[str, str]],
    out_dir: str | Path,
    unmatched_visit_keys: list[dict[str, str]] | None = None,
    imaging_key_mismatches: list[dict[str, str]] | None = None,
    rating_image_unmatched: list[dict[str, str]] | None = None,
    rating_key_collisions: list[dict[str, str]] | None = None,
) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (out / "rationale_review_queue.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(review_rows[0]) if review_rows else ["patient_id", "visit_id"])
        writer.writeheader()
        writer.writerows(review_rows)
    if unmatched_visit_keys is not None:
        fields = ["patient_id", "rating_timepoint", "completeness_timepoints", "resolution"]
        with (out / "unmatched_visit_keys.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(unmatched_visit_keys)
    if imaging_key_mismatches is not None:
        fields = ["patient_id", "visit_id", "in_completeness", "in_imaging_folders"]
        with (out / "completeness_imaging_key_mismatches.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(imaging_key_mismatches)
    if rating_image_unmatched is not None:
        fields = ["patient_id", "rating_timepoint", "resolution"]
        with (out / "rating_rows_without_image_folder.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rating_image_unmatched)
    if rating_key_collisions is not None:
        fields = ["patient_id", "visit_id", "row_count", "distinct_rating_count", "ratings", "distinct_rationale_count", "rationales", "resolution"]
        with (out / "rating_key_collisions.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rating_key_collisions)
