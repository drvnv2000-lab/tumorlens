"""Header and enhancing-label volume audit for native-space LUMIERE masks."""

from __future__ import annotations

import csv
from pathlib import Path

MASK_SPECS = {
    "deepbratumia": {
        "path": Path("DeepBraTumIA-segmentation/native/segmentation/ct1_seg_mask.nii.gz"),
        "enhancing_label": 1,
    },
    "hd_glio_auto": {
        "path": Path("HD-GLIO-AUTO-segmentation/native/segmentation_CT1_origspace.nii.gz"),
        "enhancing_label": 2,
    },
}


def audit_imaging(imaging_root: str | Path) -> tuple[dict, list[dict]]:
    """Inventory visits and measure each released method's contrast-enhancing label.

    DeepBraTumIA uses label 1 for enhancing core; HD-GLIO-AUTO uses label 2 for
    contrast-enhancing tumour. Outputs are mask-derived volumes, not expert RANO SPD
    measurements or clinical response calls.
    """
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError("Install the optional NIfTI dependency: pip install -e .[nifti]") from exc

    root = Path(imaging_root)
    if not root.is_dir():
        raise ValueError(f"Imaging root does not exist: {root}")
    visits = sorted(p for patient in root.glob("Patient-*") if patient.is_dir() for p in patient.glob("week-*") if p.is_dir())
    if not visits:
        raise ValueError(f"No Patient-*/week-* visit folders found under {root}")

    records: list[dict] = []
    for visit in visits:
        ct1 = visit / "CT1.nii.gz"
        try:
            ct1_img = nib.load(str(ct1)) if ct1.is_file() else None
            ct1_shape = tuple(ct1_img.shape[:3]) if ct1_img else None
            ct1_affine = np.asarray(ct1_img.affine) if ct1_img else None
        except Exception as exc:  # noqa: BLE001  preserve a row; report the data issue
            ct1_img, ct1_shape, ct1_affine = None, None, None
            ct1_error = type(exc).__name__
        else:
            ct1_error = ""

        row: dict = {
            "patient_id": visit.parent.name,
            "visit_id": visit.name,
            "ct1_present": bool(ct1_img),
            "ct1_read_error": ct1_error,
        }
        for method, rel_path in MASK_SPECS.items():
            path = visit / rel_path["path"]
            enhancing_label = rel_path["enhancing_label"]
            key = method
            row[f"{key}_mask_present"] = path.is_file()
            if not path.is_file():
                row.update({f"{key}_mask_read_error": "", f"{key}_enhancing_label": enhancing_label, f"{key}_enhancing_voxels": "", f"{key}_enhancing_mm3": "", f"{key}_same_voxel_grid_as_ct1": ""})
                continue
            try:
                img = nib.load(str(path))
                data = np.asanyarray(img.dataobj)
                voxels = int(np.count_nonzero(data == enhancing_label))
                voxel_mm3 = abs(float(np.linalg.det(np.asarray(img.affine)[:3, :3])))
                same_grid = bool(ct1_img and img.shape[:3] == ct1_shape and np.allclose(img.affine, ct1_affine, atol=1e-4, rtol=1e-5))
                row.update({
                    f"{key}_mask_read_error": "",
                    f"{key}_enhancing_label": enhancing_label,
                    f"{key}_enhancing_voxels": voxels,
                    f"{key}_enhancing_mm3": round(voxels * voxel_mm3, 3),
                    f"{key}_same_voxel_grid_as_ct1": same_grid,
                })
            except Exception as exc:  # noqa: BLE001  audit records the error type per file
                row.update({f"{key}_mask_read_error": type(exc).__name__, f"{key}_enhancing_label": enhancing_label, f"{key}_enhancing_voxels": "", f"{key}_enhancing_mm3": "", f"{key}_same_voxel_grid_as_ct1": False})
        records.append(row)

    summary = {
        "imaging_root": str(root),
        "n_visit_folders": len(records),
        "n_patients": len({r["patient_id"] for r in records}),
        "ct1_present": sum(bool(r["ct1_present"]) for r in records),
        "mask_availability": {
            method: sum(bool(r[f"{method}_mask_present"]) for r in records)
            for method in MASK_SPECS
        },
        "readable_mask_count": {
            method: sum(bool(r[f"{method}_mask_present"]) and not r[f"{method}_mask_read_error"] for r in records)
            for method in MASK_SPECS
        },
        "same_stored_voxel_grid_as_ct1": {
            method: sum(r[f"{method}_same_voxel_grid_as_ct1"] is True for r in records)
            for method in MASK_SPECS
        },
        "enhancing_label_by_method": {method: spec["enhancing_label"] for method, spec in MASK_SPECS.items()},
        "volume_definition": "count(voxel == method-specific enhancing label) * abs(det(mask affine 3x3)), in mm^3",
        "interpretation_warning": "These are mask-derived enhancing-label volumes, not expert bidimensional RANO measurements, validated lesion measurements, or response calls. Same-grid counts require identical stored shape and affine; differing axis order/orientation is not by itself a mask error, but spatial harmonization is required before voxelwise comparison or overlay.",
    }
    return summary, records


def write_imaging_audit(summary: dict, records: list[dict], out_dir: str | Path) -> None:
    import json

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "imaging_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if records:
        with (out / "mask_volume_inventory.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
