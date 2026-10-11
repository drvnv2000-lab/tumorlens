"""TumorLens v1 analyses on LUMIERE (descriptive; rules in PREREGISTRATION.md).

Analyses 1 to 3 as planned, exploratory analysis 4 and the post hoc sensitivity on flagged
expert rows (deviation of 2026-10-11, "independent review"). Reads the local patient-level
measurement table and the released rating sheet; writes aggregate results only (JSON, Markdown
and a manifest) to OUT_DIR.

Usage:
  python scripts/run_v1_analysis.py MEASUREMENTS_CSV LUMIERE_ROOT AUDIT_DIR OUT_DIR
      [--n-boot 10000] [--label primary]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from tumorlens import rano
from tumorlens.lumiere import RATING_COLUMN, rationale_flags, read_csv
from tumorlens.v1 import (
    OFFSETS_MM,
    SEED,
    TOOLS,
    auroc,
    bootstrap,
    build_series,
    direction_pairs_consecutive,
    direction_pairs_nadir,
    expert_row_flags,
    parse_expert_spd,
    spd_for_call,
    week_key,
)

CENSORED_SCORE = -3.5  # no flip within 3 mm: ranks as least fragile (deviation 2026-10-11)


def load_measurements(path: Path) -> tuple[dict, Counter]:
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


def median_or_nan(xs: list) -> float:
    return statistics.median(xs) if xs else float("nan")


def share(xs: list) -> float:
    return float(np.mean(xs)) if xs else float("nan")


def analysis1(visits, expert, meas, n_boot) -> dict:
    out = {}
    for tool in TOOLS:
        ratios: dict[str, list[float]] = defaultdict(list)
        diffs: dict[str, list[tuple[float, float]]] = defaultdict(list)
        single, multi = [], []
        no_mask = no_enh = measurable = non_axial = 0
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
            non_axial += int(m["axis"] != 2)
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
            "measured_in_non_axial_plane": non_axial,
            "ratio_auto_over_expert_median": bootstrap(ratios, median_or_nan, n_boot),
            "ratio_iqr": [round(float(q), 3) for q in np.percentile(flat, [25, 75])] if flat else None,
            "ratio_median_single_expert_lesion": {"n": len(single), "median": round(median_or_nan(single), 3)},
            "ratio_median_multiple_expert_lesions": {"n": len(multi), "median": round(median_or_nan(multi), 3)},
            "bland_altman_mm2": {
                "bias": bootstrap(diffs, bias, n_boot),
                "lower_limit": bootstrap(diffs, loa(-1), n_boot),
                "upper_limit": bootstrap(diffs, loa(+1), n_boot),
            },
        }
    return out


def analysis2(series_by_patient, expert, meas, n_boot) -> dict:
    out = {}
    for tool in TOOLS:
        nadir: dict[str, list[bool]] = defaultdict(list)
        cons_vol: dict[str, list[bool]] = defaultdict(list)
        cons_spd: dict[str, list[bool]] = defaultdict(list)
        ties = Counter()
        for p, series in series_by_patient.items():
            for s in series:  # pairs never cross series
                pts = [(expert[(p, v)][0], meas.get((tool, p, v), {}).get(0.0))
                       for v, _ in s if (p, v) in expert]
                pts = [(e, m) for e, m in pts if m is not None]
                if len(pts) < 2:
                    continue
                e = [x[0] for x in pts]
                a_spd = [x[1]["d1"] * x[1]["d2"] for x in pts]
                a_vol = [x[1]["volume"] for x in pts]
                nadir[p] += direction_pairs_nadir(e, a_spd)
                cons_vol[p] += direction_pairs_consecutive(e, a_vol)
                cons_spd[p] += direction_pairs_consecutive(e, a_spd)
                for i in range(1, len(pts)):
                    ties["expert_change_zero"] += int(e[i] == e[i - 1])
                    ties["auto_volume_change_zero"] += int(a_vol[i] == a_vol[i - 1])
                    ties["auto_spd_change_zero"] += int(a_spd[i] == a_spd[i - 1])

        def block(d):
            return {"pairs": sum(len(v) for v in d.values()), "patients": len(d),
                    "agreement": bootstrap(d, share, n_boot)}

        out[tool] = {
            "planned_change_from_nadir_spd": block(nadir),
            "suter_matched_consecutive_volume": block(cons_vol),
            "suter_matched_consecutive_spd": block(cons_spd),
            "consecutive_pairs_with_zero_change": dict(ties),
        }
    return out


def tool_series(series_by_patient, meas, tool):
    """Yield (patient, visits, spd_by_offset, enh_by_offset) for each analysable series."""
    for p, series in series_by_patient.items():
        for s in series:
            visits = [(v, r) for v, r in s if (tool, p, v) in meas]
            if not visits or visits[0][0] != s[0][0] or len(visits) < 2:
                yield p, None, len(s) - len(visits), None
                continue
            spd = {o: [spd_for_call(meas[(tool, p, v)][o]["d1"], meas[(tool, p, v)][o]["d2"])
                       for v, _ in visits] for o in OFFSETS_MM}
            enh = {o: [meas[(tool, p, v)][o]["voxels"] > 0 for v, _ in visits] for o in OFFSETS_MM}
            yield p, visits, len(s) - len(visits), (spd, enh)


def automated_calls(series_by_patient, meas) -> dict:
    """{tool: {(patient, visit): (expert, auto_call, flip_mm, non_axial)}} for follow-ups."""
    out = {}
    for tool in TOOLS:
        rows = {}
        for p, visits, _, se in tool_series(series_by_patient, meas, tool):
            if visits is None:
                continue
            spd, enh = se
            calls = rano.call_series(spd[0.0], enh[0.0])
            for i in range(1, len(visits)):
                v, expert_call = visits[i]
                rows[(p, v)] = (expert_call, calls[i], rano.flip_margin(spd, i, enh),
                                meas[(tool, p, v)][0.0]["axis"] != 2)
        out[tool] = rows
    return out


def analysis3(series_by_patient, meas, calls, n_boot) -> dict:
    out = {}
    for tool in TOOLS:
        n_series = n_no_base = skipped = 0
        for _, visits, missing, _ in tool_series(series_by_patient, meas, tool):
            skipped += missing
            if visits is None:
                n_no_base += 1
            else:
                n_series += 1
        rows = calls[tool]
        flips: dict[str, list] = defaultdict(list)
        for (p, _), (_, _, f, _) in sorted(rows.items()):
            flips[p].append(f)

        def within(mm):
            return lambda xs: float(np.mean([x is not None and x <= mm for x in xs])) if xs else float("nan")

        out[tool] = {
            "series_analysed": n_series,
            "series_without_readable_baseline_or_followup": n_no_base,
            "rated_visits_skipped_no_readable_mask": skipped,
            "automated_calls": len(rows),
            "patients": len(flips),
            "followups_measured_in_non_axial_plane": sum(r[3] for r in rows.values()),
            "automated_call_counts": dict(sorted(Counter(r[1] for r in rows.values()).items())),
            "share_flipping_within_mm": {f"{mm:g}": bootstrap(flips, within(mm), n_boot)
                                         for mm in (0.5, 1.0, 2.0, 3.0)},
            "calls_not_flipping_within_3mm_censored": sum(r[2] is None for r in rows.values()),
            "descriptive_expert_vs_automated_call": {
                f"{e}|{a}": n for (e, a), n in sorted(Counter((r[0], r[1]) for r in rows.values()).items())},
        }
    return out


def analysis4(calls, rationale, n_boot) -> dict:
    """Exploratory: do fragility or tool disagreement discriminate disagreement with the expert?"""
    pd_ = {t: {k: (r[0] == "PD", r[1] == "PD") for k, r in rows.items()} for t, rows in calls.items()}
    both = set(pd_["hd_glio_auto"]) & set(pd_["deepbratumia"])
    tool_disagree = {k: pd_["hd_glio_auto"][k][1] != pd_["deepbratumia"][k][1] for k in both}

    def documented_other_grounds(k):
        f = rationale_flags(rationale.get(k, ""))
        return f["mentions_t2_progression"] or f["mentions_new_lesion"]

    def run(tool, keep):
        rows = {k: r for k, r in calls[tool].items() if keep(k)}
        pa, pb, pc = defaultdict(list), defaultdict(list), defaultdict(list)
        for (p, v), (e, a, f, _) in sorted(rows.items()):
            y = (e == "PD") != (a == "PD")
            pa[p].append((-f if f is not None else CENSORED_SCORE, y))
            pc[p].append((float(f is not None and f <= 1.0), y))
            if (p, v) in tool_disagree:
                pb[p].append((float(tool_disagree[(p, v)]), y))
        ys = [y for xs in pa.values() for _, y in xs]
        expert_pd = sum(r[0] == "PD" for r in rows.values())
        return {
            "calls": len(ys), "patients": len(pa), "disagreements": int(sum(ys)),
            "expert_pd": expert_pd, "expert_non_pd": len(ys) - expert_pd,
            "disagreement_rate_when_expert_pd": round(
                share([(r[0] == "PD") != (r[1] == "PD") for r in rows.values() if r[0] == "PD"]), 3),
            "disagreement_rate_when_expert_non_pd": round(
                share([(r[0] == "PD") != (r[1] == "PD") for r in rows.values() if r[0] != "PD"]), 3),
            "auroc_fragility_score": bootstrap(pa, auroc, n_boot),
            "auroc_flip_within_1mm": bootstrap(pc, auroc, n_boot),
            "auroc_tool_disagreement": bootstrap(pb, auroc, n_boot),
            "calls_with_both_tools": sum(len(x) for x in pb.values()),
        }

    return {
        "status": "exploratory (deviation 2026-10-11, independent review); not the planned confirmatory test",
        "outcome": "automated PD/non-PD call (offset 0) differs from the expert PD/non-PD call",
        "censored_flip_score": CENSORED_SCORE,
        "all_calls": {t: run(t, lambda k: True) for t in TOOLS},
        "sensitivity_without_documented_t2_or_new_lesion": {
            t: run(t, lambda k: not documented_other_grounds(k)) for t in TOOLS},
    }


NAMES = {"deepbratumia": "DeepBraTumIA", "hd_glio_auto": "HD-GLIO-AUTO"}


def fmt(c: dict, pct: bool = False) -> str:
    if c["estimate"] is None:
        return "n/a"
    if pct:
        return f"{100 * c['estimate']:.1f}% ({100 * c['ci95'][0]:.1f} to {100 * c['ci95'][1]:.1f})"
    return f"{c['estimate']:.2f} ({c['ci95'][0]:.2f} to {c['ci95'][1]:.2f})"


def render_tables(r: dict) -> str:
    """Markdown tables generated from the results JSON (no hand-copied numbers)."""
    a1, a2, a3, a4 = (r["analysis1_measurement_agreement"], r["analysis2_direction_agreement"],
                      r["analysis3_fragility"], r["analysis4_exploratory"])
    es = r["expert_measured_set"]
    lines = ["<!-- generated by scripts/run_v1_analysis.py; do not edit by hand -->", "",
             f"Run: {r['label']}. Expert-measured set: {es['visits']} visits, {es['patients']} patients, ratings "
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
              ("| Tool | Pairs (patients) | Planned: change from nadir, SPD | Suter-matched: consecutive, volume "
              "| Consecutive, SPD | Zero-change pairs (expert / volume / SPD) |"),
              "|---|---|---|---|---|---|"]
    for t, x in a2.items():
        n, z = x["planned_change_from_nadir_spd"], x["consecutive_pairs_with_zero_change"]
        lines.append(f"| {NAMES[t]} | {n['pairs']} ({n['patients']}) | {fmt(n['agreement'], True)} | "
                     f"{fmt(x['suter_matched_consecutive_volume']['agreement'], True)} | "
                     f"{fmt(x['suter_matched_consecutive_spd']['agreement'], True)} | "
                     f"{z.get('expert_change_zero', 0)} / {z.get('auto_volume_change_zero', 0)} / "
                     f"{z.get('auto_spd_change_zero', 0)} |")
    lines += ["", "### Analysis 3: sensitivity of automated calls to uniform boundary offsets", "",
              ("| Tool | Calls (patients, series) | Change within 0.5 mm | 1 mm | 2 mm | 3 mm "
              "| No change within 3 mm (censored) | Calls CR / PR / SD / PD |"),
              "|---|---|---|---|---|---|---|---|"]
    for t, x in a3.items():
        s, c = x["share_flipping_within_mm"], x["automated_call_counts"]
        lines.append(f"| {NAMES[t]} | {x['automated_calls']} ({x['patients']}, {x['series_analysed']}) | "
                     + " | ".join(fmt(s[k], True) for k in ("0.5", "1", "2", "3"))
                     + f" | {x['calls_not_flipping_within_3mm_censored']} | "
                     f"{c.get('CR', 0)} / {c.get('PR', 0)} / {c.get('SD', 0)} / {c.get('PD', 0)} |")
    lines += ["", "### Analysis 4 (exploratory): discrimination of disagreement with the expert call", "",
              ("| Set | Tool | Calls (patients) | Disagreements | Expert PD / non-PD | AUROC fragility score "
              "| AUROC flip within 1 mm | AUROC tool disagreement | Undefined resamples (score) |"),
              "|---|---|---|---|---|---|---|---|---|"]
    for setname, label in (("all_calls", "All calls"),
                           ("sensitivity_without_documented_t2_or_new_lesion", "No documented T2/new lesion")):
        for t, x in a4[setname].items():
            lines.append(f"| {label} | {NAMES[t]} | {x['calls']} ({x['patients']}) | {x['disagreements']} | "
                         f"{x['expert_pd']} / {x['expert_non_pd']} | {fmt(x['auroc_fragility_score'])} | "
                         f"{fmt(x['auroc_flip_within_1mm'])} | {fmt(x['auroc_tool_disagreement'])} | "
                         f"{x['auroc_fragility_score']['undefined_resamples']} |")
    lines += ["", "### Descriptive: expert call versus automated call (not a preregistered analysis)", "",
              "| Expert \\ automated | " + " | ".join(f"{NAMES[t]} CR / PR / SD / PD" for t in a3) + " |",
              "|---|" + "---|" * len(a3)]
    for e in ("CR", "PR", "SD", "PD"):
        cells = []
        for t in a3:
            ct = a3[t]["descriptive_expert_vs_automated_call"]
            cells.append(" / ".join(str(ct.get(f"{e}|{k}", 0)) for k in ("CR", "PR", "SD", "PD")))
        lines.append(f"| {e} | " + " | ".join(cells) + " |")
    s = r["sensitivity_flagged_expert_rows_excluded"]
    lines += ["", "### Post hoc: analyses 1 and 2 without the 6 flagged expert rows", "",
              "| Tool | Visits | Median ratio (95% CI) | Pairs | Consecutive volume agreement |", "|---|---|---|---|---|"]
    for t in TOOLS:
        x1, x2 = s["analysis1"][t], s["analysis2"][t]["suter_matched_consecutive_volume"]
        lines.append(f"| {NAMES[t]} | {x1['analysed_visits']} | {fmt(x1['ratio_auto_over_expert_median'])} | "
                     f"{x2['pairs']} | {fmt(x2['agreement'], True)} |")
    return "\n".join(lines) + "\n"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "scripts"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("+uncommitted-changes" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("measurements", type=Path)
    ap.add_argument("lumiere_root", type=Path)
    ap.add_argument("audit_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--n-boot", type=int, default=10_000)
    ap.add_argument("--label", default="primary", help="primary, or e.g. pixel_centre")
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
    flagged = {k for k in measured_set if any(expert_row_flags(rationale[k]).values())}
    if len(flagged) != 6:
        raise SystemExit(f"Expected the 6 hand-audited flagged expert rows, found {len(flagged)}.")
    ratings_path = a.lumiere_root / "LUMIERE-ExpertRating-v202211.csv"
    ratings_rows = read_csv(ratings_path)
    by_patient: dict[str, list] = defaultdict(list)
    for r in ratings_rows:
        key = (r["Patient"], r["Date"])
        if key in collisions or key not in folders:
            continue
        by_patient[r["Patient"]].append((week_key(r["Date"]), r["Date"], (r[RATING_COLUMN] or "").strip()))
    series_by_patient = {p: build_series(sorted(rows)) for p, rows in by_patient.items()}
    calls = automated_calls(series_by_patient, meas)

    ratings_in_set = Counter(next(r[RATING_COLUMN].strip() for r in ratings_rows
                                  if (r["Patient"], r["Date"]) == k) for k in measured_set)
    kept = [k for k in measured_set if k not in flagged]
    results = {
        "label": a.label,
        "plan": "PREREGISTRATION.md (2026-10-10 plan and dated deviations of 2026-10-11)",
        "bootstrap": {"resamples": a.n_boot, "unit": "patient", "interval": "percentile 95%", "seed": SEED},
        "measurement_status_counts": {f"{t}|{s}": n for (t, s), n in sorted(status.items())},
        "expert_measured_set": {
            "visits": len(measured_set),
            "patients": len({p for p, _ in measured_set}),
            "expert_ratings": dict(sorted(ratings_in_set.items())),
            "visits_with_more_than_one_expert_lesion": sum(n > 1 for _, n in expert.values()),
            "rows_flagged_in_hand_audit": len(flagged),
        },
        "analysis1_measurement_agreement": analysis1(measured_set, expert, meas, a.n_boot),
        "analysis2_direction_agreement": analysis2(series_by_patient, expert, meas, a.n_boot),
        "analysis3_fragility": analysis3(series_by_patient, meas, calls, a.n_boot),
        "analysis4_exploratory": analysis4(calls, rationale_all(ratings_rows), a.n_boot),
        "sensitivity_flagged_expert_rows_excluded": {
            "status": "post hoc",
            "analysis1": analysis1(kept, expert, meas, a.n_boot),
            "analysis2": analysis2(series_by_patient, {k: expert[k] for k in kept}, meas, a.n_boot),
        },
    }
    a.out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if a.label == "primary" else f"_{a.label}"
    (a.out_dir / f"v1_results{suffix}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (a.out_dir / f"v1_tables{suffix}.md").write_text(render_tables(results), encoding="utf-8")
    manifest = {
        "label": a.label,
        "code_commit": git_commit(),
        "command": f"scripts/run_v1_analysis.py <measurements> <lumiere_root> <audit_dir> <out_dir> "
                   f"--n-boot {a.n_boot} --label {a.label}",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "seed": SEED,
        "bootstrap_resamples": a.n_boot,
        "inputs_sha256": {
            "LUMIERE-ExpertRating-v202211.csv": sha256(ratings_path),
            "measurements (local, patient-level)": sha256(a.measurements),
            "rationale_review_queue.csv (local audit)": sha256(a.audit_dir / "rationale_review_queue.csv"),
            "rating_key_collisions.csv (local audit)": sha256(a.audit_dir / "rating_key_collisions.csv"),
        },
        "outputs": [f"v1_results{suffix}.json", f"v1_tables{suffix}.md"],
    }
    (a.out_dir / f"manifest{suffix}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(render_tables(results))
    return 0


def rationale_all(ratings_rows: list[dict]) -> dict:
    from tumorlens.lumiere import RATIONALE_COLUMN

    return {(r["Patient"], r["Date"]): r[RATIONALE_COLUMN] or "" for r in ratings_rows}


if __name__ == "__main__":
    sys.exit(main())
