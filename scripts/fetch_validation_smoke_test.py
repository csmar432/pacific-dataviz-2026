#!/usr/bin/env python3
"""Exercise the fetcher's fail-closed CSV boundary without network access."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_official_data as fetch  # noqa: E402


class Response:
    def __init__(self, body: str, content_type: str = "text/csv; charset=utf-8", url: str = "https://example.test/data") -> None:
        self.body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        self.url = url

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self.body

    def geturl(self) -> str:
        return self.url


def body_for(columns: list[str], values: list[str]) -> str:
    return ",".join(columns) + "\n" + ",".join(values) + "\n"


def valid_row(dataset: str, code: str = "FJ", year: int = 1990) -> dict[str, str]:
    row = {column: "" for column in fetch.EXPECTED_COLUMNS[dataset]}
    row.update(fetch.DATASET_SPECS[dataset]["identity"])
    row.update({"GEO_PICT": code, "TIME_PERIOD": str(year), "OBS_VALUE": "1"})
    return row


def assert_identity_rejected(field: str, value: str) -> None:
    row = valid_row("ghg")
    row[field] = value
    with patch.object(fetch, "get_csv", return_value=[row]):
        try:
            fetch.query("ghg", "FJ", 1990, 1990)
        except ValueError as exc:
            assert field in str(exc)
        else:
            raise AssertionError(f"wrong {field} was accepted")


def main() -> None:
    columns = sorted(fetch.EXPECTED_COLUMNS["ghg"])
    values = ["1990" if column == "TIME_PERIOD" else "1" if column == "OBS_VALUE" else "" for column in columns]
    valid = body_for(columns, values)
    with patch.object(fetch, "urlopen", return_value=Response(valid)):
        assert len(fetch.get_csv("https://example.test/data", fetch.EXPECTED_COLUMNS["ghg"])) == 1

    with patch.object(fetch, "urlopen", return_value=Response(body_for(columns, values[:-1]))):
        try:
            fetch.get_csv("https://example.test/truncated", fetch.EXPECTED_COLUMNS["ghg"])
        except ValueError as exc:
            assert "malformed CSV row" in str(exc)
        else:
            raise AssertionError("truncated CSV row was accepted")

    with patch.object(fetch, "urlopen", return_value=Response(valid, "text/html")):
        try:
            fetch.get_csv("https://example.test/html", fetch.EXPECTED_COLUMNS["ghg"])
        except ValueError as exc:
            assert "content type" in str(exc)
        else:
            raise AssertionError("HTML response was accepted")

    with patch.object(fetch, "urlopen", return_value=Response(valid, "text/csvx")):
        try:
            fetch.get_csv("https://example.test/csvx", fetch.EXPECTED_COLUMNS["ghg"])
        except ValueError as exc:
            assert "content type" in str(exc)
        else:
            raise AssertionError("CSVX response was accepted")

    with patch.object(fetch, "urlopen", return_value=Response(valid, url="https://redirected.test/data")):
        try:
            fetch.get_csv("https://example.test/data", fetch.EXPECTED_COLUMNS["ghg"])
        except ValueError as exc:
            assert "different origin" in str(exc)
        else:
            raise AssertionError("cross-origin API redirect was accepted")

    duplicate_header = body_for(columns + [columns[0]], values + [""])
    with patch.object(fetch, "urlopen", return_value=Response(duplicate_header)):
        try:
            fetch.get_csv("https://example.test/duplicate", fetch.EXPECTED_COLUMNS["ghg"])
        except ValueError as exc:
            assert "duplicate CSV columns" in str(exc)
        else:
            raise AssertionError("duplicate CSV columns were accepted")

    for dataset in fetch.DATASET_SPECS:
        with patch.object(fetch, "get_csv", return_value=[valid_row(dataset)]):
            assert len(fetch.query(dataset, "FJ", 1990, 1990)) == 1

    with patch.object(fetch, "get_csv", return_value=[valid_row("ghg")]):
        try:
            fetch.query("ghg", "FJ", 1990, 1991)
        except ValueError as exc:
            assert "incomplete TIME_PERIOD coverage" in str(exc)
        else:
            raise AssertionError("incomplete indicator coverage was accepted")

    assert_identity_rejected("GEO_PICT", "WS")
    assert_identity_rejected("CLIMATE_CHANGE_INDICATORS", "SST_ANOM")
    assert_identity_rejected("DATAFLOW", "SPC:DF_OTHER(1.0)")
    assert_identity_rejected("UNIT_MEASURE", "PERCENT")
    assert_identity_rejected("FREQ", "Q")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        first = root / "data/first.txt"
        second = root / "src/second.txt"
        metadata = root / "data/snapshot_metadata.json"
        for target in [first, second, metadata]:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("old", encoding="utf-8")
        real_replace = fetch.os.replace
        calls = 0

        def fail_second_replace(source: Path, target: Path) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated publish failure")
            real_replace(source, target)

        with patch.object(fetch.os, "replace", side_effect=fail_second_replace):
            try:
                fetch.write_transaction(root, {first: "new", second: "new", metadata: "new"})
            except OSError:
                pass
            else:
                raise AssertionError("simulated transaction failure was accepted")
        assert all(target.read_text(encoding="utf-8") == "old" for target in [first, second, metadata])

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        first = root / "data/first.txt"
        metadata = root / "data/snapshot_metadata.json"
        for target in [first, metadata]:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("old", encoding="utf-8")
        real_fsync_directory = fetch.fsync_directory
        calls = 0

        def fail_after_publish(path: Path) -> None:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("simulated directory fsync failure")
            real_fsync_directory(path)

        with patch.object(fetch, "fsync_directory", side_effect=fail_after_publish):
            try:
                fetch.write_transaction(root, {first: "new", metadata: "new"})
            except OSError:
                pass
            else:
                raise AssertionError("post-replace fsync failure was accepted")
        assert first.read_text(encoding="utf-8") == "old"
        assert metadata.read_text(encoding="utf-8") == "old"

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        root = base / "project"
        outside = base / "outside"
        root.mkdir()
        outside.mkdir()
        (root / "data").symlink_to(outside, target_is_directory=True)
        try:
            fetch.write_transaction(root, {root / "data/escaped.txt": "must not write"})
        except ValueError as exc:
            assert "symlink" in str(exc)
        else:
            raise AssertionError("symlink transaction parent was accepted")

    print("fetch validation smoke: malformed CSV, redirects, incomplete identities/coverage and partial publication are rejected")


if __name__ == "__main__":
    main()
