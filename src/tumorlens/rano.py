"""Bidimensional RANO measurement and response calls, written from the published criteria.

Criteria used (RANO 1.0, bidimensional, Wen et al. 2010):
  * a lesion is measurable when both perpendicular diameters are at least 10 mm;
  * the sum of products of perpendicular diameters (SPD) is the tumour burden;
  * progression (PD): SPD at least 25 percent above the nadir (smallest SPD at any earlier
    scan, baseline included);
  * partial response (PR): SPD at least 50 percent below baseline;
  * complete response (CR): no enhancing disease;
  * otherwise stable disease (SD).
Confirmation windows, steroid use, clinical status and non-enhancing disease are NOT modelled:
this is a measurement-driven call, and the write-up says so.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

MIN_MEASURABLE_MM = 10.0
PD_FACTOR = 1.25
PR_FACTOR = 0.50


@dataclass(frozen=True)
class Lesion:
    d1_mm: float  # longest diameter in the slice
    d2_mm: float  # longest diameter perpendicular to d1
    slice_index: int

    @property
    def product(self) -> float:
        return self.d1_mm * self.d2_mm

    @property
    def measurable(self) -> bool:
        return self.d1_mm >= MIN_MEASURABLE_MM and self.d2_mm >= MIN_MEASURABLE_MM


def _pixel_corners(mask2d: np.ndarray, spacing_xy: tuple[float, float]) -> np.ndarray:
    """All pixel-corner coordinates (mm) of foreground pixels, so a single pixel has size 1."""
    ys, xs = np.nonzero(mask2d)
    sy, sx = spacing_xy
    pts = []
    for dy in (0.0, 1.0):
        for dx in (0.0, 1.0):
            pts.append(np.column_stack([(xs + dx) * sx, (ys + dy) * sy]))
    return np.unique(np.vstack(pts), axis=0)


def bidimensional(mask2d: np.ndarray, spacing_xy: tuple[float, float]) -> tuple[float, float]:
    """Longest in-plane diameter and the longest diameter perpendicular to it, in mm.

    Uses the convex hull of the foreground, so it measures the tumour outline and is
    invariant to rotation. Returns (0, 0) for an empty mask.
    """
    if not mask2d.any():
        return 0.0, 0.0
    pts = _pixel_corners(mask2d, spacing_xy)
    if len(pts) < 3:
        return 0.0, 0.0
    try:
        hull = pts[ConvexHull(pts).vertices]
    except (ValueError, RuntimeError):  # collinear points (Qhull error)
        hull = pts
    diff = hull[:, None, :] - hull[None, :, :]
    dist = np.sqrt((diff**2).sum(-1))
    i, j = np.unravel_index(np.argmax(dist), dist.shape)
    d1 = float(dist[i, j])
    u = (hull[j] - hull[i]) / d1
    perp = np.array([-u[1], u[0]])
    proj = hull @ perp
    return d1, float(proj.max() - proj.min())


def measurement_axis(spacing: tuple[float, float, float], ratio: float = 1.5) -> int:
    """Slice axis of the acquisition: the coarsest axis if it is at least `ratio` times the
    finest, else the third (axial, for canonical RAS volumes)."""
    if max(spacing) >= ratio * min(spacing):
        return int(np.argmax(spacing))
    return 2


def largest_lesion(
    mask3d: np.ndarray, spacing: tuple[float, float, float], axis: int = 2
) -> Lesion:
    """Measure the largest 26-connected 3D component on its maximal slice along `axis`.

    mask3d is indexed (x, y, z); spacing is (sx, sy, sz) in mm. The default axis 2 gives
    axial slices for a canonical (RAS) volume.
    """
    if not mask3d.any():
        return Lesion(0.0, 0.0, -1)
    structure = np.ones((3, 3, 3), dtype=bool)
    components, n_components = ndimage.label(mask3d, structure=structure)
    if n_components == 0:
        return Lesion(0.0, 0.0, -1)
    sizes = np.bincount(components.ravel(), minlength=n_components + 1)
    sizes[0] = 0
    largest = int(np.argmax(sizes))
    lesion_mask = np.moveaxis(components == largest, axis, 2)
    sp = [s for i, s in enumerate(spacing) if i != axis]
    areas = lesion_mask.sum(axis=(0, 1))
    k = int(np.argmax(areas))
    d1, d2 = bidimensional(lesion_mask[:, :, k].T, (sp[1], sp[0]))
    return Lesion(d1, d2, k)


def offset_mask_3d(
    mask3d: np.ndarray, spacing: tuple[float, float, float], offset_mm: float
) -> np.ndarray:
    """Grow (offset > 0) or shrink (offset < 0) a 3D mask boundary by offset_mm, in mm."""
    if offset_mm == 0:
        return mask3d.copy()
    if offset_mm > 0:
        return ndimage.distance_transform_edt(~mask3d, sampling=spacing) <= offset_mm
    return ndimage.distance_transform_edt(mask3d, sampling=spacing) > -offset_mm


def offset_mask(mask2d: np.ndarray, spacing_xy: tuple[float, float], offset_mm: float) -> np.ndarray:
    """Grow (offset > 0) or shrink (offset < 0) a mask boundary by offset_mm."""
    if offset_mm == 0:
        return mask2d.copy()
    if offset_mm > 0:
        d = ndimage.distance_transform_edt(~mask2d, sampling=spacing_xy)
        return d <= offset_mm
    d = ndimage.distance_transform_edt(mask2d, sampling=spacing_xy)
    return d > -offset_mm


def call_series(spd: list[float], enhancing: list[bool] | None = None) -> list[str]:
    """RANO bidimensional calls for a series of SPD values; the first entry is the baseline.

    Calls compare with the nadir, never with the previous scan. SPD counts measurable lesions
    only, so it is 0 when there is no measurable disease. When the nadir is 0, a measurable
    lesion is PD. `enhancing` says whether any enhancing tissue is present at each scan: an SPD
    of 0 is CR only without enhancing tissue; with enhancing tissue the PR and SD rules apply.
    Without `enhancing`, an SPD of 0 is CR. Rule order: CR, then PD, then PR, then SD. The nadir
    includes every earlier scan, so non-measurable scans (SPD 0) set the nadir to 0; this is a
    study convention (PREREGISTRATION.md, 2026-10-11), not a clinical RANO assessment.
    """
    if not spd:
        return []
    if enhancing is None:
        enhancing = [v > 0 for v in spd]
    if len(enhancing) != len(spd):
        raise ValueError("spd and enhancing must have the same length")
    out = ["Baseline"]
    baseline = spd[0]
    nadir = baseline
    for v, enh in zip(spd[1:], enhancing[1:]):
        if v == 0 and not enh:
            out.append("CR")
        elif (nadir > 0 and v >= PD_FACTOR * nadir) or (nadir == 0 and v > 0):
            out.append("PD")
        elif baseline > 0 and v <= PR_FACTOR * baseline:
            out.append("PR")
        else:
            out.append("SD")
        nadir = min(nadir, v)
    return out


def flip_margin(
    spd_by_offset: dict[float, list[float]],
    index: int,
    enhancing_by_offset: dict[float, list[bool]] | None = None,
) -> float | None:
    """Smallest absolute boundary offset (mm) at which the call at `index` changes.

    spd_by_offset maps a boundary offset in mm (applied to every scan alike) to the SPD
    series computed at that offset; offset 0 must be present. Returns None if no tested
    offset changes the call.
    """
    enh = enhancing_by_offset or {}
    base = call_series(spd_by_offset[0.0], enh.get(0.0))[index]
    flips = [abs(o) for o, s in spd_by_offset.items() if call_series(s, enh.get(o))[index] != base]
    return min(flips) if flips else None
