"""TumorLens v1: automated measurement of LUMIERE visits and descriptive analyses 1 to 3.

Every rule here is fixed in PREREGISTRATION.md (deviation of 2026-10-11, "analysis details
fixed before any automated measurement is computed"). Patient-level outputs stay local;
only aggregates are written for publication.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np

from . import rano

OFFSETS_MM = tuple(round(x * 0.5, 1) for x in range(-6, 7))  # -3.0 .. +3.0 mm
BOOTSTRAP_N = 10_000
SEED = 20261011

TOOLS = {
    "deepbratumia": (Path("DeepBraTumIA-segmentation/native/segmentation/ct1_seg_mask.nii.gz"), 1),
    "hd_glio_auto": (Path("HD-GLIO-AUTO-segmentation/native/segmentation_CT1_origspace.nii.gz"), 2),
}

_PAIR = re.compile(r"(\d+(?:\.\d+)?)\s*mm?\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm?", re.IGNORECASE)


def parse_expert_spd(text: str) -> tuple[float, int]:
    """Sum of products of every 'a mm x b mm' pair in the rationale, and the pair count."""
    pairs = [(float(a), float(b)) for a, b in _PAIR.findall(text or "")]
    return sum(a * b for a, b in pairs), len(pairs)


# --------------------------------------------------------------------------- measurement

def measure_mask(
    mask: np.ndarray,
    spacing: tuple[float, float, float],
    offsets: Sequence[float] = OFFSETS_MM,
    convention: str = "corner",
) -> dict:
    """Measure one canonical enhancing mask at each boundary offset."""
    axis = rano.measurement_axis(spacing)
    out = {"axis": axis, "spacing": tuple(float(s) for s in spacing), "by_offset": {}}
    voxel_mm3 = float(np.prod(spacing))
    if mask.any():
        pad = [(math.ceil((max(abs(o) for o in offsets) + 1.0) / s)) + 1 for s in spacing]
        idx = np.nonzero(mask)
        lo = [max(0, int(i.min()) - p) for i, p in zip(idx, pad)]
        hi = [min(n, int(i.max()) + p + 1) for i, n, p in zip(idx, mask.shape, pad)]
        crop = mask[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    else:
        crop = mask
    for o in offsets:
        m = rano.offset_mask_3d(crop, spacing, o) if crop.any() else crop
        les = rano.largest_lesion(m, spacing, axis, convention)
        out["by_offset"][o] = {
            "d1": les.d1_mm,
            "d2": les.d2_mm,
            "measurable": les.measurable,
            "enhancing_voxels": int(m.sum()),
            "volume_mm3": float(m.sum()) * voxel_mm3,
        }
    return out


def load_canonical_mask(path: Path, label: int) -> tuple[np.ndarray, tuple[float, float, float]]:
    import nibabel as nib

    img = nib.as_closest_canonical(nib.load(str(path)))
    data = np.asanyarray(img.dataobj)
    return data == label, tuple(float(z) for z in img.header.get_zooms()[:3])


def measure_visit(visit_dir: Path, convention: str = "corner") -> list[dict]:
    """Rows (one per tool and offset) for one visit folder; errors are recorded, not raised."""
    rows = []
    for tool, (rel, label) in TOOLS.items():
        base = {"patient_id": visit_dir.parent.name, "visit_id": visit_dir.name, "tool": tool}
        path = visit_dir / rel
        if not path.is_file():
            rows.append({**base, "status": "missing"})
            continue
        try:
            mask, spacing = load_canonical_mask(path, label)
            res = measure_mask(mask, spacing, convention=convention)
        except Exception as exc:  # noqa: BLE001  one unreadable file must not stop the run
            rows.append({**base, "status": f"error:{type(exc).__name__}"})
            continue
        for o, r in res["by_offset"].items():
            rows.append({**base, "status": "ok", "axis": res["axis"],
                         "spacing": "x".join(f"{s:.3g}" for s in res["spacing"]),
                         "offset_mm": o, **r})
    return rows


def spd_for_call(d1: float, d2: float) -> float:
    """SPD used for calls: product when measurable, else 0 (non-measurable disease)."""
    return d1 * d2 if min(d1, d2) >= rano.MIN_MEASURABLE_MM else 0.0


# --------------------------------------------------------------------------- series

CALL_RATINGS = {"CR", "PR", "SD", "PD"}


def build_series(ratings: Sequence[tuple[str, str, str]]) -> list[list[tuple[str, str]]]:
    """Split one patient's (visit_id, rating) rows, in time order, into RANO series.

    A 'Post-Op' row opens a series as baseline; CR/PR/SD/PD rows follow until the next
    'Post-Op'. 'Post-Op/PD' ends a series. Other rows are skipped. Returns lists of
    (visit_id, rating) whose first element is the baseline.
    """
    series: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] | None = None
    for _, visit, rating in ratings:
        if rating == "Post-Op":
            current = [(visit, rating)]
            series.append(current)
        elif rating == "Post-Op/PD":
            current = None
        elif rating in CALL_RATINGS and current is not None:
            current.append((visit, rating))
    return [s for s in series if len(s) >= 2]


def week_key(visit_id: str) -> tuple[int, int]:
    m = re.match(r"week-(\d+)(?:-(\d+))?", visit_id)
    if not m:
        raise ValueError(f"Unexpected visit id: {visit_id}")
    return int(m.group(1)), int(m.group(2) or 0)


# --------------------------------------------------------------------------- statistics

def bootstrap_ci(
    clusters: dict[str, list],
    stat: Callable[[list], float],
    n: int = BOOTSTRAP_N,
    seed: int = SEED,
) -> tuple[float, float, float]:
    """Point estimate and percentile 95% interval, resampling patients with replacement."""
    keys = sorted(clusters)
    flat = [x for k in keys for x in clusters[k]]
    point = stat(flat)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        pick = rng.integers(0, len(keys), len(keys))
        sample = [x for i in pick for x in clusters[keys[i]]]
        v = stat(sample)
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            vals.append(v)
    lo, hi = np.percentile(vals, [2.5, 97.5]) if vals else (math.nan, math.nan)
    return float(point), float(lo), float(hi)


def same_direction(a: float, b: float) -> bool:
    """Ties agree only when both changes are exactly zero."""
    return np.sign(a) == np.sign(b)


def direction_pairs_nadir(expert: Sequence[float], auto: Sequence[float]) -> list[bool]:
    """Analysis 2 as planned: change from the minimum of earlier values, per visit after the first."""
    out = []
    for i in range(1, len(expert)):
        de = expert[i] - min(expert[:i])
        da = auto[i] - min(auto[:i])
        out.append(bool(same_direction(de, da)))
    return out


def direction_pairs_consecutive(expert: Sequence[float], auto: Sequence[float]) -> list[bool]:
    """Suter-matched: sign of change between consecutive measured visits."""
    return [bool(same_direction(expert[i] - expert[i - 1], auto[i] - auto[i - 1]))
            for i in range(1, len(expert))]


def bootstrap(
    clusters: dict[str, list],
    stat: Callable[[list], float],
    n: int = BOOTSTRAP_N,
    seed: int = SEED,
) -> dict:
    """Like bootstrap_ci, plus the number of resamples where the statistic was undefined."""
    keys = sorted(clusters)
    flat = [x for k in keys for x in clusters[k]]
    point = stat(flat)
    rng = np.random.default_rng(seed)
    vals, undefined = [], 0
    for _ in range(n):
        pick = rng.integers(0, len(keys), len(keys))
        v = stat([x for i in pick for x in clusters[keys[i]]])
        if v is None or not math.isfinite(v):
            undefined += 1
        else:
            vals.append(v)
    lo, hi = np.percentile(vals, [2.5, 97.5]) if vals else (math.nan, math.nan)
    return {"estimate": round(float(point), 3) if point is not None else None,
            "ci95": [round(float(lo), 3), round(float(hi), 3)], "undefined_resamples": undefined}


def auroc(pairs: Sequence[tuple[float, bool]]) -> float:
    """Mann-Whitney AUROC of score for a binary outcome; ties count one half. NaN if one class."""
    pos = [s for s, y in pairs if y]
    neg = [s for s, y in pairs if not y]
    if not pos or not neg:
        return math.nan
    p = np.asarray(pos)[:, None]
    q = np.asarray(neg)[None, :]
    return float(((p > q).sum() + 0.5 * (p == q).sum()) / (len(pos) * len(neg)))


_NON_TARGET_ONLY = re.compile(r"^\s*non-?target", re.IGNORECASE)
_TARGET_TO_NM = re.compile(r"target\s*l(?:\.|esion)?\s*to\s*non-?measurable", re.IGNORECASE)


def expert_row_flags(text: str) -> dict[str, bool]:
    """Meaning flags from the hand audit of the expert-measurement rows (2026-10-11)."""
    return {"non_target_only": bool(_NON_TARGET_ONLY.match(text or "")),
            "target_became_non_measurable": bool(_TARGET_TO_NM.search(text or ""))}
