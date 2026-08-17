#!/usr/bin/env python3
"""Exercise verifier boundaries without touching the project artifacts."""

from __future__ import annotations

import sys
import stat
import tempfile
from zipfile import ZipInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_submission as verify  # noqa: E402


def main() -> None:
    symlink_info = ZipInfo("symlink")
    symlink_info.create_system = 3
    symlink_info.external_attr = stat.S_IFLNK << 16
    regular_info = ZipInfo("regular")
    regular_info.create_system = 3
    regular_info.external_attr = 0o100644 << 16
    assert stat.S_ISLNK(symlink_info.external_attr >> 16)
    assert not stat.S_ISLNK(regular_info.external_attr >> 16)

    original_root = verify.ROOT
    try:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            data = root / "data"
            data.mkdir(parents=True)
            verify.ROOT = root
            header = ",".join(verify.EXPECTED_DATA_COLUMNS)
            (data / "pacific_climate_transition.csv").write_text(
                f"{header}\nFJ,Fiji,1990,1,,0,unexpected\n",
                encoding="utf-8",
            )
            ok, message = verify.check_data()
            assert not ok and "malformed row" in message
            (data / "pacific_climate_transition.csv").write_text(
                f"{header}\nFJ,Fiji,not-a-year,1,1,1\n",
                encoding="utf-8",
            )
            ok, message = verify.check_data()
            assert not ok and "invalid country or year value" in message

            outside = base / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            (root / "README.md").symlink_to(outside)
            try:
                verify.project_file("README.md")
            except ValueError:
                pass
            else:
                raise AssertionError("external symlink was accepted")
    finally:
        verify.ROOT = original_root

    print("verifier adversarial smoke: malformed rows and symlink escapes are rejected")


if __name__ == "__main__":
    main()
