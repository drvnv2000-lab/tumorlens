"""Patient-clustered risk/coverage evaluation for precomputed deferral scores."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _curve(y: np.ndarray, score: np.ndarray, coverages: np.ndarray) -> list[dict[str, float | int]]:
    n = len(y)
    order = np.argsort(score, kind="stable")  # low score = safer to answer
    out = []
    for coverage in coverages:
        k = max(1, min(n, round(float(coverage) * n)))
        answered = order[:k]
        out.append({
            "requested_coverage": float(coverage),
            "actual_coverage": float(k / n),
            "n_answered": int(k),
            "discordance_rate_answered": float(np.mean(y[answered])),
        })
    return out


def risk_coverage(
    frame: pd.DataFrame,
    *,
    patient_col: str = "patient_id",
    outcome_col: str = "expert_discordant",
    score_cols: tuple[str, ...] = ("threshold_risk_score", "segmentation_risk_score"),
    bootstrap_reps: int = 1000,
    seed: int = 20261011,
) -> pd.DataFrame:
    required = {patient_col, outcome_col, *score_cols}
    absent = required - set(frame.columns)
    if absent:
        raise ValueError(f"Manifest missing required analysis columns: {sorted(absent)}")
    d = frame.copy()
    d[outcome_col] = pd.to_numeric(d[outcome_col], errors="coerce")
    d = d.dropna(subset=[patient_col, outcome_col, *score_cols])
    if d.empty:
        raise ValueError("No complete rows for selective-risk analysis.")
    if not set(d[outcome_col].astype(int).unique()).issubset({0, 1}):
        raise ValueError(f"{outcome_col} must be binary (0/1).")
    if (pd.to_numeric(d[list(score_cols)].stack(), errors="coerce") < 0).any():
        raise ValueError("Deferral scores must be non-negative, with larger values indicating greater risk.")

    patients = d[patient_col].astype(str).unique()
    groups: dict[str, np.ndarray] = {
        p: np.flatnonzero(d[patient_col].astype(str).to_numpy() == p) for p in patients
    }
    y = d[outcome_col].astype(int).to_numpy()
    coverages = np.linspace(0.50, 1.0, 11)
    rng = np.random.default_rng(seed)
    bootstrap_indices: list[np.ndarray] = []
    for _ in range(max(0, bootstrap_reps)):
        sampled = rng.choice(patients, size=len(patients), replace=True)
        # Repeated sampled patients are repeated clusters, as in cluster bootstrap.
        bootstrap_indices.append(np.concatenate([groups[p] for p in sampled]))

    records: list[dict] = []
    curves_by_strategy: dict[str, list[dict]] = {}
    bootstrap_by_strategy: dict[str, list[list[dict]]] = {}
    for col in score_cols:
        score = pd.to_numeric(d[col], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(score).all():
            raise ValueError(f"Score column {col!r} contains non-finite values.")
        point = _curve(y, score, coverages)
        boot_curves = [_curve(y[idx], score[idx], coverages) for idx in bootstrap_indices]
        curves_by_strategy[col] = point
        bootstrap_by_strategy[col] = boot_curves
        for j, p in enumerate(point):
            vals = np.array([bc[j]["discordance_rate_answered"] for bc in boot_curves], dtype=float)
            p.update({
                "strategy": col,
                "patients": len(patients),
                "rows": len(d),
                "discordance_ci_low": float(np.quantile(vals, .025)) if len(vals) else math.nan,
                "discordance_ci_high": float(np.quantile(vals, .975)) if len(vals) else math.nan,
                "bootstrap_reps": len(vals),
                "seed": int(seed),
            })
            records.append(p)
    result = pd.DataFrame.from_records(records)
    # Paired patient-cluster bootstrap contrast for the two planned scores.
    if len(score_cols) == 2:
        left, right = score_cols
        contrasts = []
        for j, coverage in enumerate(coverages):
            point_delta = (curves_by_strategy[right][j]["discordance_rate_answered"]
                           - curves_by_strategy[left][j]["discordance_rate_answered"])
            vals = np.array([
                b_right[j]["discordance_rate_answered"] - b_left[j]["discordance_rate_answered"]
                for b_left, b_right in zip(bootstrap_by_strategy[left], bootstrap_by_strategy[right])
            ], dtype=float)
            contrasts.append({
                "requested_coverage": float(coverage),
                "actual_coverage": float(curves_by_strategy[left][j]["actual_coverage"]),
                "contrast": f"{right} minus {left}",
                "discordance_difference": float(point_delta),
                "difference_ci_low": float(np.quantile(vals, .025)) if len(vals) else math.nan,
                "difference_ci_high": float(np.quantile(vals, .975)) if len(vals) else math.nan,
                "bootstrap_reps": len(vals),
                "seed": int(seed),
            })
        result.attrs["paired_contrasts"] = contrasts
    return result


def make_analysis_frame(manifest: pd.DataFrame) -> pd.DataFrame:
    """Create the two pre-specified, transparent deferral scores.

    Required columns: expert_call, automated_call, segmentation_spread_fraction,
    threshold_margin_fraction. A larger score means defer sooner.
    """
    required = {"patient_id", "expert_call", "automated_call", "segmentation_spread_fraction", "threshold_margin_fraction"}
    absent = required - set(manifest.columns)
    if absent:
        raise ValueError(f"Manifest missing required columns: {sorted(absent)}")
    d = manifest.copy()
    if "measurement_driven" in d:
        d = d[d["measurement_driven"].astype(str).str.casefold().isin({"true", "1", "yes"})].copy()
    d["expert_discordant"] = (d["expert_call"].astype(str).str.upper() != d["automated_call"].astype(str).str.upper()).astype(int)
    margin = pd.to_numeric(d["threshold_margin_fraction"], errors="coerce")
    # Monotone bounded transform: 1 at the boundary, approaches 0 as margin grows.
    d["threshold_risk_score"] = 1.0 / (1.0 + margin)
    d["segmentation_risk_score"] = pd.to_numeric(d["segmentation_spread_fraction"], errors="coerce")
    return d
