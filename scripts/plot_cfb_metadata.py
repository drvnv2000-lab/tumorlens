from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

PALETTE = {
    "Complete Response (CR)": "#8D6BC4",
    "Partial Response (PR)": "#2AA198",
    "Stable Disease (SD)": "#5D8CC1",
    "Progressive Disease (PD)": "#E37A68",
    "available": "#1D8F83",
    "missing": "#E8EDF2",
    "ink": "#172738",
    "muted": "#627386",
    "grid": "#E4EAF0",
}


def plot_metadata_summary(summary_path: Path, output_dir: Path) -> None:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    cohort_n = summary["n_clinical_patients"]
    timepoints = ("t0", "t1", "t2")
    available = [summary["gtv_availability_by_timepoint"][timepoint] for timepoint in timepoints]
    pairs = summary["pairs"]
    categories = (
        "Complete Response (CR)",
        "Partial Response (PR)",
        "Stable Disease (SD)",
        "Progressive Disease (PD)",
    )
    pair_labels = {"t0_to_t1": "t0 to t1", "t0_to_t2": "t0 to t2", "t1_to_t2": "t1 to t2"}

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "axes.labelcolor": PALETTE["muted"],
        "text.color": PALETTE["ink"],
        "axes.edgecolor": "#CAD4DE",
        "axes.linewidth": 0.8,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    })
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.9), gridspec_kw={"width_ratios": [0.92, 1.35, 1.1]})
    fig.subplots_adjust(left=0.07, right=0.99, top=0.78, bottom=0.24, wspace=0.42)
    fig.suptitle("CFB–GBM cohort readiness", x=0.07, y=0.96, ha="left", fontsize=21, fontweight="bold")
    fig.text(
        0.07, 0.88,
        "Version 4 · 264 patients · longitudinal GTV masks and dataset-derived volumetric response labels",
        ha="left", fontsize=11, color=PALETTE["muted"],
    )

    ax = axes[0]
    y = np.arange(len(timepoints))
    missing = [cohort_n - count for count in available]
    ax.barh(y, available, color=PALETTE["available"], height=0.56, label="GTV available")
    ax.barh(y, missing, left=available, color=PALETTE["missing"], height=0.56, label="Not available")
    ax.set_yticks(y, [f"At {timepoint}" for timepoint in timepoints])
    ax.invert_yaxis()
    ax.set_xlim(0, cohort_n)
    ax.set_xlabel("Patients")
    ax.set_title("A  Longitudinal masks", loc="left", pad=12)
    ax.grid(axis="x", color=PALETTE["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.tick_params(axis="x", colors=PALETTE["muted"])
    for yi, count in zip(y, available):
        ax.text(count + 4, yi, f"{count} / {cohort_n}", va="center", color=PALETTE["ink"], fontsize=9)
    ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1.03, -0.26), ncol=1, fontsize=8)

    ax = axes[1]
    y = np.arange(len(pairs))
    [pair["n_labeled_pairs"] for pair in pairs]
    for yi, pair in enumerate(pairs):
        left = 0.0
        total = pair["n_labeled_pairs"]
        for category in categories:
            count = pair["published_categories"][category]
            fraction = count / total if total else 0
            ax.barh(yi, fraction, left=left, color=PALETTE[category], height=0.56, edgecolor="white", linewidth=0.5)
            if count >= 8:
                ax.text(left + fraction / 2, yi, str(count), ha="center", va="center", color="white", fontsize=9, fontweight="bold")
            left += fraction
        ax.text(1.03, yi, f"n={total}", va="center", color=PALETTE["muted"], fontsize=9)
    ax.set_yticks(y, [pair_labels[pair["pair"]] for pair in pairs])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.5, 1], ["0%", "50%", "100%"])
    ax.set_xlabel("Published label composition")
    ax.set_title("B  Dataset-derived response labels", loc="left", pad=12)
    ax.grid(axis="x", color=PALETTE["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.tick_params(axis="x", colors=PALETTE["muted"])
    legend_handles = [
        Patch(facecolor=PALETTE[category], label=category)
        for category in categories
    ]
    ax.legend(handles=legend_handles, frameon=False, loc="lower center", bbox_to_anchor=(0.52, -0.30), ncol=2, fontsize=8)

    ax = axes[2]
    labels = [pair_labels[pair["pair"]] for pair in pairs]
    source_a = []
    source_b = []
    for pair in pairs:
        counts = pair["source_pair_counts"]
        manual_to_generated = counts.get("humanSegmentation / genSegmentation", 0)
        generated_to_generated = counts.get("genSegmentation / genSegmentation", 0)
        source_a.append(manual_to_generated)
        source_b.append(generated_to_generated)
    y = np.arange(len(labels))
    ax.barh(y, source_a, color="#263D53", height=0.56, label="Manual → generated")
    ax.barh(y, source_b, left=source_a, color="#9EB4C6", height=0.56, label="Generated → generated")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    max_count = max((a + b for a, b in zip(source_a, source_b)), default=1)
    ax.set_xlim(0, max_count * 1.28)
    ax.set_xlabel("Patient pairs")
    ax.set_title("C  Mask provenance", loc="left", pad=12)
    ax.grid(axis="x", color=PALETTE["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.tick_params(axis="x", colors=PALETTE["muted"])
    for yi, (a, b) in enumerate(zip(source_a, source_b)):
        if a:
            ax.text(a / 2, yi, str(a), ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        if b:
            ax.text(a + b / 2, yi, str(b), ha="center", va="center", color=PALETTE["ink"], fontsize=9, fontweight="bold")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.55, -0.26), ncol=1, fontsize=8)

    fig.text(
        0.07, 0.025,
        "Dataset-derived labels use the same GTV volumes and a pre-treatment t0; "
        "they are not independent expert calls or full clinical RANO 2.0 calls. CR is sparse.",
        fontsize=9, color=PALETTE["muted"], ha="left",
    )
    stem = output_dir / "fig01_cfb_cohort_readiness"
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=360, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the aggregate-only CFB-GBM cohort readiness figure.")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    plot_metadata_summary(args.summary, args.out)


if __name__ == "__main__":
    main()





