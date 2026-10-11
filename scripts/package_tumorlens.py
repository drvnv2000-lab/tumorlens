from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    ".gitignore",
    "CITATION.cff",
    "LICENSE",
    "README.md",
    "PHASE0.md",
    "PREREGISTRATION.md",
    "pyproject.toml",
    "requirements-lock.txt",
    "PACKAGE_STATUS.md",
)
ROOT_DIRS = (
    ".github",
    "docs",
    "examples",
    "prototype-import",
    "schema",
    "scripts",
    "src",
    "tests",
    "viewer",
    "data/curated",
)
EXCLUDED_DIRS = {
    ".git", ".venv", ".vendor", "__pycache__", ".pytest_cache", ".ruff_cache", ".egg-info",
    ".mypy_cache", "results", "raw", "dist", "build", "node_modules",
}
EXCLUDED_SUFFIXES = {
    ".nii", ".gz", ".dcm", ".tcia", ".parquet", ".pkl", ".pickle", ".pyc",
    ".sqlite", ".db", ".log", ".npy",
}
EXCLUDED_NAMES = {
    "required_masks.csv", "required_qc_images.csv", "selected_transfer_manifest.csv",
    "patient_perturbations.csv", "mask_qc.json", "exclusions.csv",
}
PATIENT_OUTPUT_NAME = re.compile(r"^(patient|subject)[-_].*\.(csv|tsv|json|parquet)$", re.IGNORECASE)


def _safe_file(path: Path, rel: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    if any(part.lower() in EXCLUDED_DIRS or part.lower().endswith(".egg-info") for part in rel.parts[:-1]):
        return False
    if path.name.lower() in EXCLUDED_NAMES or PATIENT_OUTPUT_NAME.match(path.name):
        return False
    return not any(path.name.lower().endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def iter_package_files() -> list[tuple[Path, str]]:
    candidates: set[Path] = {ROOT / name for name in ROOT_FILES}
    for dirname in ROOT_DIRS:
        base = ROOT / dirname
        if not base.exists():
            continue
        for current, dirnames, filenames in os.walk(base, followlinks=False):
            current_path = Path(current)
            dirnames[:] = [
                name for name in dirnames
                if (
                    name.lower() not in EXCLUDED_DIRS
                    and not name.lower().endswith(".egg-info")
                    and not (current_path / name).is_symlink()
                )
            ]
            for filename in filenames:
                candidates.add(current_path / filename)
    selected: list[tuple[Path, str]] = []
    for path in candidates:
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            continue
        if _safe_file(path, rel):
            selected.append((path, rel.as_posix()))
    return sorted(selected, key=lambda item: item[1].casefold())


def build_archive(output: Path) -> dict[str, object]:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = iter_package_files()
    hashes = []
    for path, name in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.append(f"{digest}  {name}")
    manifest = ("\n".join(hashes) + "\n").encode("utf-8")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in files:
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("PACKAGE_MANIFEST.sha256", date_time=(2020, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(info, manifest)
    size = output.stat().st_size
    return {"archive": str(output), "included_files": len(files) + 1, "archive_bytes": size}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a TumorLens source package without raw or patient-level data.")
    parser.add_argument("--out", default="dist/TumorLens-portfolio.zip")
    args = parser.parse_args()
    output = Path(args.out)
    if not output.is_absolute():
        output = ROOT / output
    output = output.resolve()
    allowed = (ROOT / "dist").resolve()
    if not output.is_relative_to(allowed):
        parser.error("--out must point inside the project dist/ folder.")
    result = build_archive(output)
    print(f"Created {result['archive']} ({result['included_files']} files, {result['archive_bytes']} bytes)")


if __name__ == "__main__":
    main()
