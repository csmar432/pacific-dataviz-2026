#!/usr/bin/env python3
"""Fetch the three official indicators used by the Pacific Dataviz MVP.

The page ships with a local snapshot so it works without a live API request.
Run this script again when refreshing the snapshot before submission.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


API_ROOT = "https://stats-nsi-stable.pacificdata.org/rest/data"
COUNTRIES = {
    "FJ": "Fiji",
    "KI": "Kiribati",
    "WS": "Samoa",
    "SB": "Solomon Islands",
    "TO": "Tonga",
    "TV": "Tuvalu",
    "VU": "Vanuatu",
}
MAX_RESPONSE_BYTES = 4_000_000
MISSING_VALUES = {"", "NA", "N/A", "NULL", "NONE", "..", "-"}
RANGES = {
    "ghg_tonnes_per_capita": (0, 100),
    "sst_anomaly_celsius": (-10, 10),
    "renewable_share_percent": (0, 100),
}
EXPECTED_COLUMNS = {
    "ghg": {"CLIMATE_CHANGE_INDICATORS", "DATAFLOW", "ERROR_TYPE", "ERROR_VAL", "FREQ", "GEO_PICT", "OBS_COMMENT", "OBS_STATUS", "OBS_VALUE", "REPORTING_TYPE", "TIME_PERIOD", "UNIT_MEASURE"},
    "sst": {"CLIMATE_CHANGE_INDICATORS", "DATAFLOW", "ERROR_TYPE", "ERROR_VAL", "FREQ", "GEO_PICT", "OBS_COMMENT", "OBS_STATUS", "OBS_VALUE", "REPORTING_TYPE", "TIME_PERIOD", "UNIT_MEASURE"},
    "renewable": {"AGE", "COMPOSITE_BREAKDOWN", "DATAFLOW", "DATA_SOURCE", "DISABILITY", "EDUCATION", "FREQ", "GEO_PICT", "INCOME", "INDICATOR", "NATURE", "OBS_COMMENT", "OBS_STATUS", "OBS_VALUE", "OCCUPATION", "REPORTING_TYPE", "SEX", "TIME_PERIOD", "UNIT_MEASURE", "URBANIZATION"},
}
DATASET_SPECS = {
    "ghg": {
        "flow": "SPC,DF_CLIMATE_CHANGE,1.0",
        "key": "A.GHG_EMI_CAPITA.{code}",
        "identity": {
            "DATAFLOW": "SPC:DF_CLIMATE_CHANGE(1.0)",
            "FREQ": "A",
            "CLIMATE_CHANGE_INDICATORS": "GHG_EMI_CAPITA",
            "UNIT_MEASURE": "TON",
        },
    },
    "sst": {
        "flow": "SPC,DF_CLIMATE_CHANGE,1.0",
        "key": "A.SST_ANOM.{code}",
        "identity": {
            "DATAFLOW": "SPC:DF_CLIMATE_CHANGE(1.0)",
            "FREQ": "A",
            "CLIMATE_CHANGE_INDICATORS": "SST_ANOM",
            "UNIT_MEASURE": "CELSIUS",
        },
    },
    "renewable": {
        "flow": "SPC,DF_SDG,3.0",
        "key": "A.EG_FEC_RNEW.{code}._T._T._T._T._T._T._Z._T",
        "identity": {
            "DATAFLOW": "SPC:DF_SDG(3.0)",
            "FREQ": "A",
            "INDICATOR": "EG_FEC_RNEW",
            "UNIT_MEASURE": "PERCENT",
            "SEX": "_T",
            "AGE": "_T",
            "URBANIZATION": "_T",
            "INCOME": "_T",
            "EDUCATION": "_T",
            "OCCUPATION": "_T",
            "COMPOSITE_BREAKDOWN": "_Z",
            "DISABILITY": "_T",
        },
    },
}


def get_csv(url: str, expected_columns: set[str]) -> list[dict[str, str]]:
    for attempt in range(3):
        try:
            request = Request(url, headers={"Accept": "text/csv", "User-Agent": "PacificDatavizMVP/1.0"})
            with urlopen(request, timeout=30) as response:
                requested = urlsplit(url)
                final = urlsplit(response.geturl())
                if (final.scheme, final.netloc) != (requested.scheme, requested.netloc):
                    raise ValueError(f"API redirected to a different origin: {response.geturl()}")
                content_type = (response.headers.get("Content-Type") or "").lower()
                media_type, *parameters = [part.strip() for part in content_type.split(";")]
                accepted_media_types = {"text/csv", "application/vnd.sdmx.data+csv"}
                if media_type not in accepted_media_types:
                    raise ValueError(f"unexpected API content type: {content_type}")
                for parameter in parameters:
                    if "=" not in parameter:
                        raise ValueError(f"malformed API content type parameter: {parameter}")
                    name, value = (part.strip().lower() for part in parameter.split("=", 1))
                    if name not in {"charset", "version"} or not value:
                        raise ValueError(f"unsupported API content type parameter: {parameter}")
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError(f"API response exceeds {MAX_RESPONSE_BYTES} bytes")
            reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
            fieldnames = reader.fieldnames or []
            if len(fieldnames) != len(set(fieldnames)):
                raise ValueError("API response contains duplicate CSV columns")
            rows = list(reader)
            if not rows:
                raise ValueError("API response contains no observations")
            fieldnames = set(rows[0])
            if fieldnames != expected_columns:
                got = sorted("<extra>" if column is None else column for column in fieldnames)
                raise ValueError(f"unexpected API schema: expected {sorted(expected_columns)}, got {got}")
            if any(None in row or any(value is None for value in row.values()) or any(key not in row for key in expected_columns) for row in rows):
                raise ValueError("API response contains a malformed CSV row")
            return rows
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.75)
    raise RuntimeError("unreachable")


def parse_observation(value: str | None) -> float | None:
    cleaned = (value or "").strip()
    if cleaned.upper() in MISSING_VALUES:
        return None
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"non-numeric OBS_VALUE: {value!r}") from exc


def add_observations(
    observations: dict[tuple[str, int], dict[str, object]],
    code: str,
    country: str,
    rows: list[dict[str, str]],
    field: str,
) -> None:
    lower, upper = RANGES[field]
    for row in rows:
        try:
            year = int(row["TIME_PERIOD"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid TIME_PERIOD in {field}: {row!r}") from exc
        value = parse_observation(row.get("OBS_VALUE"))
        if value is not None and not lower <= value <= upper:
            raise ValueError(f"{field} value outside expected range: {value}")
        record = observations.setdefault((code, year), {"country_code": code, "country": country, "year": year})
        record[field] = value


def query(dataset: str, code: str, start: int, end: int) -> list[dict[str, str]]:
    spec = DATASET_SPECS[dataset]
    flow = spec["flow"]
    key = spec["key"].format(code=code)
    params = urlencode(
        {
            "startPeriod": start,
            "endPeriod": end,
            "dimensionAtObservation": "AllDimensions",
        }
    )
    rows = get_csv(f"{API_ROOT}/{flow}/{key}?{params}", EXPECTED_COLUMNS[dataset])
    seen_years: set[int] = set()
    for row in rows:
        expected_identity = {**spec["identity"], "GEO_PICT": code}
        for field, expected in expected_identity.items():
            if row.get(field) != expected:
                raise ValueError(
                    f"unexpected {field} in {dataset}/{code}: expected {expected!r}, got {row.get(field)!r}"
                )
        try:
            year = int(row["TIME_PERIOD"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid TIME_PERIOD in {dataset}/{code}: {row!r}") from exc
        if not start <= year <= end:
            raise ValueError(f"TIME_PERIOD outside requested range in {dataset}/{code}: {year}")
        if year in seen_years:
            raise ValueError(f"duplicate TIME_PERIOD in {dataset}/{code}: {year}")
        seen_years.add(year)
    expected_years = set(range(start, end + 1))
    if seen_years != expected_years:
        missing = sorted(expected_years - seen_years)
        raise ValueError(f"incomplete TIME_PERIOD coverage in {dataset}/{code}: missing {missing}")
    return rows


def build_snapshot() -> list[dict[str, object]]:
    observations: dict[tuple[str, int], dict[str, object]] = {}
    for code, country in COUNTRIES.items():
        add_observations(observations, code, country, query("ghg", code, 1990, 2024), "ghg_tonnes_per_capita")
        add_observations(observations, code, country, query("sst", code, 1990, 2024), "sst_anomaly_celsius")
        add_observations(observations, code, country, query("renewable", code, 2010, 2022), "renewable_share_percent")
    return sorted(observations.values(), key=lambda row: (row["country_code"], row["year"]))


def fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_transaction_target(root: Path, target: Path) -> None:
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"transaction target escapes root: {target}") from exc
    if not relative.parts or ".." in relative.parts:
        raise ValueError(f"transaction target escapes root: {target}")
    current = root
    for part in relative.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise ValueError(f"transaction parent must not be a symlink: {current}")
    if target.is_symlink():
        raise ValueError(f"transaction target must not be a symlink: {target}")


def write_transaction(root: Path, files: dict[Path, str]) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"transaction root must be a real directory: {root}")
    for target in files:
        validate_transaction_target(root, target)
    staging = Path(tempfile.mkdtemp(prefix=".snapshot-staging-", dir=root))
    try:
        for target, content in files.items():
            relative = target.relative_to(root)
            staged = staging / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            with staged.open("w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            fsync_directory(staged.parent)
        metadata_targets = [target for target in files if target.name == "snapshot_metadata.json"]
        ordered_targets = [target for target in files if target not in metadata_targets] + metadata_targets
        backups: dict[Path, Path | None] = {}
        backup_root = staging / ".backup"
        for target in ordered_targets:
            if target.is_file():
                backup = backup_root / target.relative_to(root)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                backups[target] = backup
            else:
                backups[target] = None
        replaced: list[Path] = []
        try:
            for target in ordered_targets:
                target.parent.mkdir(exist_ok=True)
                os.replace(staging / target.relative_to(root), target)
                replaced.append(target)
                fsync_directory(target.parent)
        except Exception:
            for target in reversed(replaced):
                backup = backups[target]
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(backup, target)
                fsync_directory(target.parent)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def write_outputs(rows: list[dict[str, object]], root: Path) -> None:
    data_dir = root / "data"
    src_dir = root / "src"
    targets = [
        data_dir / "pacific_climate_transition.csv",
        src_dir / "data.js",
        data_dir / "snapshot_metadata.json",
        data_dir / "data_dictionary.md",
    ]
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"transaction root must be a real directory: {root}")
    for target in targets:
        validate_transaction_target(root, target)
    data_dir.mkdir(exist_ok=True)
    src_dir.mkdir(exist_ok=True)

    fields = [
        "country_code",
        "country",
        "year",
        "ghg_tonnes_per_capita",
        "renewable_share_percent",
        "sst_anomaly_celsius",
    ]
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows({field: row.get(field, "") if row.get(field) is not None else "" for field in fields} for row in rows)
    csv_text = csv_buffer.getvalue()

    dictionary_text = None
    dictionary = data_dir / "data_dictionary.md"
    downloaded_at = datetime.now(timezone.utc)
    if dictionary.is_file():
        dictionary_text = dictionary.read_text(encoding="utf-8")
        dictionary_text = re.sub(r"Snapshot downloaded \*\*[^*]+\*\*", f"Snapshot downloaded **{downloaded_at.date().isoformat()}**", dictionary_text, count=1)

    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    metadata = {
        "transaction": "commit-marker-written-last",
        "downloaded_at_utc": downloaded_at.isoformat(timespec="seconds"),
        "downloaded_on": downloaded_at.date().isoformat(),
        "api_root": API_ROOT,
        "row_count": len(rows),
        "countries": sorted({row["country_code"] for row in rows}),
        "csv_sha256": hashlib.sha256(csv_text.encode("utf-8")).hexdigest(),
    }
    if dictionary_text is not None:
        metadata["dictionary_sha256"] = hashlib.sha256(dictionary_text.encode("utf-8")).hexdigest()
    data_text = f"window.PACIFIC_DATA={payload};window.PACIFIC_METADATA={json.dumps(metadata, separators=(',', ':'))};\n"
    metadata_text = json.dumps({**metadata, "data_js_sha256": hashlib.sha256(data_text.encode("utf-8")).hexdigest()}, indent=2) + "\n"
    files = {
        data_dir / "pacific_climate_transition.csv": csv_text,
        src_dir / "data.js": data_text,
        data_dir / "snapshot_metadata.json": metadata_text,
    }
    if dictionary_text is not None:
        files[dictionary] = dictionary_text
    write_transaction(root, files)
    print(f"snapshot metadata: {metadata['downloaded_on']} / CSV SHA-256 {metadata['csv_sha256'][:12]}…")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    rows = build_snapshot()
    write_outputs(rows, args.root)
    print(f"wrote {len(rows)} rows for {len(COUNTRIES)} countries")


if __name__ == "__main__":
    main()
