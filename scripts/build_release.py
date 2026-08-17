#!/usr/bin/env python3
"""Package the verified interactive dataviz and supporting evidence."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "README.md",
    "src/index.html",
    "src/styles.css",
    "src/app.js",
    "src/data.js",
    "data/pacific_climate_transition.csv",
    "data/data_dictionary.md",
    "data/snapshot_metadata.json",
    "scripts/fetch_official_data.py",
    "scripts/build_static_fallback.py",
    "scripts/build_release.py",
    "scripts/run_pipeline.py",
    "scripts/verify_submission.py",
    "scripts/runtime_smoke_test.js",
    "scripts/fetch_validation_smoke_test.py",
    "scripts/verification_adversarial_smoke_test.py",
    "submission/problem-statement.md",
    "submission/ai-disclosure.md",
    "submission/checklist.md",
    "submission/README.md",
    "submission/build-environment.txt",
    "submission/fallback.html",
    "submission/fallback.pdf",
    "submission/fallback.png",
]
MANIFEST = "submission/release-manifest.sha256"


def source_file(relative: str) -> Path:
    if ROOT.is_symlink() or not ROOT.is_dir():
        raise ValueError("release root must be a real directory")
    current = ROOT
    for part in Path(relative).parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"release source must not be a symlink: {relative}")
    if not current.is_file():
        raise FileNotFoundError(relative)
    return current


def fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest() -> str:
    lines = [f"{sha256(source_file(relative))}  {relative}" for relative in FILES]
    return "\n".join(lines) + "\n"


def main() -> None:
    output = ROOT / "submission/pacific-dataviz-2026-release.zip"
    if output.parent.is_symlink() or not output.parent.is_dir() or output.is_symlink():
        raise ValueError("release output must remain inside a real submission directory")
    manifest = build_manifest()
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=f".{output.name}.", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with temporary.open("w+b") as handle:
            with ZipFile(handle, "w", ZIP_DEFLATED) as archive:
                for relative in FILES:
                    path = source_file(relative)
                    archive.write(path, Path("pacific-dataviz-2026") / relative)
                archive.writestr(str(Path("pacific-dataviz-2026") / MANIFEST), manifest)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
        fsync_directory(output.parent)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"wrote {output.name} with {len(FILES) + 1} files and embedded SHA-256 manifest ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
