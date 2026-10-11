"""Transparent threshold calculations; deliberately not a complete RANO implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Response = Literal["CR", "PR", "SD", "PD", "NOT_ASSESSABLE"]


@dataclass(frozen=True)
class ThresholdResult:
    response: Response
    percent_from_baseline: float | None
    percent_from_nadir: float | None
    pd_threshold_mm2: float | None
    pr_threshold_mm2: float | None
    threshold_margin_fraction: float | None
    rule_set: str
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


def bidimensional_threshold_call(
    *,
    baseline_spd_mm2: float | None,
    nadir_spd_mm2: float | None,
    current_spd_mm2: float | None,
    measurable: bool = True,
    new_lesion: bool = False,
    rule_set: str = "rano_2_0_radiographic_thresholds",
) -> ThresholdResult:
    """Return a *radiographic threshold* category for bidimensional SPD.

    This calculation does not assess neurologic status, corticosteroid dose,
    confirmation scans, treatment context, or all non-target-lesion rules.
    ``nadir_spd_mm2`` must be the smallest valid prior measurement including
    the current visit only when that is explicitly the analysis definition.
    """
    if new_lesion:
        return ThresholdResult(
            "PD", None, None, None, None, 0.0, rule_set,
            "New lesion flag supplied by the curated manifest; not inferred from a mask.",
        )
    vals = (baseline_spd_mm2, nadir_spd_mm2, current_spd_mm2)
    if not measurable or any(v is None for v in vals):
        return ThresholdResult(
            "NOT_ASSESSABLE", None, None, None, None, None, rule_set,
            "Missing or non-measurable target lesion. This is not a complete RANO category.",
        )
    baseline, nadir, current = (float(v) for v in vals)
    if min(baseline, nadir, current) < 0 or baseline == 0 or nadir == 0:
        raise ValueError("SPD values must be non-negative and baseline/nadir must be > 0.")

    pd_cut = 1.25 * nadir
    pr_cut = 0.50 * baseline
    delta_base = (current / baseline) - 1.0
    delta_nadir = (current / nadir) - 1.0
    if current >= pd_cut:
        call: Response = "PD"
        margin = (current - pd_cut) / max(pd_cut, 1e-12)
    elif current <= pr_cut:
        call = "PR"
        margin = (pr_cut - current) / max(pr_cut, 1e-12)
    else:
        call = "SD"
        # The nearest boundary, normalized to the threshold value.
        margin = min((current - pr_cut) / max(pr_cut, 1e-12), (pd_cut - current) / max(pd_cut, 1e-12))
    return ThresholdResult(
        call, delta_base * 100.0, delta_nadir * 100.0, pd_cut, pr_cut,
        max(0.0, float(margin)), rule_set,
        "Bidimensional threshold-only result; apply protocol-specific clinical and confirmation criteria separately.",
    )


def volume_threshold_call(
    *,
    baseline_mm3: float | None,
    nadir_mm3: float | None,
    current_mm3: float | None,
    measurable: bool = True,
) -> ThresholdResult:
    """RANO 2.0 volumetric threshold flags (PR -65%, PD +40%) only."""
    vals = (baseline_mm3, nadir_mm3, current_mm3)
    if not measurable or any(v is None for v in vals):
        return ThresholdResult("NOT_ASSESSABLE", None, None, None, None, None,
                               "rano_2_0_volumetric_thresholds",
                               "Missing or non-measurable disease; not a full response category.")
    baseline, nadir, current = (float(v) for v in vals)
    if min(baseline, nadir, current) < 0 or baseline == 0 or nadir == 0:
        raise ValueError("Volume values must be non-negative and baseline/nadir must be > 0.")
    pd_cut, pr_cut = 1.40 * nadir, 0.35 * baseline
    if current >= pd_cut:
        call: Response = "PD"
        margin = (current - pd_cut) / max(pd_cut, 1e-12)
    elif current <= pr_cut:
        call = "PR"
        margin = (pr_cut - current) / max(pr_cut, 1e-12)
    else:
        call = "SD"
        margin = min((current - pr_cut) / max(pr_cut, 1e-12), (pd_cut - current) / max(pd_cut, 1e-12))
    return ThresholdResult(call, (current / baseline - 1) * 100, (current / nadir - 1) * 100,
                           pd_cut, pr_cut, max(0.0, float(margin)),
                           "rano_2_0_volumetric_thresholds",
                           "Volumetric threshold-only result; not a complete clinical RANO assessment.")
