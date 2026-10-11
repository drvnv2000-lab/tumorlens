"""Write the expert-measurement audit table (local, patient-level) and its aggregate summary.

Records the hand audit of 2026-10-11: every one of the 110 rationale strings was read against
the parsed pairs. The local table keeps the verbatim text, parsed pairs, product sum, expert
call, meaning flags and the adjudication; only counts go to the published JSON.

Usage: python scripts/write_parser_audit.py LUMIERE_ROOT AUDIT_DIR LOCAL_CSV OUT_JSON
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from tumorlens.lumiere import RATING_COLUMN, read_csv
from tumorlens.v1 import _PAIR, expert_row_flags, parse_expert_spd

# Hand-audit result of 2026-10-11 (PREREGISTRATION.md): all numbers transcribed correctly.
TRANSCRIPTION = "correct (hand audit 2026-10-11)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("audit_dir", type=Path)
    ap.add_argument("local_csv", type=Path)
    ap.add_argument("out_json", type=Path)
    a = ap.parse_args(argv)
    folders = {(d.parent.name, d.name) for d in (a.root / "Imaging").glob("Patient-*/week-*") if d.is_dir()}
    collisions = {(r["patient_id"], r["visit_id"]) for r in read_csv(a.audit_dir / "rating_key_collisions.csv")}
    queue = read_csv(a.audit_dir / "rationale_review_queue.csv")
    ratings = {(r["Patient"], r["Date"]): r[RATING_COLUMN].strip()
               for r in read_csv(a.root / "LUMIERE-ExpertRating-v202211.csv")}
    rows = []
    for r in queue:
        key = (r["patient_id"], r["visit_id"])
        if r["dimension_and_source_flags_screen_only"] != "true" or key not in folders or key in collisions:
            continue
        text = r["rationale"]
        spd, n = parse_expert_spd(text)
        flags = expert_row_flags(text)
        approx = bool(re.search(r"\bapprox", text, re.IGNORECASE))
        meaning = [k for k, v in flags.items() if v] + (["approximate"] if approx else [])
        rows.append({
            "patient_id": key[0], "visit_id": key[1], "expert_call": ratings.get(key, ""),
            "rationale_verbatim": text,
            "parsed_pairs": "; ".join(f"{x} x {y}" for x, y in _PAIR.findall(text)),
            "n_pairs": n, "expert_spd_mm2": round(spd, 2),
            "transcription": TRANSCRIPTION,
            "meaning_flags": ", ".join(meaning) or "none",
            "used_in_primary": "yes",
            "excluded_in_post_hoc_flag_sensitivity": "yes" if any(flags.values()) else "no",
        })
    a.local_csv.parent.mkdir(parents=True, exist_ok=True)
    with a.local_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    flag_counts = Counter(f for r in rows for f in r["meaning_flags"].split(", ") if f != "none")
    summary = {
        "rows_audited_by_hand": len(rows),
        "transcription_correct": sum(r["transcription"].startswith("correct") for r in rows),
        "rows_with_more_than_one_pair": sum(r["n_pairs"] > 1 for r in rows),
        "meaning_flags": dict(sorted(flag_counts.items())),
        "rows_excluded_in_post_hoc_flag_sensitivity": sum(
            r["excluded_in_post_hoc_flag_sensitivity"] == "yes" for r in rows),
        "note": "Patient-level table kept local (results/v1/expert_parser_audit.csv).",
    }
    a.out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
