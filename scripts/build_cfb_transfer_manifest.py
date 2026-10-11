"""Build the local, patient-level CFB-GBM selective-transfer manifest."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASKS = ROOT / "results" / "cfb_gbm_robustness" / "required_masks.csv"
QC_IMAGES = ROOT / "results" / "cfb_gbm_robustness" / "required_qc_images.csv"
OUTPUT = ROOT / "results" / "cfb_gbm_robustness" / "selected_transfer_manifest.csv"
FIELDS = (
    "relative_path",
    "asset_type",
    "patient_id",
    "timepoint",
    "mask_source",
    "pairs",
    "purpose",
)


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
        return list(reader)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()

    masks = read_csv(MASKS, {"relative_path", "patient_id", "timepoint", "mask_source", "pairs"})
    qc_images = read_csv(QC_IMAGES, {"relative_path", "patient_id", "timepoint", "purpose"})

    records: list[dict[str, str]] = []
    records.extend(
        {
            "relative_path": row["relative_path"],
            "asset_type": "gtv_mask",
            "patient_id": row["patient_id"],
            "timepoint": row["timepoint"],
            "mask_source": row["mask_source"],
            "pairs": row["pairs"],
            "purpose": "boundary_robustness",
        }
        for row in masks
    )
    records.extend(
        {
            "relative_path": row["relative_path"],
            "asset_type": "t1gd_qc_image",
            "patient_id": row["patient_id"],
            "timepoint": row["timepoint"],
            "mask_source": "",
            "pairs": "",
            "purpose": row["purpose"],
        }
        for row in qc_images
    )

    paths = [row["relative_path"] for row in records]
    if len(paths) != len(set(paths)):
        raise ValueError("The transfer manifest contains duplicate relative paths.")
    if any(not path or Path(path).is_absolute() or ".." in Path(path).parts for path in paths):
        raise ValueError("Every transfer path must be a safe, non-empty relative path.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(records, key=lambda row: (row["relative_path"].casefold(), row["asset_type"])))

    print(f"Masks: {len(masks)}; QC images: {len(qc_images)}; unique paths: {len(paths)}")
    print(f"Local manifest: {args.out}")


if __name__ == "__main__":
    main()
