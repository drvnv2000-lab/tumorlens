from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TABLES = {
    "clinical": "CFB-GBM_clinical_data_v03_20260619.tsv",
    "treatment": "CFB-GBM_treatment_data_v02_20260129.tsv",
    "availability": "CFB-GBM_treatment_imaging_availability_v03_20260619.tsv",
    "ct_availability": "CFB-GBM_ct_availability_v02_20260129.tsv",
    "mri_availability": "CFB-GBM_mri_availability_v02_20260129.tsv",
    "rano": "CFB-GBM_rano_criteria_v04_20260909.tsv",
    "dictionary": "CFB-GBM_column_descriptions_v03_20260619.tsv",
}

PAIR_FIELDS = (
    ("t0_to_t1", "t0", "t1", "size_t0 (cm3)", "size_t1 (cm3)", "rano_t0_to_t1"),
    ("t0_to_t2", "t0", "t2", "size_t0 (cm3)", "size_t2 (cm3)", "rano_t0_to_t2"),
    ("t1_to_t2", "t1", "t2", "size_t1 (cm3)", "size_t2 (cm3)", "rano_t1_to_t2"),
)
CATEGORIES = (
    "Complete Response (CR)",
    "Partial Response (PR)",
    "Stable Disease (SD)",
    "Progressive Disease (PD)",
)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rano_category(baseline_cm3: float, followup_cm3: float) -> str:
    if baseline_cm3 <= 0:
        raise ValueError("RANO pair has a non-positive baseline volume.")
    if followup_cm3 <= 0:
        return "Complete Response (CR)"
    reduction = 1.0 - followup_cm3 / baseline_cm3
    if reduction >= 0.65:
        return "Partial Response (PR)"
    if reduction <= -0.40:
        return "Progressive Disease (PD)"
    return "Stable Disease (SD)"


def audit_cfb_metadata(input_dir: str | Path) -> dict[str, Any]:
    source = Path(input_dir)
    missing = [name for name in TABLES.values() if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing CFB-GBM metadata tables: {', '.join(missing)}")

    tables = {key: _read_tsv(source / name) for key, name in TABLES.items()}
    availability: dict[tuple[str, str], str] = {}
    available_mask_counts: Counter[str] = Counter()
    gtv_rows = 0
    for row in tables["availability"]:
        if row.get("gtv") == "1":
            gtv_rows += 1
            patient = row["id_patient"]
            timepoint = row["temporality"]
            availability[(patient, timepoint)] = row.get("gtv_type", "")
            available_mask_counts[timepoint] += 1

    mri_counts: Counter[str] = Counter()
    for row in tables["mri_availability"]:
        if row.get("t1gd") == "1":
            mri_counts[row["temporality"]] += 1

    pair_results: list[dict[str, Any]] = []
    total_labeled = 0
    total_mismatches = 0
    total_missing_mask_endpoints = 0
    for name, time_a, time_b, vol_a, vol_b, label_field in PAIR_FIELDS:
        labels: Counter[str] = Counter()
        source_pairs: Counter[str] = Counter()
        source_pair_labels: dict[str, Counter[str]] = defaultdict(Counter)
        n = mismatches = missing_masks = 0
        for row in tables["rano"]:
            published = row.get(label_field, "").strip()
            if not published:
                continue
            n += 1
            baseline = float(row[vol_a])
            followup = float(row[vol_b])
            recomputed = _rano_category(baseline, followup)
            labels[published] += 1
            mismatches += recomputed != published
            type_a = availability.get((row["id_patient"], time_a), "missing")
            type_b = availability.get((row["id_patient"], time_b), "missing")
            if type_a == "missing" or type_b == "missing":
                missing_masks += 1
            source_pair = f"{type_a or 'unspecified'} / {type_b or 'unspecified'}"
            source_pairs[source_pair] += 1
            source_pair_labels[source_pair][published] += 1

        total_labeled += n
        total_mismatches += mismatches
        total_missing_mask_endpoints += missing_masks
        pair_results.append(
            {
                "pair": name,
                "timepoint_a": time_a,
                "timepoint_b": time_b,
                "n_labeled_pairs": n,
                "published_categories": {category: labels[category] for category in CATEGORIES},
                "source_pair_counts": dict(sorted(source_pairs.items())),
                "source_pair_category_counts": {
                    source_pair: {category: counts[category] for category in CATEGORIES}
                    for source_pair, counts in sorted(source_pair_labels.items())
                },
                "recomputed_label_mismatches": mismatches,
                "pairs_missing_a_gtv_availability_record": missing_masks,
            }
        )

    hashes = {
        key: _sha256(source / filename)
        for key, filename in TABLES.items()
    }
    return {
        "audit": "cfb_gbm_metadata_reproduction",
        "dataset": "CFB-GBM Version 4",
        "license": "CC BY 4.0",
        "n_clinical_patients": len(tables["clinical"]),
        "n_treatment_rows": len(tables["treatment"]),
        "n_gtv_availability_rows": gtv_rows,
        "gtv_availability_by_timepoint": {
            timepoint: available_mask_counts[timepoint] for timepoint in ("t0", "t1", "t2")
        },
        "t1gd_availability_by_timepoint": {
            timepoint: mri_counts[timepoint] for timepoint in ("t0", "t1", "t2")
        },
        "n_rano_table_rows": len(tables["rano"]),
        "total_labeled_pairs": total_labeled,
        "total_recomputed_label_mismatches": total_mismatches,
        "total_pairs_missing_a_gtv_availability_record": total_missing_mask_endpoints,
        "pairs": pair_results,
        "input_tables": {
            key: {"filename": filename, "sha256": hashes[key]}
            for key, filename in TABLES.items()
        },
        "software": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "tumorlens": "0.1.0",
        },
        "claim_boundary": (
            "RANO categories are derived from the same GTV volumes being assessed. "
            "This audit reproduces published labels; it does not estimate independent "
            "diagnostic accuracy or clinical prediction performance."
        ),
    }


def write_cfb_metadata_audit(summary: dict[str, Any], out_dir: str | Path) -> None:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    fields = ["pair", "n_labeled_pairs", *CATEGORIES, "recomputed_label_mismatches"]
    with (output / "pair_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for pair in summary["pairs"]:
            writer.writerow(
                {
                    "pair": pair["pair"],
                    "n_labeled_pairs": pair["n_labeled_pairs"],
                    **pair["published_categories"],
                    "recomputed_label_mismatches": pair["recomputed_label_mismatches"],
                }
            )

    lines = [
        "# CFB-GBM Version 4 metadata reproduction",
        "",
        f"Total labeled pairs: {summary['total_labeled_pairs']}",
        f"Published-label mismatches: {summary['total_recomputed_label_mismatches']}",
        "",
        "| Pair | n | CR | PR | SD | PD | Mismatches |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for pair in summary["pairs"]:
        cats = pair["published_categories"]
        lines.append(
            f"| {pair['pair']} | {pair['n_labeled_pairs']} | "
            f"{cats['Complete Response (CR)']} | {cats['Partial Response (PR)']} | "
            f"{cats['Stable Disease (SD)']} | {cats['Progressive Disease (PD)']} | "
            f"{pair['recomputed_label_mismatches']} |"
        )
    lines += [
        "",
        ("Categories were recalculated from the official Version 4 GTV volume columns using "
        "the thresholds in the CFB-GBM v2.0 paper. Output is aggregate-only; no patient IDs "
        "or patient-level result rows are written."),
        "",
        summary["claim_boundary"],
        "",
    ]
    (output / "REPRODUCIBILITY.md").write_text("\n".join(lines), encoding="utf-8")
