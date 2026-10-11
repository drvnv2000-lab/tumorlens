from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

PAIR_LABELS = {
    "t0_to_t1": "t0 → t1",
    "t0_to_t2": "t0 → t2",
    "t1_to_t2": "t1 → t2",
}
PAIR_COLORS = {
    "t0_to_t1": "#087f8c",
    "t0_to_t2": "#df735c",
    "t1_to_t2": "#7064ad",
}
CATEGORY_KEYS = (
    "Complete Response (CR)",
    "Partial Response (PR)",
    "Stable Disease (SD)",
    "Progressive Disease (PD)",
)
CATEGORY_SHORT = ("CR", "PR", "SD", "PD")
INK = "#172b3a"
MUTED = "#657786"
GRID = "#e4ebf0"


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(value: str) -> float:
    return float(value) if value not in ("", "None", "nan") else float("nan")


def _panel_label(ax, label: str) -> None:
    ax.text(-0.12, 1.08, label, transform=ax.transAxes, fontsize=14, fontweight="bold", color=INK, va="top")


def build_robustness_figure(aggregate_dir: Path, metadata_summary: Path, out_dir: Path) -> list[Path]:
    summary_path = aggregate_dir / "summary.json"
    curve_path = aggregate_dir / "robustness_by_pair_radius.csv"
    transition_path = aggregate_dir / "category_transitions_1mm.csv"
    for path in (summary_path, curve_path, transition_path, metadata_summary):
        if not path.is_file():
            raise FileNotFoundError(f"Required aggregate input is missing: {path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_summary.read_text(encoding="utf-8"))
    curves = _csv(curve_path)
    transitions = _csv(transition_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(14.1, 4.65), facecolor="white")
    grid = fig.add_gridspec(1, 3, width_ratios=(0.95, 1.25, 1.05), left=0.065, right=0.965, top=0.84, bottom=0.19, wspace=0.48)
    ax_flow = fig.add_subplot(grid[0, 0])
    ax_curve = fig.add_subplot(grid[0, 1])
    ax_transition = fig.add_subplot(grid[0, 2])
    for ax in (ax_flow, ax_curve, ax_transition):
        ax.set_facecolor("white")
        ax.tick_params(colors=MUTED, labelsize=9, length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)

    # A. Candidate-to-analyzed cohort flow, with exclusions inferred from aggregate counts.
    _panel_label(ax_flow, "A")
    candidates = summary["candidate_labeled_pairs"]
    processed = summary["processed_pairs_by_interval"]
    pair_keys = [key for key in PAIR_LABELS if key in candidates]
    y = np.arange(len(pair_keys))
    included = np.asarray([int(processed.get(key, 0)) for key in pair_keys])
    excluded = np.asarray([max(0, int(candidates[key]) - int(processed.get(key, 0))) for key in pair_keys])
    ax_flow.barh(y, included, color="#087f8c", height=0.58, label="Analyzed")
    ax_flow.barh(y, excluded, left=included, color="#dce5ea", height=0.58, label="Not analyzed")
    for i, (n_in, n_out) in enumerate(zip(included, excluded, strict=True)):
        if n_in:
            ax_flow.text(max(1, n_in * 0.5), i, str(n_in), ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        if n_out:
            ax_flow.text(n_in + n_out * 0.5, i, str(n_out), ha="center", va="center", color=INK, fontsize=9)
    ax_flow.set_yticks(y, [PAIR_LABELS[key] for key in pair_keys])
    ax_flow.invert_yaxis()
    ax_flow.set_xlim(0, max(int(candidates[key]) for key in pair_keys) * 1.12)
    ax_flow.set_xlabel("Patient pairs", color=MUTED, fontsize=9)
    ax_flow.set_title("Pair flow", loc="left", color=INK, fontsize=11, fontweight="semibold", pad=14)
    ax_flow.grid(axis="x", color=GRID, linewidth=0.7)
    ax_flow.set_axisbelow(True)
    ax_flow.legend(frameon=False, fontsize=8, loc="lower right", bbox_to_anchor=(1.03, -0.36), ncol=1)

    # B. Patient-level any-flip rates and percentile bootstrap intervals.
    _panel_label(ax_curve, "B")
    for key in pair_keys:
        rows = sorted((row for row in curves if row["pair"] == key), key=lambda row: float(row["radius_mm"]))
        if not rows:
            continue
        x = np.asarray([float(row["radius_mm"]) for row in rows])
        rate = np.asarray([_as_float(row["any_flip_rate"]) * 100 for row in rows])
        low = np.asarray([_as_float(row["ci95_low"]) * 100 for row in rows])
        high = np.asarray([_as_float(row["ci95_high"]) * 100 for row in rows])
        color = PAIR_COLORS[key]
        ax_curve.plot(x, rate, marker="o", markersize=4.2, linewidth=2, color=color, label=f"{PAIR_LABELS[key]} (n={int(rows[0]['n_pairs'])})")
        ax_curve.fill_between(x, low, high, color=color, alpha=0.13, linewidth=0)
    ax_curve.axvline(1.0, color="#9aa9b4", linewidth=1, linestyle=(0, (3, 3)), zorder=0)
    ax_curve.set_xlim(0.35, 3.15)
    ax_curve.set_ylim(bottom=0)
    ax_curve.set_xticks([0.5, 1, 1.5, 2, 2.5, 3])
    ax_curve.set_xlabel("Boundary offset radius (mm)", color=MUTED, fontsize=9)
    ax_curve.set_ylabel("Pairs with ≥1 category flip (%)", color=MUTED, fontsize=9)
    ax_curve.set_title("Label sensitivity", loc="left", color=INK, fontsize=11, fontweight="semibold", pad=14)
    ax_curve.grid(axis="y", color=GRID, linewidth=0.7)
    ax_curve.set_axisbelow(True)
    ax_curve.legend(frameon=False, fontsize=8, loc="upper left")

    # C. Primary-interval perturbation-scenario transition matrix at 1 mm.
    _panel_label(ax_transition, "C")
    primary = [row for row in transitions if row["pair"] == "t0_to_t1"]
    counts = np.zeros((4, 4), dtype=int)
    for row in primary:
        i = CATEGORY_KEYS.index(row["published_category"])
        j = CATEGORY_KEYS.index(row["perturbed_category"])
        counts[i, j] = int(row["n_pair_scenarios"])
    row_totals = counts.sum(axis=1, keepdims=True)
    percents = np.divide(counts * 100, row_totals, out=np.zeros_like(counts, dtype=float), where=row_totals > 0)
    cmap = LinearSegmentedColormap.from_list("tumorlens_transition", ["#f4f7f9", "#b6e1d8", "#087f8c"])
    image = ax_transition.imshow(percents, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    ax_transition.set_xticks(range(4), CATEGORY_SHORT)
    ax_transition.set_yticks(range(4), CATEGORY_SHORT)
    ax_transition.set_xlabel("Perturbed category", color=MUTED, fontsize=9)
    ax_transition.set_ylabel("Published category", color=MUTED, fontsize=9)
    ax_transition.set_title("Transitions at 1 mm", loc="left", color=INK, fontsize=11, fontweight="semibold", pad=14)
    for i in range(4):
        for j in range(4):
            color = "white" if percents[i, j] >= 62 else INK
            ax_transition.text(j, i, f"{percents[i, j]:.0f}%\n(n={counts[i,j]})", ha="center", va="center", color=color, fontsize=8)
    colorbar = fig.colorbar(image, ax=ax_transition, fraction=0.046, pad=0.04)
    colorbar.set_label("Within-row scenarios (%)", color=MUTED, fontsize=8)
    colorbar.ax.tick_params(labelsize=8, colors=MUTED, length=0)
    for spine in colorbar.ax.spines.values():
        spine.set_visible(False)

    primary_n = int(summary["candidate_labeled_pairs"]["t0_to_t1"])
    metadata_n = int(metadata.get("total_labeled_pairs", 0))
    fig.text(0.065, 0.055,
        f"Primary interval: t0 → t1; candidate n={primary_n}. Metadata audit reproduced {metadata_n} published labels. "
        "Intervals are patient-level percentile bootstrap CIs; transition cells summarize four perturbation scenarios per pair. "
        "These are dataset-derived volumetric labels, not independent clinical response calls.",
        fontsize=8, color=MUTED, va="bottom", wrap=True)
    outputs = [
        out_dir / "fig01_cfb_gbm_boundary_robustness.pdf",
        out_dir / "fig01_cfb_gbm_boundary_robustness.svg",
        out_dir / "fig01_cfb_gbm_boundary_robustness.png",
    ]
    for path in outputs:
        fig.savefig(path, dpi=400, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Create paper figures from aggregate-only CFB-GBM robustness outputs.")
    parser.add_argument("--aggregate-dir", type=Path, required=True)
    parser.add_argument("--metadata-summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    outputs = build_robustness_figure(args.aggregate_dir, args.metadata_summary, args.out)
    for path in outputs:
        print(path.resolve())


if __name__ == "__main__":
    main()