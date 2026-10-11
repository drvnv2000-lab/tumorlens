from __future__ import annotations

import csv
import hashlib
import json
import platform
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import scipy
from scipy.ndimage import distance_transform_edt

from . import __version__
from .cfb_qc import validate_cfb_qc_review

PAIR_FIELDS = (
    ("t0_to_t1", "t0", "t1", "size_t0 (cm3)", "size_t1 (cm3)", "rano_t0_to_t1"),
    ("t0_to_t2", "t0", "t2", "size_t0 (cm3)", "size_t2 (cm3)", "rano_t0_to_t2"),
    ("t1_to_t2", "t1", "t2", "size_t1 (cm3)", "size_t2 (cm3)", "rano_t1_to_t2"),
)
RADII_MM = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
CATEGORIES = (
    "Complete Response (CR)",
    "Partial Response (PR)",
    "Stable Disease (SD)",
    "Progressive Disease (PD)",
)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _category(baseline_cm3: float, followup_cm3: float) -> str:
    if not np.isfinite([baseline_cm3, followup_cm3]).all() or baseline_cm3 <= 0 or followup_cm3 < 0:
        raise ValueError("Volumes must be finite and non-negative, with a positive baseline.")
    if followup_cm3 == 0:
        return "Complete Response (CR)"
    if followup_cm3 <= baseline_cm3 * 0.35:
        return "Partial Response (PR)"
    if followup_cm3 >= baseline_cm3 * 1.40:
        return "Progressive Disease (PD)"
    return "Stable Disease (SD)"


def _mask_geometry(path: Path) -> tuple[np.ndarray, tuple[float, float, float], float, str, dict[str, Any]]:
    image = nib.load(str(path))
    if len(image.shape) != 3 or not np.isfinite(image.affine).all():
        raise ValueError("Mask must be a finite-affine 3D NIfTI.")
    determinant = float(np.linalg.det(image.affine[:3, :3]))
    if not np.isfinite(determinant) or abs(determinant) < 1e-8:
        raise ValueError("Mask affine is singular.")
    basis = image.affine[:3, :3]
    gram = basis.T @ basis
    axis_lengths = np.sqrt(np.diag(gram))
    cosine = gram / np.outer(axis_lengths, axis_lengths)
    if not np.allclose(cosine, np.eye(3), atol=1e-5, rtol=0):
        raise ValueError("Sheared voxel axes are unsupported by the spacing-only distance transform.")
    spacing = tuple(float(x) for x in nib.affines.voxel_sizes(image.affine))
    if len(spacing) != 3 or any((not np.isfinite(x) or x <= 0) for x in spacing):
        raise ValueError("Mask voxel spacing must be finite and positive.")
    values = np.asanyarray(image.dataobj)
    if not np.isfinite(values).all():
        raise ValueError("Mask contains non-finite values.")
    if not set(np.unique(values).tolist()).issubset({0, 1}):
        raise ValueError("GTV mask is not binary (expected only 0 and 1).")
    mask = values != 0
    voxel_cm3 = abs(determinant) / 1000.0
    geometry = {
        "shape_voxels": [int(value) for value in image.shape],
        "affine": [[float(value) for value in row] for row in image.affine],
        "axis_directions": [[float(value) for value in row] for row in (basis / axis_lengths[np.newaxis, :])],
        "voxel_spacing_mm": [float(value) for value in spacing],
        "unique_values": [value.item() if isinstance(value, np.generic) else value for value in np.unique(values)],
        "foreground_voxels": int(mask.sum()),
        "voxel_volume_cm3": float(voxel_cm3),
    }
    return mask, spacing, voxel_cm3, _sha256(path), geometry


def _volumes_at_radii(mask: np.ndarray, spacing: tuple[float, float, float], voxel_cm3: float):
    original_voxels = int(mask.sum())
    if original_voxels == 0:
        return {radius: {"erode": 0.0, "dilate": 0.0} for radius in RADII_MM}

    # Work on a padded lesion bounding box. The margin exceeds the largest
    # requested offset, so distances near the lesion are identical to those on
    # the full acquisition grid while avoiding repeated full-volume EDTs.
    coordinates = np.nonzero(mask)
    margin = np.ceil(max(RADII_MM) / np.asarray(spacing)).astype(int) + 2
    starts = [max(0, int(axis.min()) - int(pad)) for axis, pad in zip(coordinates, margin)]
    stops = [min(mask.shape[i], int(coordinates[i].max()) + int(margin[i]) + 1) for i in range(3)]
    crop_slices = tuple(slice(start, stop) for start, stop in zip(starts, stops))
    roi = mask[crop_slices]
    pad_width = tuple((int(pad), int(pad)) for pad in margin)
    padded = np.pad(roi, pad_width, mode="constant", constant_values=False)
    distance_inside = distance_transform_edt(padded, sampling=spacing)
    distance_outside = distance_transform_edt(~padded, sampling=spacing)
    roi_slices = tuple(slice(int(pad), int(pad) + size) for pad, size in zip(margin, roi.shape))
    distance_inside = distance_inside[roi_slices]
    distance_outside = distance_outside[roi_slices]
    result: dict[float, dict[str, float]] = {}
    for radius in RADII_MM:
        eroded_voxels = int(np.count_nonzero(roi & (distance_inside > radius)))
        dilated_voxels = original_voxels + int(np.count_nonzero((~roi) & (distance_outside <= radius)))
        result[radius] = {
            "erode": eroded_voxels * voxel_cm3,
            "dilate": dilated_voxels * voxel_cm3,
        }
    return result


def _bootstrap_interval(values: np.ndarray, seed: int, repetitions: int = 10_000):
    n = int(values.size)
    if n == 0:
        return None, None
    rng = np.random.default_rng(seed)
    sample_indices = rng.integers(0, n, size=(repetitions, n))
    bootstrap_rates = values[sample_indices].mean(axis=1)
    low, high = np.quantile(bootstrap_rates, [0.025, 0.975])
    return float(low), float(high)


def write_cfb_mask_manifest(metadata_dir: str | Path, out_file: str | Path) -> dict[str, Any]:
    """Write a local, patient-level list of unique GTV files required by labeled pairs."""
    metadata = Path(metadata_dir)
    rano_path = metadata / "CFB-GBM_rano_criteria_v04_20260909.tsv"
    availability_path = metadata / "CFB-GBM_treatment_imaging_availability_v03_20260619.tsv"
    if not rano_path.is_file() or not availability_path.is_file():
        raise FileNotFoundError("Expected official CFB-GBM Version 4 RANO and GTV availability TSV files.")

    mask_types = {
        (row["id_patient"], row["temporality"]): row.get("gtv_type", "")
        for row in _read_tsv(availability_path)
        if row.get("gtv") == "1"
    }
    masks: dict[tuple[str, str], set[str]] = defaultdict(set)
    candidate_pairs: Counter[str] = Counter()
    for pair_name, time_a, time_b, _vol_a, _vol_b, label_field in PAIR_FIELDS:
        for row in _read_tsv(rano_path):
            if not row.get(label_field, "").strip():
                continue
            patient_id = row["id_patient"]
            candidate_pairs[pair_name] += 1
            masks[(patient_id, time_a)].add(pair_name)
            masks[(patient_id, time_b)].add(pair_name)

    output = Path(out_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("patient_id", "timepoint", "relative_path", "mask_source", "pairs")
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for (patient_id, timepoint), pairs in sorted(
            masks.items(), key=lambda item: (int(item[0][0]), item[0][1])
        ):
            writer.writerow(
                {
                    "patient_id": patient_id,
                    "timepoint": timepoint,
                    "relative_path": f"{int(patient_id):03d}/{timepoint}/{patient_id}_{timepoint}_gtv.nii.gz",
                    "mask_source": mask_types.get((patient_id, timepoint), "missing"),
                    "pairs": ";".join(sorted(pairs)),
                }
            )
    return {
        "candidate_labeled_pairs": dict(candidate_pairs),
        "unique_required_masks": len(masks),
        "manifest": output.name,
        "patient_level": True,
    }


def run_cfb_robustness(
    metadata_dir: str | Path,
    imaging_root: str | Path,
    local_out: str | Path,
    aggregate_out: str | Path,
    qc_manifest_path: str | Path,
    qc_review_path: str | Path,
    seed: int = 20261011,
) -> dict[str, Any]:
    qc_summary = validate_cfb_qc_review(qc_manifest_path, qc_review_path)
    metadata = Path(metadata_dir)
    images = Path(imaging_root)
    local = Path(local_out)
    aggregate = Path(aggregate_out)
    local.mkdir(parents=True, exist_ok=True)
    aggregate.mkdir(parents=True, exist_ok=True)

    rano_path = metadata / "CFB-GBM_rano_criteria_v04_20260909.tsv"
    availability_path = metadata / "CFB-GBM_treatment_imaging_availability_v03_20260619.tsv"
    if not rano_path.is_file() or not availability_path.is_file():
        raise FileNotFoundError("Expected official CFB-GBM Version 4 RANO and GTV availability TSV files.")

    rano_rows = _read_tsv(rano_path)
    availability_rows = _read_tsv(availability_path)
    mask_types = {
        (row["id_patient"], row["temporality"]): row.get("gtv_type", "")
        for row in availability_rows if row.get("gtv") == "1"
    }

    patient_results: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []
    input_hashes: list[str] = []
    mask_qc: dict[str, dict[str, Any]] = {}
    mask_metrics: dict[str, dict[str, Any]] = {}
    for pair_name, time_a, time_b, vol_a, vol_b, label_field in PAIR_FIELDS:
        for source_row in rano_rows:
            published = source_row.get(label_field, "").strip()
            if not published:
                continue
            patient_id = source_row["id_patient"]
            paths = [
                images / f"{int(patient_id):03d}" / time_a / f"{patient_id}_{time_a}_gtv.nii.gz",
                images / f"{int(patient_id):03d}" / time_b / f"{patient_id}_{time_b}_gtv.nii.gz",
            ]
            if not all(path.is_file() for path in paths):
                exclusions.append({"patient_id": patient_id, "pair": pair_name, "reason": "missing_mask"})
                continue
            try:
                for path, timepoint in zip(paths, (time_a, time_b)):
                    key = str(path.resolve())
                    if key not in mask_metrics:
                        mask, spacing, voxel_volume, file_hash, geometry = _mask_geometry(path)
                        mask_metrics[key] = {
                            "spacing": spacing,
                            "voxel_volume": voxel_volume,
                            "sha256": file_hash,
                            "geometry": geometry,
                            "volume_cm3": float(mask.sum()) * voxel_volume,
                            "offset_volumes": _volumes_at_radii(mask, spacing, voxel_volume),
                        }
                        mask_qc[key] = {
                            "patient_id": patient_id,
                            "timepoint": timepoint,
                            "sha256": file_hash,
                            **geometry,
                        }
                base_metrics, follow_metrics = (mask_metrics[str(path.resolve())] for path in paths)
                base_spacing = base_metrics["spacing"]
                follow_spacing = follow_metrics["spacing"]
                base_metrics["voxel_volume"]
                follow_metrics["voxel_volume"]
                base_hash, follow_hash = base_metrics["sha256"], follow_metrics["sha256"]
                base_geometry, follow_geometry = base_metrics["geometry"], follow_metrics["geometry"]
                base_volume, follow_volume = base_metrics["volume_cm3"], follow_metrics["volume_cm3"]
                base_offsets, follow_offsets = base_metrics["offset_volumes"], follow_metrics["offset_volumes"]
                if not np.allclose(
                    np.asarray(base_geometry["axis_directions"]),
                    np.asarray(follow_geometry["axis_directions"]),
                    atol=1e-4,
                    rtol=0,
                ):
                    raise ValueError("Baseline and follow-up mask physical orientations are incompatible.")
                if base_volume <= 0:
                    raise ValueError("Baseline GTV mask is empty.")
                if follow_volume <= 0 and float(source_row[vol_b]) > 0:
                    raise ValueError("Follow-up GTV mask is empty but published volume is positive.")
                published_base = float(source_row[vol_a])
                published_follow = float(source_row[vol_b])
                if abs(base_volume - published_base) > 0.0051:
                    raise ValueError("Baseline mask volume differs from the rounded published volume.")
                if abs(follow_volume - published_follow) > 0.0051:
                    raise ValueError("Follow-up mask volume differs from the rounded published volume.")
                if _category(base_volume, follow_volume) != published:
                    raise ValueError("Unperturbed mask volumes do not reproduce the published category.")
                input_hashes.extend((base_hash, follow_hash))
                type_a = mask_types.get((patient_id, time_a), "missing")
                type_b = mask_types.get((patient_id, time_b), "missing")
                source_pair = f"{type_a or 'unspecified'} / {type_b or 'unspecified'}"
                for radius in RADII_MM:
                    independent_categories: list[str] = []
                    shared_categories: list[str] = []
                    non_evaluable = 0
                    for base_sign, follow_sign in (
                        ("dilate", "dilate"),
                        ("dilate", "erode"),
                        ("erode", "dilate"),
                        ("erode", "erode"),
                    ):
                        bvol = base_offsets[radius][base_sign]
                        fvol = follow_offsets[radius][follow_sign]
                        if bvol <= 0:
                            non_evaluable += 1
                            continue
                        independent_categories.append(_category(bvol, fvol))
                    for sign in ("dilate", "erode"):
                        bvol = base_offsets[radius][sign]
                        fvol = follow_offsets[radius][sign]
                        if bvol > 0:
                            shared_categories.append(_category(bvol, fvol))
                    independent_flips = sum(category != published for category in independent_categories)
                    shared_flips = sum(category != published for category in shared_categories)
                    patient_results.append(
                        {
                            "patient_id": patient_id,
                            "pair": pair_name,
                            "published_category": published,
                            "source_pair": source_pair,
                            "radius_mm": radius,
                            "independent_scenarios": len(independent_categories),
                            "independent_flip_scenarios": independent_flips,
                            "independent_categories": json.dumps(independent_categories, separators=(",", ":")),
                            "independent_any_flip": int(independent_flips > 0),
                            "shared_scenarios": len(shared_categories),
                            "shared_flip_scenarios": shared_flips,
                            "shared_categories": json.dumps(shared_categories, separators=(",", ":")),
                            "shared_any_flip": int(shared_flips > 0),
                            "non_evaluable_independent_scenarios": non_evaluable,
                            "baseline_cm3": base_volume,
                            "followup_cm3": follow_volume,
                            "baseline_spacing_mm": "x".join(f"{x:g}" for x in base_spacing),
                            "followup_spacing_mm": "x".join(f"{x:g}" for x in follow_spacing),
                        }
                    )
            except (OSError, ValueError, RuntimeError) as exc:
                exclusions.append(
                    {"patient_id": patient_id, "pair": pair_name, "reason": str(exc)}
                )

    if not patient_results:
        raise RuntimeError("No eligible CFB-GBM mask pairs were processed.")

    fields = list(patient_results[0])
    with (local / "patient_perturbations.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(patient_results)
    with (local / "exclusions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("patient_id", "pair", "reason"))
        writer.writeheader()
        writer.writerows(exclusions)
    (local / "mask_qc.json").write_text(
        json.dumps({"mask_count": len(mask_qc), "masks": mask_qc}, indent=2), encoding="utf-8"
    )

    summary_rows: list[dict[str, Any]] = []
    strata_rows: list[dict[str, Any]] = []
    defaultdict(Counter)
    n_non_evaluable = Counter()
    pair_names = [entry[0] for entry in PAIR_FIELDS]
    for pair_index, pair_name in enumerate(pair_names):
        for radius_index, radius in enumerate(RADII_MM):
            selected = [row for row in patient_results if row["pair"] == pair_name and row["radius_mm"] == radius]
            values = np.asarray([row["independent_any_flip"] for row in selected], dtype=np.float64)
            low, high = _bootstrap_interval(values, seed + pair_index * 100 + radius_index)
            scenario_count = sum(row["independent_scenarios"] for row in selected)
            scenario_flips = sum(row["independent_flip_scenarios"] for row in selected)
            non_eval = sum(row["non_evaluable_independent_scenarios"] for row in selected)
            n_non_evaluable[(pair_name, radius)] = non_eval
            summary_rows.append(
                {
                    "pair": pair_name,
                    "radius_mm": radius,
                    "n_pairs": len(selected),
                    "n_any_flip": int(values.sum()),
                    "any_flip_rate": float(values.mean()) if len(values) else None,
                    "ci95_low": low,
                    "ci95_high": high,
                    "n_flip_scenarios": scenario_flips,
                    "n_evaluable_scenarios": scenario_count,
                    "n_non_evaluable_scenarios": non_eval,
                    "scenario_flip_fraction": scenario_flips / scenario_count if scenario_count else None,
                    "shared_offset_any_flip_rate": float(np.mean([row["shared_any_flip"] for row in selected])) if selected else None,
                }
            )
            for source_pair in sorted({row["source_pair"] for row in selected}):
                group = [row for row in selected if row["source_pair"] == source_pair]
                group_values = np.asarray([row["independent_any_flip"] for row in group], dtype=np.float64)
                group_low, group_high = _bootstrap_interval(
                    group_values, seed + pair_index * 100 + radius_index * 10 + len(strata_rows)
                )
                strata_rows.append(
                    {
                        "pair": pair_name,
                        "radius_mm": radius,
                        "source_pair": source_pair,
                        "n_pairs": len(group),
                        "n_any_flip": int(group_values.sum()),
                        "any_flip_rate": float(group_values.mean()) if len(group_values) else None,
                        "ci95_low": group_low,
                        "ci95_high": group_high,
                    }
                )

    aggregate_fields = list(summary_rows[0])
    with (aggregate / "robustness_by_pair_radius.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=aggregate_fields)
        writer.writeheader()
        writer.writerows(summary_rows)
    with (aggregate / "robustness_by_mask_source.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(strata_rows[0]) if strata_rows else [])
        writer.writeheader()
        writer.writerows(strata_rows)

    transition_rows: list[dict[str, Any]] = []
    for pair_name in pair_names:
        selected = [row for row in patient_results if row["pair"] == pair_name and row["radius_mm"] == 1.0]
        scenario_counts: Counter[tuple[str, str]] = Counter()
        pair_presence: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in selected:
            for category in json.loads(row["independent_categories"]):
                scenario_counts[(row["published_category"], category)] += 1
                pair_presence[(row["published_category"], category)].add(row["patient_id"])
        for original in CATEGORIES:
            for perturbed in CATEGORIES:
                transition_rows.append(
                    {
                        "pair": pair_name,
                        "published_category": original,
                        "perturbed_category": perturbed,
                        "n_pair_scenarios": scenario_counts[(original, perturbed)],
                        "n_pairs_with_transition": len(pair_presence[(original, perturbed)]),
                    }
                )

    with (aggregate / "category_transitions_1mm.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(transition_rows[0]))
        writer.writeheader()
        writer.writerows(transition_rows)
    counts_excluded = Counter(row["reason"] for row in exclusions)
    mask_hash_digest = hashlib.sha256("\n".join(sorted(input_hashes)).encode("utf-8")).hexdigest()
    public_summary = {
        "study": "CFB-GBM geometric RANO category robustness",
        "primary_interval": "t0_to_t1",
        "primary_radius_mm": 1.0,
        "seed": seed,
        "bootstrap_repetitions": 10_000,
        "pre_outcome_image_qc": qc_summary,
        "radii_mm": list(RADII_MM),
        "candidate_labeled_pairs": {
            "t0_to_t1": 160,
            "t0_to_t2": 112,
            "t1_to_t2": 107,
        },
        "processed_pairs_by_interval": {
            pair: len([row for row in patient_results if row["pair"] == pair and row["radius_mm"] == 1.0])
            for pair in pair_names
        },
        "exclusions_by_reason": dict(counts_excluded),
        "mask_input_digest_sha256": mask_hash_digest,
        "source_input_sha256": {
            rano_path.name: _sha256(rano_path),
            availability_path.name: _sha256(availability_path),
        },
        "software": {
            "tumorlens": __version__,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "nibabel": nib.__version__,
        },
        "aggregate_outputs": [
            "robustness_by_pair_radius.csv",
            "robustness_by_mask_source.csv",
            "category_transitions_1mm.csv",
        ],
        "claim_boundary": (
            "Published pairwise volumetric RANO categories are derived from the same GTV volumes. "
            "Results estimate sensitivity of those categories to controlled voxel-centre boundary "
            "offsets; they do not estimate independent expert agreement, diagnostic accuracy, or "
            "clinical prediction performance."
        ),
    }
    (aggregate / "summary.json").write_text(json.dumps(public_summary, indent=2), encoding="utf-8")


    return public_summary



