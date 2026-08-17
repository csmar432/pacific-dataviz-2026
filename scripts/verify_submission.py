#!/usr/bin/env python3
"""Run repeatable local delivery checks for the Pacific Dataviz submission."""

from __future__ import annotations

import csv
import functools
import hashlib
import json
import math
import os
import re
import secrets
import stat
import subprocess
import sys
import threading
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COUNTRIES = {"FJ", "KI", "WS", "SB", "TO", "TV", "VU"}
COUNTRY_NAMES = {"FJ": "Fiji", "KI": "Kiribati", "WS": "Samoa", "SB": "Solomon Islands", "TO": "Tonga", "TV": "Tuvalu", "VU": "Vanuatu"}
EXPECTED_YEARS = set(range(1990, 2025))
RANGES = {
    "ghg_tonnes_per_capita": (0, 100),
    "renewable_share_percent": (0, 100),
    "sst_anomaly_celsius": (-10, 10),
}
EXPECTED_FIELD_YEARS = {
    "ghg_tonnes_per_capita": EXPECTED_YEARS,
    "sst_anomaly_celsius": EXPECTED_YEARS,
    "renewable_share_percent": set(range(2010, 2023)),
}
EXPECTED_DATA_COLUMNS = [
    "country_code",
    "country",
    "year",
    "ghg_tonnes_per_capita",
    "renewable_share_percent",
    "sst_anomaly_celsius",
]
REQUIRED = [
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
    "submission/DELIVERY.md",
    "submission/build-environment.txt",
    "submission/fallback.html",
    "submission/fallback.pdf",
    "submission/fallback.png",
    "submission/pacific-dataviz-2026-release.zip",
]
EXPECTED_RELEASE_FILES = set(REQUIRED) - {
    "submission/DELIVERY.md",
    "submission/pacific-dataviz-2026-release.zip",
}


def check_file(path: str) -> tuple[bool, str]:
    try:
        target = project_file(path)
        return target.stat().st_size > 0, f"file: {path}"
    except (OSError, ValueError):
        return False, f"file: {path}"


def project_file(relative: str) -> Path:
    current = ROOT
    for part in Path(relative).parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"project file must not be a symlink: {relative}")
    if not current.is_file():
        raise FileNotFoundError(relative)
    return current


def check_data() -> tuple[bool, str]:
    with (ROOT / "data/pacific_climate_transition.csv").open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or reader.fieldnames != EXPECTED_DATA_COLUMNS or len(reader.fieldnames) != len(set(reader.fieldnames)):
            return False, "data: CSV header is not the exact unique schema"
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) or set(row) != set(EXPECTED_DATA_COLUMNS) for row in rows):
        return False, "data: CSV contains a malformed row"
    try:
        countries = {row["country_code"] for row in rows}
        counts = {code: sum(row["country_code"] == code for row in rows) for code in countries}
        years = {code: {int(row["year"]) for row in rows if row["country_code"] == code} for code in countries}
        field_coverage_ok = all(
            {int(row["year"]) for row in rows if row["country_code"] == code and row[field]} == expected_years
            for code in EXPECTED_COUNTRIES
            for field, expected_years in EXPECTED_FIELD_YEARS.items()
        )
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"data: invalid country or year value ({exc})"
    overlap = [row for row in rows if row["year"] == "2022" and all(row[field] for field in ["ghg_tonnes_per_capita", "renewable_share_percent", "sst_anomaly_celsius"])]
    overlap_codes = {row["country_code"] for row in overlap}
    names_ok = all(COUNTRY_NAMES.get(row["country_code"]) == row["country"] for row in rows)
    numeric = [field for field, bounds in RANGES.items() if all(_valid_number(row[field], *bounds) for row in rows if row[field])]
    coverage_ok = countries == EXPECTED_COUNTRIES and all(counts[code] == 35 and years[code] == EXPECTED_YEARS for code in EXPECTED_COUNTRIES)
    ok = len(rows) == 245 and coverage_ok and field_coverage_ok and names_ok and len(overlap) == 7 and overlap_codes == EXPECTED_COUNTRIES and len(numeric) == 3
    return ok, f"data: {len(rows)} bounded rows / {len(countries)} expected country identities / {len(overlap)} complete 2022 rows"


def _valid_number(value: str, lower: float, upper: float) -> bool:
    try:
        parsed = float(value)
        return math.isfinite(parsed) and lower <= parsed <= upper
    except ValueError:
        return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_rows(rows: list[dict[str, str | float | int | None]]) -> list[dict[str, object]]:
    fields = ["ghg_tonnes_per_capita", "renewable_share_percent", "sst_anomaly_celsius"]
    return [
        {
            "country_code": row["country_code"],
            "country": row["country"],
            "year": int(row["year"]),
            **{field: (float(row[field]) if row.get(field) not in (None, "") else None) for field in fields},
        }
        for row in rows
    ]


def check_embedded_data() -> tuple[bool, str]:
    csv_rows = list(csv.DictReader((ROOT / "data/pacific_climate_transition.csv").open(encoding="utf-8")))
    source = (ROOT / "src/data.js").read_text(encoding="utf-8")
    match = re.fullmatch(r"window\.PACIFIC_DATA=(.*?);window\.PACIFIC_METADATA=(.*?);\n", source, re.DOTALL)
    if not match:
        return False, "embedded data: generated data.js contract not found"
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return False, f"embedded data: invalid JSON ({exc})"
    try:
        ok = normalize_rows(payload) == normalize_rows(csv_rows)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"embedded data: invalid row value ({exc})"
    return ok, f"embedded data: {len(payload)} rows match the CSV snapshot"


def check_metadata() -> tuple[bool, str]:
    metadata = json.loads((ROOT / "data/snapshot_metadata.json").read_text(encoding="utf-8"))
    csv_path = ROOT / "data/pacific_climate_transition.csv"
    data_path = ROOT / "src/data.js"
    dictionary_path = ROOT / "data/data_dictionary.md"
    csv_rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    embedded_match = re.fullmatch(
        r"window\.PACIFIC_DATA=(.*?);window\.PACIFIC_METADATA=(.*?);\n",
        data_path.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    embedded = json.loads(embedded_match.group(2)) if embedded_match else {}
    semantic_keys = ["transaction", "downloaded_at_utc", "downloaded_on", "api_root", "row_count", "countries", "csv_sha256", "dictionary_sha256"]
    ok = (
        metadata.get("transaction") == "commit-marker-written-last"
        and metadata.get("csv_sha256") == sha256(csv_path)
        and metadata.get("data_js_sha256") == sha256(data_path)
        and metadata.get("dictionary_sha256") == sha256(dictionary_path)
        and metadata.get("row_count") == len(csv_rows)
        and metadata.get("countries") == sorted({row["country_code"] for row in csv_rows})
        and all(metadata.get(key) == embedded.get(key) for key in semantic_keys)
    )
    return ok, "metadata: snapshot date, row count and SHA-256 hashes are consistent"


def check_text_contract() -> tuple[bool, str]:
    page = (ROOT / "src/index.html").read_text(encoding="utf-8")
    dictionary = (ROOT / "data/data_dictionary.md").read_text(encoding="utf-8")
    forbidden = ["DEMO DATA", "Replace the demo values", "placeholder"]
    required_page = ["pacificdatavizchallenge.org", "data_dictionary.md", 'aria-live="polite"']
    required_dictionary = ["GHG_EMI_CAPITA", "SST_ANOM", "EG_FEC_RNEW"]
    forbidden.append('>Read as<')
    live_regions = {
        identifier: re.search(rf'<[^>]+id="{identifier}"[^>]*>', page)
        for identifier in ["snapshot-takeaway", "snapshot-detail", "trend-summary"]
    }
    live_regions_ok = all(match and 'aria-live="polite"' in match.group(0) and 'aria-atomic="true"' in match.group(0) for match in live_regions.values())
    ok = not any(item in page for item in forbidden) and all(item in page for item in required_page) and all(item in dictionary for item in required_dictionary) and live_regions_ok
    return ok, "text contract: official IDs, source links and no demo placeholder"


class LocalLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.links.append(value)


def check_local_links() -> tuple[bool, str]:
    parser = LocalLinkParser()
    parser.feed((ROOT / "src/index.html").read_text(encoding="utf-8"))
    missing: list[str] = []
    for link in parser.links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (ROOT / "src" / unquote(parsed.path)).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            missing.append(link)
            continue
        if not target.is_file() and not (target.is_dir() and (target / "index.html").is_file()):
            missing.append(link)
    if missing:
        return False, f"links: missing {', '.join(missing)}"
    return True, f"links: {len(parser.links)} local HTML links resolve"


def check_node() -> tuple[bool, str]:
    commands = [["node", "--check", "src/app.js"], ["node", "--check", "src/data.js"], ["node", "scripts/runtime_smoke_test.js"]]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            return False, f"syntax: {' '.join(command)}\n{result.stderr.strip()}"
    return True, "syntax: app.js and data.js"


def check_fetch_validation() -> tuple[bool, str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-B", "scripts/fetch_validation_smoke_test.py"], cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode:
        return False, f"fetch validation: {result.stderr.strip()}"
    return True, "fetch validation: malformed rows, non-CSV MIME, redirects and incomplete API identities/coverage are rejected"


def check_verifier_adversarial() -> tuple[bool, str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-B", "scripts/verification_adversarial_smoke_test.py"], cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode:
        return False, f"verifier adversarial: {result.stderr.strip()}"
    return True, "verifier adversarial: trailing CSV fields and symlink escapes are rejected"


def check_build_environment() -> tuple[bool, str]:
    evidence = (ROOT / "submission/build-environment.txt").read_text(encoding="utf-8")
    labels = ["Python: ", "WeasyPrint: ", "pdftoppm/Poppler: pdftoppm version "]
    ok = all(any(line.startswith(label) and len(line) > len(label) for line in evidence.splitlines()) for label in labels)
    return ok, "build environment: Python, WeasyPrint and Poppler versions recorded"


def check_cache_hygiene() -> tuple[bool, str]:
    caches = list((ROOT / "scripts").rglob("__pycache__")) + list((ROOT / "scripts").rglob("*.pyc"))
    return not caches, f"cache hygiene: {len(caches)} generated Python cache path(s)"


def check_pdf() -> tuple[bool, str]:
    try:
        import pdfplumber

        with pdfplumber.open(ROOT / "submission/fallback.pdf") as pdf:
            text = pdf.pages[0].extract_text() or ""
            ok = len(pdf.pages) == 1 and "The Pacific" in text and "SST" in text and "ANOMALY" in text
        return ok, f"pdf: {len(pdf.pages)} page(s), text and table checks"
    except Exception as exc:  # pragma: no cover - environment dependency
        return False, f"pdf: {exc}"


def check_release() -> tuple[bool, str]:
    archive_path = ROOT / "submission/pacific-dataviz-2026-release.zip"
    with ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if any(info.create_system == 3 and stat.S_ISLNK(info.external_attr >> 16) for info in infos):
            return False, "release: archive contains a symbolic-link entry"
        names = [info.filename for info in infos]
        manifest_name = "pacific-dataviz-2026/submission/release-manifest.sha256"
        expected_names = {f"pacific-dataviz-2026/{relative}" for relative in EXPECTED_RELEASE_FILES} | {manifest_name}
        normalized_names = [name.replace("\\", "/") for name in names]
        canonical = all("\\" not in name for name in names)
        safe = canonical and all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in normalized_names)
        unique = len(names) == len(set(names))
        if not safe or not unique or set(names) != expected_names:
            return False, f"release: {len(names)} archive paths are unsafe, duplicate or incomplete"
        entries: dict[str, str] = {}
        for line in archive.read(manifest_name).decode("utf-8").splitlines():
            parts = line.split("  ", 1)
            if len(parts) != 2:
                return False, "release: malformed SHA-256 manifest line"
            digest, relative = parts
            path = Path(relative)
            if not re.fullmatch(r"[0-9a-f]{64}", digest) or relative in entries:
                return False, "release: invalid digest or duplicate manifest path"
            if "\\" in relative or path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
                return False, "release: unsafe manifest path"
            entries[relative] = digest
        if set(entries) != EXPECTED_RELEASE_FILES:
            return False, "release: manifest does not match the fixed release allowlist"
        try:
            local_files = {relative: project_file(relative).read_bytes() for relative in EXPECTED_RELEASE_FILES}
        except (OSError, ValueError):
            return False, "release: allowlisted local source is missing or a symlink"
        same = all(
            hashlib.sha256(local_files[relative]).hexdigest() == digest
            and archive.read(f"pacific-dataviz-2026/{relative}") == local_files[relative]
            for relative, digest in entries.items()
        )
    ok = same
    return ok, f"release: {len(names)} safe files match the SHA-256 manifest"


def check_http() -> tuple[bool, str]:
    token = secrets.token_hex(16)

    class SmokeHandler(SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            self.send_header("X-Pacific-Smoke-Token", token)
            super().end_headers()

        def log_message(self, _format: str, *args: object) -> None:
            return

    handler = functools.partial(SmokeHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        paths = [
            "/src/",
            "/data/pacific_climate_transition.csv",
            "/data/data_dictionary.md",
            "/data/snapshot_metadata.json",
            "/submission/checklist.md",
            "/submission/README.md",
            "/submission/pacific-dataviz-2026-release.zip",
        ]
        for path in paths:
            with urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
                response.read()
                expected_server = response.headers.get("X-Pacific-Smoke-Token") == token
                expected_path = urlsplit(response.geturl()).path == path
                if response.status != 200 or not expected_server or not expected_path:
                    return False, f"http: {path} did not come from the expected local server"
        return True, f"http: {len(paths)} public package paths returned 200"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def write_delivery(results: list[tuple[bool, str]], external: list[str]) -> None:
    passed = sum(ok for ok, _ in results)
    lines = [
        "# Delivery report",
        "",
        "Generated by `scripts/verify_submission.py`.",
        "",
        f"- Local checks passed: **{passed}/{len(results)}**",
        "- Internal package status: **READY**" if passed == len(results) else "- Internal package status: **CHECKS FAILED**",
        "- External status: **REQUIRES HUMAN / HOSTING INPUT**",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- [{'x' if ok else ' '}] {message}" for ok, message in results)
    lines += ["", "## External items that cannot be safely automated here", ""]
    lines.extend(f"- [ ] {item}" for item in external)
    lines += ["", "The original project remains outside this isolated copy and is not modified by this report.", ""]
    submission = ROOT / "submission"
    delivery = submission / "DELIVERY.md"
    if ROOT.is_symlink() or not ROOT.is_dir() or submission.is_symlink() or not submission.is_dir() or delivery.is_symlink():
        raise ValueError("delivery path must remain inside real project directories")
    delivery.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    results = [check_file(path) for path in REQUIRED]
    results.extend([
        check_data(),
        check_embedded_data(),
        check_metadata(),
        check_text_contract(),
        check_local_links(),
        check_node(),
        check_fetch_validation(),
        check_verifier_adversarial(),
        check_build_environment(),
        check_cache_hygiene(),
        check_pdf(),
        check_release(),
        check_http(),
    ])
    external = [
        "Add the real creator/team identity and contact details to the registration form.",
        "Independently confirm the exact dataset-specific licence/attribution terms; the API does not expose a licence field and the package does not guess one.",
        "Keep the published interactive URL accessible until 31 August 2029.",
        "Test the hosted page from a logged-out browser and capture the live-page screenshot.",
        "Confirm the entrant's originality statement and approve the prepared AI-use disclosure.",
        "Submit the registration form before 31 August 2026, 23:00 Fiji time.",
    ]
    write_delivery(results, external)
    for ok, message in results:
        print(f"{'PASS' if ok else 'FAIL'} {message}")
    print(f"WROTE submission/DELIVERY.md ({sum(ok for ok, _ in results)}/{len(results)} internal checks passed)")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
