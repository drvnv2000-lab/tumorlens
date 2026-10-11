"""Measure every LUMIERE visit with both tools at every boundary offset (patient-level, local).

Usage: python scripts/run_v1_measure.py IMAGING_ROOT OUT_CSV [--workers 6] [--convention centre]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from tumorlens.v1 import measure_visit

FIELDS = ["patient_id", "visit_id", "tool", "status", "axis", "spacing", "offset_mm", "d1", "d2",
          "measurable", "enhancing_voxels", "volume_mm3"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("imaging_root", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--convention", choices=("corner", "centre"), default="corner")
    a = ap.parse_args(argv)
    visits = sorted(v for p in a.imaging_root.glob("Patient-*") for v in p.glob("week-*") if v.is_dir())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        futures = [ex.submit(measure_visit, v, a.convention) for v in visits]
        for i, f in enumerate(as_completed(futures), 1):
            rows.extend(f.result())
            if i % 50 == 0:
                print(f"{i}/{len(visits)} visits, {time.time() - t0:.0f} s", flush=True)
    rows.sort(key=lambda r: (r["patient_id"], r["visit_id"], r["tool"], r.get("offset_mm", 0)))
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Done: {len(visits)} visits, {len(rows)} rows, {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
