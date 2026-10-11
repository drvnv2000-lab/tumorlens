import csv

import nibabel as nib
import numpy as np
import pytest

from tumorlens import cfb_robustness as robustness
from tumorlens.cfb_qc import validate_cfb_qc_review


def save_nifti(path, data, affine=None):
    image = nib.Nifti1Image(data, np.eye(4) if affine is None else affine)
    nib.save(image, str(path))
    return path


@pytest.mark.parametrize(
    ("baseline", "followup", "expected"),
    [
        (100.0, 0.0, "Complete Response (CR)"),
        (100.0, 35.0, "Partial Response (PR)"),
        (100.0, 35.01, "Stable Disease (SD)"),
        (100.0, 140.0, "Progressive Disease (PD)"),
        (100.0, 139.99, "Stable Disease (SD)"),
    ],
)
def test_category_thresholds(baseline, followup, expected):
    assert robustness._category(baseline, followup) == expected


def test_category_rejects_nonpositive_baseline():
    with pytest.raises(ValueError, match="positive baseline"):
        robustness._category(0, 1)


def test_category_rejects_negative_followup():
    with pytest.raises(ValueError, match="finite and non-negative"):
        robustness._category(1, -0.1)


def test_volume_offsets_are_monotone_and_physical():
    mask = np.zeros((31, 31, 31), dtype=bool)
    mask[15, 15, 15] = True
    volumes = robustness._volumes_at_radii(mask, (1.0, 1.0, 2.0), 0.002)
    assert volumes[0.5]["dilate"] == pytest.approx(0.002)
    assert volumes[1.0]["dilate"] >= volumes[0.5]["dilate"]
    assert volumes[3.0]["dilate"] >= volumes[2.5]["dilate"]
    assert volumes[0.5]["erode"] == pytest.approx(0.002)
    assert all(volumes[radius]["erode"] == 0 for radius in (1.0, 1.5, 2.0, 2.5, 3.0))


def test_cropped_offsets_match_full_grid_reference():
    rng = np.random.default_rng(42)
    mask = rng.random((19, 17, 13)) > 0.96
    spacing = (0.8, 1.2, 2.0)
    voxel_cm3 = float(np.prod(spacing)) / 1000
    actual = robustness._volumes_at_radii(mask, spacing, voxel_cm3)
    margin = np.ceil(max(robustness.RADII_MM) / np.asarray(spacing)).astype(int) + 2
    padded = np.pad(mask, tuple((int(pad), int(pad)) for pad in margin), constant_values=False)
    original = tuple(slice(int(pad), int(pad) + size) for pad, size in zip(margin, mask.shape))
    inside = robustness.distance_transform_edt(padded, sampling=spacing)[original]
    outside = robustness.distance_transform_edt(~padded, sampling=spacing)[original]
    for radius, volumes in actual.items():
        expected_erode = np.count_nonzero(mask & (inside > radius)) * voxel_cm3
        expected_dilate = (
            int(mask.sum()) + np.count_nonzero((~mask) & (outside <= radius))
        ) * voxel_cm3
        assert volumes["erode"] == pytest.approx(expected_erode)
        assert volumes["dilate"] == pytest.approx(expected_dilate)


def test_empty_mask_offsets_remain_zero():
    volumes = robustness._volumes_at_radii(np.zeros((5, 6, 7), bool), (1, 1, 1), 0.001)
    assert all(value == {"erode": 0.0, "dilate": 0.0} for value in volumes.values())


def test_mask_geometry_reads_binary_nifti_and_spacing(tmp_path):
    affine = np.diag([0.8, 1.2, 2.0, 1.0])
    data = np.zeros((5, 6, 7), dtype=np.uint8)
    data[2, 3, 4] = 1
    path = save_nifti(tmp_path / "mask.nii.gz", data, affine)
    mask, spacing, voxel_cm3, digest, geometry = robustness._mask_geometry(path)
    assert mask.sum() == 1
    assert spacing == pytest.approx((0.8, 1.2, 2.0))
    assert voxel_cm3 == pytest.approx(0.00192)
    assert len(digest) == 64
    assert geometry["foreground_voxels"] == 1


def test_mask_geometry_rejects_nonbinary_mask(tmp_path):
    data = np.zeros((4, 4, 4), dtype=np.uint8)
    data[1, 1, 1] = 2
    path = save_nifti(tmp_path / "nonbinary.nii.gz", data)
    with pytest.raises(ValueError, match="not binary"):
        robustness._mask_geometry(path)


def test_mask_geometry_rejects_sheared_affine(tmp_path):
    affine = np.eye(4)
    affine[0, 1] = 0.25
    path = save_nifti(tmp_path / "sheared.nii.gz", np.zeros((4, 4, 4), dtype=np.uint8), affine)
    with pytest.raises(ValueError, match="Sheared voxel axes"):
        robustness._mask_geometry(path)


def test_bootstrap_interval_is_seeded_and_bounded():
    values = np.array([0, 0, 1, 1], dtype=float)
    first = robustness._bootstrap_interval(values, seed=7, repetitions=500)
    second = robustness._bootstrap_interval(values, seed=7, repetitions=500)
    assert first == second
    assert 0 <= first[0] <= 0.5 <= first[1] <= 1


def test_bootstrap_interval_empty_input():
    assert robustness._bootstrap_interval(np.array([]), seed=1) == (None, None)


def test_qc_gate_accepts_exact_reviewed_sample(tmp_path):
    manifest = tmp_path / "manifest.csv"
    review = tmp_path / "review.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("patient_id", "timepoint"))
        writer.writeheader()
        writer.writerow({"patient_id": "1", "timepoint": "t0"})
    fields = (
        "patient_id", "timepoint", "image_sha256", "mask_sha256",
        "overlay_checked", "overlay_usable", "reviewer",
    )
    row = {
        "patient_id": "1", "timepoint": "t0", "image_sha256": "a" * 64,
        "mask_sha256": "b" * 64, "overlay_checked": "YES", "overlay_usable": "YES",
        "reviewer": "AB",
    }
    with review.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    assert validate_cfb_qc_review(manifest, review)["all_overlays_usable"] is True


def test_qc_gate_rejects_missing_reviewer(tmp_path):
    manifest = tmp_path / "manifest.csv"
    review = tmp_path / "review.csv"
    manifest.write_text("patient_id,timepoint\n1,t0\n", encoding="utf-8")
    review.write_text(
        "patient_id,timepoint,image_sha256,mask_sha256,overlay_checked,overlay_usable,reviewer\n"
        f"1,t0,{'a' * 64},{'b' * 64},YES,YES,\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="reviewer initials"):
        validate_cfb_qc_review(manifest, review)
