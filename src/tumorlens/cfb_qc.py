from __future__ import annotations

import csv
import hashlib
import html
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def _key(row: dict[str, str]) -> tuple[str, str]:
    return row["patient_id"].strip(), row["timepoint"].strip()


def _display_slices(image_data: np.ndarray, mask_data: np.ndarray, out: Path, label: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Install the declared matplotlib dependency to render the QC gallery.") from exc
    mask = mask_data != 0
    if image_data.ndim != 3 or mask.ndim != 3 or image_data.shape != mask.shape:
        raise ValueError("QC image and GTV mask must have matching 3D dimensions.")
    # Reorient both already-registered inputs to canonical axes for consistent axial display.
    mask_indices = np.argwhere(mask)
    if mask_indices.size:
        center = mask_indices.mean(axis=0)
        occupied = np.flatnonzero(mask.sum(axis=(0, 1)))
        middle = int(occupied[np.argmin(np.abs(occupied - center[2]))])
    else:
        middle = mask.shape[2] // 2
    slice_indices = [max(0, middle - 2), middle, min(mask.shape[2] - 1, middle + 2)]
    shown = np.stack([image_data[:, :, k] for k in slice_indices])
    finite = shown[np.isfinite(shown)]
    if not finite.size:
        raise ValueError("QC T1-Gd image has no finite intensities.")
    low, high = np.percentile(finite, [1, 99])
    if not np.isfinite([low, high]).all() or high <= low:
        low = float(finite.min())
        high = float(finite.max())
    if high <= low:
        raise ValueError("QC T1-Gd image has no displayable intensity range.")

    fig, axes = plt.subplots(1, 3, figsize=(11.8, 4.0), constrained_layout=True)
    fig.patch.set_facecolor("#111820")
    for ax, k in zip(axes, slice_indices, strict=True):
        ax.imshow(image_data[:, :, k].T, cmap="gray", origin="lower", vmin=low, vmax=high)
        plane = mask[:, :, k].T.astype(np.uint8)
        if plane.any():
            ax.contour(plane, levels=[0.5], colors=["#ff4566"], linewidths=1.2)
        ax.set_title(f"Axial slice {k + 1}", fontsize=10, color="#dce7ef")
        ax.axis("off")
    fig.suptitle(f"{label} · T1-Gd with released GTV contour", fontsize=12, fontweight="semibold", color="#f1f5f9")
    fig.savefig(out, dpi=180, facecolor="#111820")
    plt.close(fig)


def build_cfb_qc_gallery(
    qc_manifest_path: str | Path,
    mask_manifest_path: str | Path,
    imaging_root: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    """Render the prespecified, outcome-independent T1-Gd/GTV overlay review gallery."""
    qc_manifest = Path(qc_manifest_path)
    mask_manifest = Path(mask_manifest_path)
    root = Path(imaging_root)
    out = Path(out_dir)
    if not qc_manifest.is_file() or not mask_manifest.is_file() or not root.is_dir():
        raise FileNotFoundError("QC manifest, mask manifest, or imaging root is missing.")
    qc_rows = _read_csv(qc_manifest)
    mask_rows = _read_csv(mask_manifest)
    masks = {_key(row): row["relative_path"] for row in mask_rows}
    expected = {_key(row) for row in qc_rows}
    if len(expected) != len(qc_rows) or not qc_rows:
        raise ValueError("QC manifest must contain unique, non-empty patient/timepoint rows.")
    out.mkdir(parents=True, exist_ok=True)
    overlays = out / "overlays"
    overlays.mkdir(parents=True, exist_ok=True)
    review_rows: list[dict[str, str]] = []
    cards: list[str] = []
    for row in qc_rows:
        patient_id, timepoint = _key(row)
        key = (patient_id, timepoint)
        if key not in masks:
            raise ValueError(f"No GTV mask in the mask manifest for {patient_id}/{timepoint}.")
        image_path = root / row["relative_path"]
        mask_path = root / masks[key]
        if not image_path.is_file() or not mask_path.is_file():
            raise FileNotFoundError(f"Missing prespecified QC input for {patient_id}/{timepoint}.")
        image = nib.load(str(image_path))
        mask = nib.load(str(mask_path))
        if len(image.shape) != 3 or len(mask.shape) != 3:
            raise ValueError(f"QC inputs must be 3D for {patient_id}/{timepoint}.")
        if image.shape != mask.shape or not np.allclose(image.affine, mask.affine, atol=1e-4, rtol=1e-5):
            raise ValueError(f"T1-Gd and GTV geometry differ for {patient_id}/{timepoint}; inspect the source before outcomes.")
        # Canonical reorientation is applied identically after matching the native grids.
        image = nib.as_closest_canonical(image)
        mask = nib.as_closest_canonical(mask)
        image_data = np.asanyarray(image.dataobj, dtype=np.float32)
        mask_data = np.asanyarray(mask.dataobj)
        if not np.isfinite(image_data).all() or not np.isfinite(mask_data).all():
            raise ValueError(f"QC input contains non-finite voxels for {patient_id}/{timepoint}.")
        if not set(np.unique(mask_data).tolist()).issubset({0, 1}):
            raise ValueError(f"QC GTV mask is not binary for {patient_id}/{timepoint}.")
        filename = f"patient-{int(patient_id):03d}_{timepoint}.png"
        _display_slices(image_data, mask_data, overlays / filename, f"Patient {int(patient_id):03d} · {timepoint}")
        review_rows.append({
            "patient_id": patient_id,
            "timepoint": timepoint,
            "image_path": row["relative_path"],
            "mask_path": masks[key],
            "image_sha256": _sha256(image_path),
            "mask_sha256": _sha256(mask_path),
            "mask_foreground_voxels": str(int(np.count_nonzero(mask_data))),
            "overlay_checked": "",
            "overlay_usable": "",
            "reviewer": "",
            "issues": "",
        })
        cards.append(
            f'<article><h2>Patient {int(patient_id):03d} · {html.escape(timepoint)}</h2>'
            f'<img src="overlays/{html.escape(filename)}" alt="T1-Gd with GTV contour overlay"></article>'
        )
    with (out / "qc_review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TumorLens · CFB-GBM pre-outcome QC</title><style>
:root{color-scheme:dark;background:#0b1117;color:#e8edf2;font:15px/1.5 system-ui,sans-serif}body{max-width:1100px;margin:36px auto;padding:0 20px}h1{font-size:26px;margin:0 0 8px}p{color:#a9b6c3;max-width:80ch}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}article{background:#121b24;border:1px solid #263544;border-radius:14px;padding:14px}h2{font-size:15px;margin:0 0 10px;color:#d9e5ee}img{width:100%;height:auto;border-radius:8px;border:1px solid #283744}code{color:#f7b267}</style><body>
<h1>CFB-GBM · Pre-outcome overlay review</h1><p>Review each locked T1-Gd/GTV overlay without viewing response categories or perturbation results. Confirm that the released contour is visible on the expected anatomy and that the overlay is usable. A zero-voxel mask is displayed without a contour; verify that this is the expected zero-volume follow-up before marking it usable. Record every row in <code>qc_review.csv</code>: set <code>overlay_checked</code> and <code>overlay_usable</code> to YES, and enter reviewer initials. If any overlay is unusable or a systematic alignment issue appears, stop and investigate before running the robustness analysis.</p>
<main>__CARDS__</main></body></html>""".replace("__CARDS__", "\n".join(cards))
    (out / "index.html").write_text(page, encoding="utf-8")
    return {"qc_pairs": len(review_rows), "gallery": "index.html", "review_template": "qc_review.csv", "outcome_independent": True}


def validate_cfb_qc_review(qc_manifest_path: str | Path, review_path: str | Path) -> dict[str, Any]:
    """Fail closed unless every locked overlay was reviewed and deemed usable."""
    expected_rows = _read_csv(Path(qc_manifest_path))
    review_rows = _read_csv(Path(review_path))
    expected = {_key(row) for row in expected_rows}
    observed = [_key(row) for row in review_rows]
    if len(expected) != len(expected_rows) or len(set(observed)) != len(observed):
        raise ValueError("QC manifest or review file contains duplicate patient/timepoint entries.")
    if set(observed) != expected:
        raise ValueError("QC review rows must match the locked patient/timepoint sample exactly.")
    input_digest = hashlib.sha256()
    for row in review_rows:
        for column in ("image_sha256", "mask_sha256"):
            value = row.get(column, "").strip()
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
                raise ValueError("QC review rows must preserve image and mask SHA-256 hashes.")
            input_digest.update(value.lower().encode("ascii"))
            input_digest.update(b"\n")
        if row.get("overlay_checked", "").strip().upper() != "YES":
            raise ValueError("Every prespecified overlay must be marked YES in overlay_checked.")
        if row.get("overlay_usable", "").strip().upper() != "YES":
            raise ValueError("Every prespecified overlay must be marked YES in overlay_usable; stop and investigate issues first.")
        if not row.get("reviewer", "").strip():
            raise ValueError("Enter reviewer initials for every prespecified overlay.")
    return {
        "qc_pairs_reviewed": len(review_rows),
        "all_overlays_usable": True,
        "input_digest_sha256": input_digest.hexdigest(),
        "qc_manifest_sha256": _sha256(Path(qc_manifest_path)),
    }