"""Numerical check that the HD-GLIO-AUTO PIR rotation changes no v1 measurement.

For a seeded random sample of PIR-stored visits: measure the HD-GLIO-AUTO enhancing mask as
stored and after undoing the 180-degree in-plane rotation (flip of canonical axes 0 and 1), at
offsets -1, 0 and +1 mm, and compare with the stored v1 measurement table. Aggregate JSON only.

Usage: python scripts/check_pir_invariance.py IMAGING_ROOT MEASUREMENTS_CSV OUT_JSON [--n 25]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

from tumorlens.v1 import TOOLS, load_canonical_mask, measure_mask

OFFSETS = (-1.0, 0.0, 1.0)
KEYS = ("d1", "d2", "volume_mm3", "enhancing_voxels")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("measurements", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--n", type=int, default=25)
    a = ap.parse_args(argv)
    rel, label = TOOLS["hd_glio_auto"]
    stored = {}
    with a.measurements.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["tool"] == "hd_glio_auto" and r["status"] == "ok" and float(r["offset_mm"]) in OFFSETS:
                stored[(r["patient_id"], r["visit_id"], float(r["offset_mm"]))] = r
    pir = [v for p in sorted(a.root.glob("Patient-*")) for v in sorted(p.glob("week-*"))
           if (v / rel).is_file() and nib.aff2axcodes(nib.load(str(v / "CT1.nii.gz")).affine) == ("P", "I", "R")]
    sample = random.Random(20261011).sample(pir, min(a.n, len(pir)))
    max_diff_flip, max_diff_stored, nonempty = 0.0, 0.0, 0
    for v in sample:
        mask, sp = load_canonical_mask(v / rel, label)
        nonempty += int(mask.any())
        r0 = measure_mask(mask, sp, OFFSETS)["by_offset"]
        r1 = measure_mask(np.flip(mask, (0, 1)), sp, OFFSETS)["by_offset"]
        for o in OFFSETS:
            for k in KEYS:
                max_diff_flip = max(max_diff_flip, abs(float(r0[o][k]) - float(r1[o][k])))
                s = stored.get((v.parent.name, v.name, o))
                if s is not None:
                    max_diff_stored = max(max_diff_stored, abs(float(r0[o][k]) - float(s[k])))
    out = {"pir_visits_with_hd_mask": len(pir), "sampled": len(sample), "sampled_nonempty": nonempty,
           "offsets_mm": list(OFFSETS), "quantities": list(KEYS),
           "max_abs_difference_stored_vs_rotation_undone": max_diff_flip,
           "max_abs_difference_recomputed_vs_v1_table": max_diff_stored}
    a.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
