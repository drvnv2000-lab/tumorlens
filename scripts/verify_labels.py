"""Check which integer label is the contrast-enhancing compartment for each LUMIERE segmenter.

Three independent checks, written to an aggregate JSON (no patient-level rows):
  1. DeepBraTumIA's own output: per-label voxel volume in the atlas label map versus the named
     volumes in `measured_volumes_in_mm3.json`, written by DeepBraTumIA alongside the map.
  2. Signal: median intensity on post-contrast T1 (CT1) divided by pre-contrast T1, per label,
     from the released pyradiomics tables. The enhancing compartment brightens with contrast.
  3. Label names in the released pyradiomics tables, reported as found.

Usage: python scripts/verify_labels.py LUMIERE_ROOT OUT_JSON [--n-visits 60]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd


def volume_json_check(imaging: Path, n_visits: int, seed: int = 0) -> dict:
    files = sorted(imaging.glob("Patient-*/week-*/DeepBraTumIA-segmentation/atlas/segmentation/measured_volumes_in_mm3.json"))
    pick = random.Random(seed).sample(files, min(n_visits, len(files)))
    matches: dict[int, dict[str, int]] = {1: {}, 2: {}, 3: {}}
    all_exact = 0
    for f in pick:
        named = json.loads(f.read_text())
        img = nib.load(str(f.with_name("seg_mask.nii.gz")))
        data = np.asanyarray(img.dataobj)
        vox = abs(float(np.linalg.det(img.affine[:3, :3])))
        ok = True
        for label in (1, 2, 3):
            mm3 = float((data == label).sum()) * vox
            hits = [k for k, v in named.items() if abs(v - mm3) <= 1.0]
            ok &= len(hits) == 1
            for k in hits:
                matches[label][k] = matches[label].get(k, 0) + 1
        all_exact += int(ok)
    return {"visits_sampled": len(pick), "visits_with_all_three_labels_matched_uniquely": all_exact,
            "label_to_named_volume_counts": {str(k): v for k, v in matches.items()}}


def enhancement_check(csv_path: Path) -> dict:
    cols = ["Patient", "Time point", "Label", "Label name", "Sequence", "original_firstorder_Median"]
    d = pd.read_csv(csv_path, usecols=cols)
    names = d.groupby("Label")["Label name"].agg(lambda s: sorted(set(s))).to_dict()
    p = d.pivot_table(index=["Patient", "Time point"], columns=["Sequence", "Label"],
                      values="original_firstorder_Median").dropna()
    labels = sorted(d["Label"].unique())
    ratio = {lab: p[("CT1", lab)] / p[("T1", lab)] for lab in labels}
    out = {"visits_with_all_labels": len(p),
           "released_label_names": {str(k): v for k, v in names.items()},
           "median_ct1_over_t1": {str(k): round(float(v.median()), 3) for k, v in ratio.items()}}
    best = max(labels, key=lambda lab: float(ratio[lab].median()))
    others = [lab for lab in labels if lab != best]
    out["most_enhancing_label"] = int(best)
    out["share_of_visits_where_it_enhances_most"] = round(float(
        np.all([ratio[best] > ratio[o] for o in others], axis=0).mean()), 4)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--n-visits", type=int, default=60)
    a = ap.parse_args(argv)
    result = {
        "deepbratumia_volume_json": volume_json_check(a.root / "Imaging", a.n_visits),
        "deepbratumia_signal": enhancement_check(a.root / "LUMIERE-pyradiomics-deepbratumia-features.csv"),
        "hd_glio_auto_signal": enhancement_check(a.root / "LUMIERE-pyradiomics-hdglioauto-features.csv"),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
