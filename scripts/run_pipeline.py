#!/usr/bin/env python3
"""Refresh, build, package and verify the complete local submission."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    "fetch_official_data.py",
    "build_static_fallback.py",
    "build_release.py",
    "verify_submission.py",
]
CACHE_DIR = ROOT / "scripts/__pycache__"


def main() -> int:
    shutil.rmtree(CACHE_DIR, ignore_errors=True)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        for script in STEPS:
            print(f"\n==> {script}")
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / script)], cwd=ROOT, env=env)
            if result.returncode:
                return result.returncode
    finally:
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
    print("\nPipeline complete: local package refreshed, packaged and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
