"""Check which integer label is the contrast-enhancing compartment for each LUMIERE segmenter.

Three independent checks, written to an aggregate JSON (no patient-level rows):
  1. DeepBraTumIA's own output: per-label voxel volume in the atlas label map versus the named
     volumes in `measured_volumes_in_mm3.json`, written by DeepBraTumIA alongside the map.
  2. Signal: median intensity on post-contrast T1 (CT1) divided by pre-contrast T1, per label,
     from the released pyradiomics tables. The enhancing compartment brightens with contrast.
  3. Label names in the released pyradiomics tables, reported as found.
  4. Native CT1-space masks actually measured by v1 (added 2026-10-12): per-label volume of the
     native DeepBraTumIA mask against DeepBraTumIA's named volumes, and median CT1 intensity per
     label (relative to the brain median) for both tools on the CT1 grid.

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


def native_check(imaging: Path, n_visits: int, seed: int = 0) -> dict:
    """Checks on the native CT1-space masks that v1 measures (same visit sample as check 1)."""
    from nibabel.processing import resample_from_to

    files = sorted(imaging.glob("Patient-*/week-*/DeepBraTumIA-segmentation/atlas/segmentation/measured_volumes_in_mm3.json"))
    pick = random.Random(seed).sample(files, min(n_visits, len(files)))
    db_rel = Path("DeepBraTumIA-segmentation/native/segmentation/ct1_seg_mask.nii.gz")
    hd_rel = Path("HD-GLIO-AUTO-segmentation/native/segmentation_CT1_origspace.nii.gz")
    vol_ratio: dict[int, list[float]] = {1: [], 2: [], 3: []}
    names = {1: "Enhancing_Core", 2: "Necrotic_NonEnhancing", 3: "Edema_Compartment"}
    rel_int: dict[str, dict[int, list[float]]] = {"deepbratumia": {1: [], 2: [], 3: []}, "hd_glio_auto": {1: [], 2: []}}
    brightest = {"deepbratumia": [], "hd_glio_auto": []}
    used = 0
    for f in pick:
        visit = f.parents[3]
        if not (visit / db_rel).is_file() or not (visit / hd_rel).is_file():
            continue
        used += 1
        named = json.loads(f.read_text())
        raw_ct1 = nib.load(str(visit / "CT1.nii.gz"))
        ct1 = nib.as_closest_canonical(raw_ct1)
        ct = np.asanyarray(ct1.dataobj).astype(np.float32)
        brain = float(np.median(ct[ct > 0]))
        for tool, rel, labels in (("deepbratumia", db_rel, (1, 2, 3)), ("hd_glio_auto", hd_rel, (1, 2))):
            img = nib.as_closest_canonical(nib.load(str(visit / rel)))
            data = np.asanyarray(img.dataobj)
            if tool == "deepbratumia":
                vox = abs(float(np.linalg.det(img.affine[:3, :3])))
                for lab in labels:
                    if named.get(names[lab], 0) > 0:
                        vol_ratio[lab].append(float((data == lab).sum()) * vox / named[names[lab]])
            if img.shape[:3] != ct1.shape[:3] or not np.allclose(img.affine, ct1.affine, atol=1e-3):
                data = np.asanyarray(resample_from_to(img, ct1, order=0).dataobj)
            if tool == "hd_glio_auto" and nib.aff2axcodes(raw_ct1.affine) == ("P", "I", "R"):
                data = np.flip(data, (0, 1))  # released rotation, see reports/v1/mask_alignment.json
            med = {}
            for lab in labels:
                m = data == lab
                if m.sum() >= 20:
                    med[lab] = float(np.median(ct[m])) / brain
                    rel_int[tool][lab].append(med[lab])
            enh = 1 if tool == "deepbratumia" else 2
            if enh in med and len(med) > 1:
                brightest[tool].append(max(med, key=med.get) == enh)
    return {
        "visits_used": used,
        "deepbratumia_native_volume_over_named_volume_median": {
            f"{k} ({names[k]})": round(float(np.median(v)), 3) for k, v in vol_ratio.items() if v},
        "median_ct1_relative_to_brain_median": {
            t: {str(k): round(float(np.median(v)), 3) for k, v in d.items() if v} for t, d in rel_int.items()},
        "enhancing_label_brightest_on_ct1": {
            t: f"{sum(v)} of {len(v)}" for t, v in brightest.items()},
        "enhancing_label_tested": {"deepbratumia": 1, "hd_glio_auto": 2},
    }


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
        "native_ct1_masks": native_check(a.root / "Imaging", a.n_visits),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
