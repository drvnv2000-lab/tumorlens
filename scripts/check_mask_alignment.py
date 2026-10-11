"""Check spatial alignment of each tool's native mask with CT1 and with the other tool.

For each visit: whole-tumour masks of both tools on the canonical CT1 grid; Dice between them
as stored and under each axis flip of the HD-GLIO-AUTO mask. A flip that beats the stored
orientation means the stored native-space mask is mirrored. Writes an aggregate JSON and,
with --details, a local patient-level CSV.

Usage: python scripts/check_mask_alignment.py IMAGING_ROOT OUT_JSON [--details CSV]
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel.processing import resample_from_to

DB = Path("DeepBraTumIA-segmentation/native/segmentation/ct1_seg_mask.nii.gz")
HD = Path("HD-GLIO-AUTO-segmentation/native/segmentation_CT1_origspace.nii.gz")
FLIPS = [f for r in range(4) for f in itertools.combinations((0, 1, 2), r)]


def on_ct1(path: Path, ct1) -> np.ndarray:
    img = nib.as_closest_canonical(nib.load(str(path)))
    if img.shape[:3] != ct1.shape[:3] or not np.allclose(img.affine, ct1.affine, atol=1e-3):
        img = resample_from_to(img, ct1, order=0)
    return np.asanyarray(img.dataobj) > 0


def dice(a: np.ndarray, b: np.ndarray) -> float:
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float("nan")


def check(visit: Path) -> dict | None:
    if not (visit / DB).is_file() or not (visit / HD).is_file():
        return None
    try:
        ct1 = nib.as_closest_canonical(nib.load(str(visit / "CT1.nii.gz")))
        db, hd = on_ct1(visit / DB, ct1), on_ct1(visit / HD, ct1)
    except Exception as exc:  # noqa: BLE001
        return {"patient_id": visit.parent.name, "visit_id": visit.name, "error": type(exc).__name__}
    if not db.any() or not hd.any():
        return {"patient_id": visit.parent.name, "visit_id": visit.name, "empty": True}
    scores = {"".join(map(str, f)) or "none": dice(db, np.flip(hd, f) if f else hd) for f in FLIPS}
    best = max(scores, key=scores.get)
    raw_ct1 = nib.load(str(visit / "CT1.nii.gz"))
    return {"patient_id": visit.parent.name, "visit_id": visit.name, "best_flip": best,
            "dice_stored": round(scores["none"], 3), "dice_best": round(scores[best], 3),
            "ct1_axcodes": "".join(nib.aff2axcodes(raw_ct1.affine)),
            "hd_axcodes": "".join(nib.aff2axcodes(nib.load(str(visit / HD)).affine)),
            "db_axcodes": "".join(nib.aff2axcodes(nib.load(str(visit / DB)).affine))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--details", type=Path)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    visits = sorted(v for p in a.root.glob("Patient-*") for v in p.glob("week-*") if v.is_dir())
    with ProcessPoolExecutor(a.workers) as ex:
        rows = [r for r in ex.map(check, visits) if r]
    ok = [r for r in rows if "best_flip" in r]
    mirrored = [r for r in ok if r["best_flip"] != "none" and r["dice_best"] >= r["dice_stored"] + 0.1]
    summary = {
        "visits_with_both_masks": len(rows),
        "visits_both_nonempty": len(ok),
        "best_flip_counts": dict(Counter(r["best_flip"] for r in ok)),
        "hd_mask_mirrored_dice_gain_ge_0.1": len(mirrored),
        "mirrored_by_ct1_orientation": dict(Counter(r["ct1_axcodes"] for r in mirrored)),
        "all_by_ct1_orientation": dict(Counter(r["ct1_axcodes"] for r in ok)),
        "median_dice_stored": float(np.median([r["dice_stored"] for r in ok])),
        "median_dice_best": float(np.median([r["dice_best"] for r in ok])),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if a.details:
        with a.details.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}))
            w.writeheader()
            w.writerows(rows)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
