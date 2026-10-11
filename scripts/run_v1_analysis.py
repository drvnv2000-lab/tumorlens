"""TumorLens v1 analyses 1 to 3 on LUMIERE (descriptive; rules in PREREGISTRATION.md).

Reads the local patient-level measurement table and the released rating sheet; writes
aggregate results only (JSON and Markdown) to OUT_DIR.

Usage:
  python scripts/run_v1_analysis.py MEASUREMENTS_CSV LUMIERE_ROOT AUDIT_DIR OUT_DIR [--n-boot 10000]
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from tumorlens import rano
from tumorlens.lumiere import RATING_COLUMN, read_csv
from tumorlens.v1 import (
    OFFSETS_MM,
    TOOLS,
    bootstrap_ci,
    build_series,
    direction_pairs_consecutive,
    direction_pairs_nadir,
    parse_expert_spd,
    spd_for_call,
    week_key,
)


def load_measurements(path: Path) -> dict:
    """{(tool, patient, visit): {offset: row}} for readable masks; plus status counts."""
    meas: dict = defaultdict(dict)
    status: Counter = Counter()
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = (r["tool"], r["patient_id"], r["visit_id"])
            if r["status"] != "ok":
                status[(r["tool"], r["status"])] += 1
                continue
            o = float(r["offset_mm"])
            if o == 0.0:
                status[(r["tool"], "ok")] += 1
            meas[key][o] = {
                "d1": float(r["d1"]), "d2": float(r["d2"]),
                "voxels": int(r["enhancing_voxels"]), "volume": float(r["volume_mm3"]),
                "axis": int(r["axis"]),
            }
    return meas, status


def r3(x: float) -> float:
    return round(float(x), 3)


def ci(point_lo_hi: tuple[float, float, float]) -> dict:
    p, lo, hi = point_lo_hi
    return {"estimate": r3(p), "ci95": [r3(lo), r3(hi)]}


def median_or_nan(xs: list) -> float:
    return statistics.median(xs) if xs else float("nan")


def analysis1(visits, expert, meas, n_boot) -> dict:
    out = {}
    for tool in TOOLS:
        ratios: dict[str, list[float]] = defaultdict(list)
        diffs: dict[str, list[tuple[float, float]]] = defaultdict(list)
        single, multi = [], []
        no_mask = no_enh = measurable = 0
        for p, v in visits:
            m = meas.get((tool, p, v), {}).get(0.0)
            if m is None:
                no_mask += 1
                continue
            if m["voxels"] == 0:
                no_enh += 1
                continue
            auto = m["d1"] * m["d2"]
            measurable += int(min(m["d1"], m["d2"]) >= rano.MIN_MEASURABLE_MM)
            e_spd, n_pairs = expert[(p, v)]
            ratios[p].append(auto / e_spd)
            diffs[p].append((auto, e_spd))
            (single if n_pairs == 1 else multi).append(auto / e_spd)
        flat = [x for xs in ratios.values() for x in xs]

        def bias(sample):
            return float(np.mean([a - e for a, e in sample]))

        def loa(sign):
            def f(sample):
                d = np.array([a - e for a, e in sample])
                return float(d.mean() + sign * 1.96 * d.std(ddof=1)) if len(d) > 1 else float("nan")
            return f

        out[tool] = {
            "visits_in_set": len(visits),
            "no_readable_mask": no_mask,
            "no_enhancing_voxel": no_enh,
            "analysed_visits": len(flat),
            "analysed_patients": len(ratios),
            "automated_lesion_measurable": measurable,
            "ratio_auto_over_expert_median": ci(bootstrap_ci(ratios, median_or_nan, n_boot)),
            "ratio_iqr": [r3(q) for q in np.percentile(flat, [25, 75])] if flat else None,
            "ratio_median_single_expert_lesion": {"n": len(single), "median": r3(median_or_nan(single))},
            "ratio_median_multiple_expert_lesions": {"n": len(multi), "median": r3(median_or_nan(multi))},
            "bland_altman_mm2": {
                "bias": ci(bootstrap_ci(diffs, bias, n_boot)),
                "lower_limit": ci(bootstrap_ci(diffs, loa(-1), n_boot)),
                "upper_limit": ci(bootstrap_ci(diffs, loa(+1), n_boot)),
            },
        }
    return out


def analysis2(series_by_patient, expert, meas, n_boot) -> dict:
    out = {}
    for tool in TOOLS:
        nadir: dict[str, list[bool]] = defaultdict(list)
        cons_vol: dict[str, list[bool]] = defaultdict(list)
        cons_spd: dict[str, list[bool]] = defaultdict(list)
        for p, series in series_by_patient.items():
            for s in series:
                pts = [(v, expert[(p, v)][0], meas.get((tool, p, v), {}).get(0.0))
                       for v, _ in s if (p, v) in expert]
                pts = [(v, e, m) for v, e, m in pts if m is not None]
                if len(pts) < 2:
                    continue
                e = [x[1] for x in pts]
                a_spd = [x[2]["d1"] * x[2]["d2"] for x in pts]
                a_vol = [x[2]["volume"] for x in pts]
                nadir[p] += direction_pairs_nadir(e, a_spd)
                cons_vol[p] += direction_pairs_consecutive(e, a_vol)
                cons_spd[p] += direction_pairs_consecutive(e, a_spd)

        def share(xs):
            return float(np.mean(xs)) if xs else float("nan")

        def block(d):
            n = sum(len(v) for v in d.values())
            return {"pairs": n, "patients": len(d), "agreement": ci(bootstrap_ci(d, share, n_boot))}

        out[tool] = {
            "planned_change_from_nadir_spd": block(nadir),
            "suter_matched_consecutive_volume": block(cons_vol),
            "suter_matched_consecutive_spd": block(cons_spd),
        }
    return out


def analysis3(series_by_patient, meas, n_boot) -> dict:
    out = {}
    for tool in TOOLS:
        flips: dict[str, list[float | None]] = defaultdict(list)
        crosstab: Counter = Counter()
        auto_calls: Counter = Counter()
        n_series = n_skipped_visits = n_series_no_baseline = 0
        non_axial = total_visits = 0
        for p, series in series_by_patient.items():
            for s in series:
                visits = [(v, r) for v, r in s if (tool, p, v) in meas]
                n_skipped_visits += len(s) - len(visits)
                if not visits or visits[0][0] != s[0][0] or len(visits) < 2:
                    n_series_no_baseline += 1
                    continue
                n_series += 1
                spd = {o: [spd_for_call(meas[(tool, p, v)][o]["d1"], meas[(tool, p, v)][o]["d2"])
                           for v, _ in visits] for o in OFFSETS_MM}
                enh = {o: [meas[(tool, p, v)][o]["voxels"] > 0 for v, _ in visits] for o in OFFSETS_MM}
                calls = rano.call_series(spd[0.0], enh[0.0])
                for i in range(1, len(visits)):
                    total_visits += 1
                    non_axial += int(meas[(tool, p, visits[i][0])][0.0]["axis"] != 2)
                    flips[p].append(rano.flip_margin(spd, i, enh))
                    crosstab[(visits[i][1], calls[i])] += 1
                    auto_calls[calls[i]] += 1

        def within(mm):
            def f(xs):
                return float(np.mean([x is not None and x <= mm for x in xs])) if xs else float("nan")
            return f

        out[tool] = {
            "series_analysed": n_series,
            "series_without_readable_baseline_or_followup": n_series_no_baseline,
            "rated_visits_skipped_no_readable_mask": n_skipped_visits,
            "automated_calls": sum(auto_calls.values()),
            "patients": len(flips),
            "followups_measured_in_non_axial_plane": non_axial,
            "automated_call_counts": dict(sorted(auto_calls.items())),
            "share_flipping_within_mm": {f"{mm:g}": ci(bootstrap_ci(flips, within(mm), n_boot))
                                         for mm in (0.5, 1.0, 2.0, 3.0)},
            "descriptive_expert_vs_automated_call": {f"{e}|{a}": n for (e, a), n in sorted(crosstab.items())},
        }
    return out


NAMES = {"deepbratumia": "DeepBraTumIA", "hd_glio_auto": "HD-GLIO-AUTO"}


def fmt(c: dict, pct: bool = False) -> str:
    if pct:
        return f"{100 * c['estimate']:.1f}% ({100 * c['ci95'][0]:.1f} to {100 * c['ci95'][1]:.1f})"
    return f"{c['estimate']:.2f} ({c['ci95'][0]:.2f} to {c['ci95'][1]:.2f})"


def render_tables(r: dict) -> str:
    """Markdown tables generated from the results JSON (no hand-copied numbers)."""
    a1, a2, a3 = (r["analysis1_measurement_agreement"], r["analysis2_direction_agreement"],
                  r["analysis3_fragility"])
    es = r["expert_measured_set"]
    lines = ["<!-- generated by scripts/run_v1_analysis.py; do not edit by hand -->", "",
             f"Expert-measured set: {es['visits']} visits, {es['patients']} patients, ratings "
             + ", ".join(f"{k} {v}" for k, v in es["expert_ratings"].items())
             + f"; {es['visits_with_more_than_one_expert_lesion']} visits with more than one expert lesion.",
             "", "### Analysis 1: measurement agreement (automated SPD / expert SPD)", "",
             ("| Tool | Visits (patients) | Median ratio (95% CI) | IQR | Single-lesion median (n) "
             "| Multi-lesion median (n) | Bland-Altman bias, mm² (95% CI) | Limits of agreement, mm² |"),
             "|---|---|---|---|---|---|---|---|"]
    for t, x in a1.items():
        ba = x["bland_altman_mm2"]
        lines.append(
            f"| {NAMES[t]} | {x['analysed_visits']} ({x['analysed_patients']}) | "
            f"{fmt(x['ratio_auto_over_expert_median'])} | {x['ratio_iqr'][0]:.2f} to {x['ratio_iqr'][1]:.2f} | "
            f"{x['ratio_median_single_expert_lesion']['median']:.2f} ({x['ratio_median_single_expert_lesion']['n']}) | "
            f"{x['ratio_median_multiple_expert_lesions']['median']:.2f} ({x['ratio_median_multiple_expert_lesions']['n']}) | "
            f"{ba['bias']['estimate']:.0f} ({ba['bias']['ci95'][0]:.0f} to {ba['bias']['ci95'][1]:.0f}) | "
            f"{ba['lower_limit']['estimate']:.0f} to {ba['upper_limit']['estimate']:.0f} |")
    lines += ["", "### Analysis 2: direction agreement with the expert", "",
              "| Tool | Pairs (patients) | Planned: change from nadir, SPD | Suter-matched: consecutive, volume | Consecutive, SPD |",
              "|---|---|---|---|---|"]
    for t, x in a2.items():
        n = x["planned_change_from_nadir_spd"]
        lines.append(f"| {NAMES[t]} | {n['pairs']} ({n['patients']}) | {fmt(n['agreement'], True)} | "
                     f"{fmt(x['suter_matched_consecutive_volume']['agreement'], True)} | "
                     f"{fmt(x['suter_matched_consecutive_spd']['agreement'], True)} |")
    lines += ["", "### Analysis 3: boundary fragility of automated calls", "",
              "| Tool | Calls (patients, series) | Flip within 0.5 mm | 1 mm | 2 mm | 3 mm | Calls CR / PR / SD / PD |",
              "|---|---|---|---|---|---|---|"]
    for t, x in a3.items():
        s, c = x["share_flipping_within_mm"], x["automated_call_counts"]
        lines.append(f"| {NAMES[t]} | {x['automated_calls']} ({x['patients']}, {x['series_analysed']}) | "
                     + " | ".join(fmt(s[k], True) for k in ("0.5", "1", "2", "3"))
                     + f" | {c.get('CR', 0)} / {c.get('PR', 0)} / {c.get('SD', 0)} / {c.get('PD', 0)} |")
    lines += ["", "### Descriptive: expert call versus automated call (not a preregistered analysis)", "",
              "| Expert \\ automated | " + " | ".join(f"{NAMES[t]} CR / PR / SD / PD" for t in a3) + " |",
              "|---|" + "---|" * len(a3)]
    for e in ("CR", "PR", "SD", "PD"):
        cells = []
        for t in a3:
            ct = a3[t]["descriptive_expert_vs_automated_call"]
            cells.append(" / ".join(str(ct.get(f"{e}|{k}", 0)) for k in ("CR", "PR", "SD", "PD")))
        lines.append(f"| {e} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("measurements", type=Path)
    ap.add_argument("lumiere_root", type=Path)
    ap.add_argument("audit_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--n-boot", type=int, default=10_000)
    a = ap.parse_args(argv)

    meas, status = load_measurements(a.measurements)
    imaging = a.lumiere_root / "Imaging"
    folders = {(d.parent.name, d.name) for d in imaging.glob("Patient-*/week-*") if d.is_dir()}

    collisions = {(r["patient_id"], r["visit_id"]) for r in read_csv(a.audit_dir / "rating_key_collisions.csv")}
    queue = read_csv(a.audit_dir / "rationale_review_queue.csv")
    measured_set = sorted({(r["patient_id"], r["visit_id"]) for r in queue
                           if r["dimension_and_source_flags_screen_only"] == "true"}
                          & folders - collisions)
    rationale = {(r["patient_id"], r["visit_id"]): r["rationale"] for r in queue}
    expert = {k: parse_expert_spd(rationale[k]) for k in measured_set}
    if any(spd <= 0 for spd, _ in expert.values()):
        raise SystemExit("A measured-set rationale has no parseable dimension pair.")
    ratings_rows = read_csv(a.lumiere_root / "LUMIERE-ExpertRating-v202211.csv")
    by_patient: dict[str, list] = defaultdict(list)
    for r in ratings_rows:
        key = (r["Patient"], r["Date"])
        if key in collisions or key not in folders:
            continue
        by_patient[r["Patient"]].append((week_key(r["Date"]), r["Date"], (r[RATING_COLUMN] or "").strip()))
    series_by_patient = {p: build_series(sorted(rows)) for p, rows in by_patient.items()}

    ratings_in_set = Counter(next(r[RATING_COLUMN].strip() for r in ratings_rows
                                  if (r["Patient"], r["Date"]) == k) for k in measured_set)
    results = {
        "plan": "PREREGISTRATION.md, deviation 2026-10-11 'analysis details fixed before any automated measurement is computed'",
        "bootstrap": {"resamples": a.n_boot, "unit": "patient", "interval": "percentile 95%"},
        "measurement_status_counts": {f"{t}|{s}": n for (t, s), n in sorted(status.items())},
        "expert_measured_set": {
            "visits": len(measured_set),
            "patients": len({p for p, _ in measured_set}),
            "expert_ratings": dict(sorted(ratings_in_set.items())),
            "visits_with_more_than_one_expert_lesion": sum(n > 1 for _, n in expert.values()),
        },
        "analysis1_measurement_agreement": analysis1(measured_set, expert, meas, a.n_boot),
        "analysis2_direction_agreement": analysis2(series_by_patient, expert, meas, a.n_boot),
        "analysis3_fragility": analysis3(series_by_patient, meas, a.n_boot),
    }
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "v1_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (a.out_dir / "v1_tables.md").write_text(render_tables(results), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
