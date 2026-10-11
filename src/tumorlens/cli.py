from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import pandas as pd

from . import __version__
from .cfb_gbm import audit_cfb_metadata, write_cfb_metadata_audit
from .cfb_qc import build_cfb_qc_gallery
from .cfb_robustness import run_cfb_robustness, write_cfb_mask_manifest
from .imaging import audit_imaging, write_imaging_audit
from .lumiere import audit_lumiere, write_audit
from .response import bidimensional_threshold_call
from .selective import make_analysis_frame, risk_coverage


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _audit(args: argparse.Namespace) -> int:
    summary, review, unmatched_visit_keys, imaging_key_mismatches, rating_image_unmatched, rating_key_collisions = audit_lumiere(
        args.ratings,
        args.completeness,
        args.imaging_root,
    )
    summary["software"] = {"tumorlens": __version__, "python": platform.python_version(), "platform": platform.platform()}
    summary["input_hashes_sha256"] = {str(Path(p).name): _sha256(Path(p)) for p in [args.ratings, args.completeness] if p}
    write_audit(
        summary,
        review,
        args.out,
        unmatched_visit_keys if args.completeness else None,
        imaging_key_mismatches if args.imaging_root else None,
        rating_image_unmatched if args.imaging_root else None,
        rating_key_collisions,
    )
    print(json.dumps(summary, indent=2))
    print(f"\nWrote audit outputs to: {Path(args.out).resolve()}")
    return 0



def _cfb_metadata_audit(args: argparse.Namespace) -> int:
    summary = audit_cfb_metadata(args.input_dir)
    write_cfb_metadata_audit(summary, args.out)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote aggregate CFB-GBM metadata outputs to: {Path(args.out).resolve()}")
    return 0

def _cfb_robustness(args: argparse.Namespace) -> int:
    summary = run_cfb_robustness(
        metadata_dir=args.metadata_dir,
        imaging_root=args.imaging_root,
        local_out=args.local_out,
        aggregate_out=args.aggregate_out,
        qc_manifest_path=args.qc_manifest,
        qc_review_path=args.qc_review,
        seed=args.seed,
    )
    print(json.dumps(summary, indent=2))
    print(f"\nWrote patient-level local outputs to: {Path(args.local_out).resolve()}")
    print(f"Wrote aggregate-only outputs to: {Path(args.aggregate_out).resolve()}")
    return 0


def _cfb_qc_overlays(args: argparse.Namespace) -> int:
    summary = build_cfb_qc_gallery(
        qc_manifest_path=args.qc_manifest,
        mask_manifest_path=args.mask_manifest,
        imaging_root=args.imaging_root,
        out_dir=args.out,
    )
    print(json.dumps(summary, indent=2))
    print(f"\nWrote prespecified QC gallery to: {Path(args.out).resolve()}")
    return 0


def _cfb_mask_manifest(args: argparse.Namespace) -> int:
    summary = write_cfb_mask_manifest(args.metadata_dir, args.out)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote local patient-level mask manifest to: {Path(args.out).resolve()}")
    return 0


def _analyze(args: argparse.Namespace) -> int:
    source = Path(args.manifest)
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    analysis = make_analysis_frame(frame)
    curve = risk_coverage(
        analysis,
        bootstrap_reps=args.bootstrap_reps,
        seed=args.seed,
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    curve.to_csv(out / "risk_coverage.csv", index=False)
    contrasts = curve.attrs.get("paired_contrasts", [])
    if contrasts:
        pd.DataFrame.from_records(contrasts).to_csv(out / "risk_coverage_contrasts.csv", index=False)
    summary = {
        "status": "analysis_output_not_interpreted",
        "manifest": source.name,
        "manifest_sha256": _sha256(source),
        "n_rows_analysis": len(analysis),
        "n_patients": int(analysis.patient_id.nunique()),
        "n_expert_discordant": int(analysis.expert_discordant.sum()),
        "discordance_fraction": float(analysis.expert_discordant.mean()) if len(analysis) else None,
        "bootstrap_reps": args.bootstrap_reps,
        "seed": args.seed,
        "caution": "Discordance is relative to the available expert rating, not established diagnostic error or clinical harm. Review the frozen cohort and protocol before interpreting results.",
        "contrast_file": "risk_coverage_contrasts.csv" if contrasts else None,
    }
    (out / "analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nWrote analysis outputs to: {out.resolve()}")
    return 0


def _rano(args: argparse.Namespace) -> int:
    result = bidimensional_threshold_call(
        baseline_spd_mm2=args.baseline,
        nadir_spd_mm2=args.nadir,
        current_spd_mm2=args.current,
        measurable=not args.not_measurable,
        new_lesion=args.new_lesion,
        rule_set=args.rule_set,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


def _imaging_audit(args: argparse.Namespace) -> int:
    summary, records = audit_imaging(args.imaging_root)
    write_imaging_audit(summary, records, args.out)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote imaging audit outputs to: {Path(args.out).resolve()}")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tumorlens", description="Research utilities for longitudinal response-measurement deferral.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("lumiere-audit", help="Summarize LUMIERE ratings and produce a human-review rationale queue.")
    p.add_argument("--ratings", required=True)
    p.add_argument("--completeness")
    p.add_argument("--imaging-root", help="Optional local image-folder tree for exact visit-key comparison.")
    p.add_argument("--out", required=True)
    p.set_defaults(run=_audit)
    p = sub.add_parser("imaging-audit", help="Inventory native LUMIERE masks and calculate method-specific enhancing volumes.")
    p.add_argument("--imaging-root", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(run=_imaging_audit)
    p = sub.add_parser("cfb-metadata-audit", help="Reproduce aggregate CFB-GBM Version 4 RANO labels from metadata.")
    p.add_argument("--input-dir", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(run=_cfb_metadata_audit)
    p = sub.add_parser("cfb-robustness", help="Run patient-level CFB-GBM mask boundary perturbation analysis.")
    p.add_argument("--metadata-dir", required=True)
    p.add_argument("--imaging-root", required=True)
    p.add_argument("--local-out", required=True, help="Patient-level results location; keep local and out of shared archives.")
    p.add_argument("--aggregate-out", required=True, help="Aggregate-only results location suitable for the project package.")
    p.add_argument("--qc-manifest", required=True, help="Locked outcome-independent T1-Gd QC sample manifest.")
    p.add_argument("--qc-review", required=True, help="Completed local review CSV from cfb-qc-overlays.")
    p.add_argument("--seed", type=int, default=20261011)
    p.set_defaults(run=_cfb_robustness)
    p = sub.add_parser("cfb-qc-overlays", help="Render locked pre-outcome T1-Gd/GTV QC overlays and a review template.")
    p.add_argument("--qc-manifest", required=True)
    p.add_argument("--mask-manifest", required=True)
    p.add_argument("--imaging-root", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(run=_cfb_qc_overlays)
    p = sub.add_parser("cfb-mask-manifest", help="List unique GTV masks required by labeled CFB-GBM pairs.")
    p.add_argument("--metadata-dir", required=True)
    p.add_argument("--out", required=True, help="Local patient-level manifest; keep out of shared archives.")
    p.set_defaults(run=_cfb_mask_manifest)
    p = sub.add_parser("analyze", help="Patient-clustered selective-risk analysis from a curated manifest.")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bootstrap-reps", type=int, default=1000)
    p.add_argument("--seed", type=int, default=20261011)
    p.set_defaults(run=_analyze)
    p = sub.add_parser("threshold", help="Calculate a transparent bidimensional threshold-only result.")
    p.add_argument("--baseline", type=float)
    p.add_argument("--nadir", type=float)
    p.add_argument("--current", type=float)
    p.add_argument("--not-measurable", action="store_true")
    p.add_argument("--new-lesion", action="store_true")
    p.add_argument("--rule-set", default="rano_2_0_radiographic_thresholds")
    p.set_defaults(run=_rano)
    args = parser.parse_args(argv)
    try:
        sys.exit(args.run(args))
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        parser.exit(2, f"tumorlens: error: {exc}\n")



