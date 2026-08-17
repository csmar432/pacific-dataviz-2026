#!/usr/bin/env python3
"""Build a one-page static fallback from the local official data snapshot."""

from __future__ import annotations

import csv
import html
import json
import platform
import subprocess
from pathlib import Path

import weasyprint


COLORS = {"FJ": "#147c73", "KI": "#d66c52", "WS": "#7c61a8", "SB": "#2d8caa", "TO": "#c88c2f", "TV": "#4f8d61", "VU": "#bd5b65"}
CHART_LABELS = {"FJ": "Fiji", "KI": "Kiribati", "WS": "Samoa", "SB": "Solomon", "TO": "Tonga", "TV": "Tuvalu", "VU": "Vanuatu"}


def fmt(value: str, digits: int = 1) -> str:
    return f"{float(value):.{digits}f}".rstrip("0").rstrip(".")


def read_snapshot(root: Path) -> list[dict[str, str]]:
    with (root / "data/pacific_climate_transition.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return sorted(
        [
            row
            for row in rows
            if row["year"] == "2022"
            and row["renewable_share_percent"]
            and row["ghg_tonnes_per_capita"]
            and row["sst_anomaly_celsius"]
        ],
        key=lambda row: float(row["renewable_share_percent"]),
        reverse=True,
    )


def scatter(rows: list[dict[str, str]]) -> str:
    width, height = 760, 380
    left, right, top, bottom = 60, 22, 22, 52
    chart_width, chart_height = width - left - right, height - top - bottom
    x = lambda value: left + float(value) / 55 * chart_width
    y = lambda value: top + chart_height - float(value) / 3.6 * chart_height
    grid = []
    for tick in [0, 10, 20, 30, 40, 50]:
        grid.append(f'<line x1="{x(tick)}" y1="{top}" x2="{x(tick)}" y2="{top + chart_height}" stroke="#e5eae4"/><text x="{x(tick)}" y="{height - 22}" text-anchor="middle" class="axis">{tick}%</text>')
    for tick in [0, 1, 2, 3]:
        grid.append(f'<line x1="{left}" y1="{y(tick)}" x2="{width - right}" y2="{y(tick)}" stroke="#e5eae4"/><text x="{left - 10}" y="{y(tick) + 4}" text-anchor="end" class="axis">{tick}</text>')
    dots = []
    for row in rows:
        px, py = x(row["renewable_share_percent"]), y(row["ghg_tonnes_per_capita"])
        dots.append(f'<circle cx="{px}" cy="{py}" r="8" fill="{COLORS[row["country_code"]]}" stroke="#fffefa" stroke-width="3"/><text x="{px + 12}" y="{py + 4}" class="label">{html.escape(CHART_LABELS[row["country_code"]])}</text>')
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="2022 comparison of renewable share and greenhouse gas emissions per person">{"".join(grid)}<line x1="{left}" y1="{top + chart_height}" x2="{width - right}" y2="{top + chart_height}" stroke="#9eb2ae"/><text x="{width / 2}" y="{height - 3}" text-anchor="middle" class="axis-title">Renewable share of total final energy consumption</text><text x="16" y="{height / 2}" transform="rotate(-90 16 {height / 2})" text-anchor="middle" class="axis-title">GHG emissions / person</text>{"".join(dots)}</svg>'


def build(root: Path) -> None:
    submission = root / "submission"
    if any(path.is_symlink() or not path.is_dir() for path in [root, root / "data", submission]):
        raise ValueError("fallback paths must remain inside real project directories")
    output_paths = [submission / "fallback.html", submission / "fallback.pdf", submission / "fallback.png", submission / "build-environment.txt"]
    if any(path.is_symlink() for path in output_paths):
        raise ValueError("fallback output must not be a symlink")
    rows = read_snapshot(root)
    if not rows:
        raise RuntimeError("the 2022 fallback requires at least one complete country row")
    metadata = json.loads((root / "data/snapshot_metadata.json").read_text(encoding="utf-8"))
    snapshot_date = html.escape(metadata["downloaded_on"])
    highest = rows[0]
    lowest_ghg = min(rows, key=lambda row: float(row["ghg_tonnes_per_capita"]))
    table = "".join(
        f'<tr><th scope="row"><strong>{index}</strong> {html.escape(row["country"])}</th><td>{fmt(row["renewable_share_percent"], 2)}%</td><td>{fmt(row["ghg_tonnes_per_capita"])} t</td><td>{fmt(row["sst_anomaly_celsius"])}°C</td></tr>'
        for index, row in enumerate(rows, 1)
    )
    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Two speeds of transition — static fallback</title>
<style>
@page {{ size: A4 landscape; margin: 16mm; }}
* {{ box-sizing: border-box; }} body {{ margin: 0; color: #122f35; background: #f7f5ef; font-family: Arial, sans-serif; }}
.top {{ display: flex; justify-content: space-between; gap: 30px; align-items: end; border-bottom: 1px solid #d7dfd8; padding-bottom: 16px; }}
.eyebrow {{ color: #147c73; font-size: 10px; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; }}
h1 {{ max-width: 690px; margin: 8px 0 8px; font-size: 38px; line-height: .98; }} p {{ color: #48666b; line-height: 1.45; }} .lede {{ max-width: 620px; margin: 0; font-size: 13px; }}
.badge {{ padding: 8px 11px; border: 1px solid #bddbd0; border-radius: 20px; color: #075951; font-size: 10px; white-space: nowrap; }}
.grid {{ display: grid; grid-template-columns: 1.4fr .6fr; gap: 18px; margin-top: 18px; }} .card {{ padding: 16px; border: 1px solid #d7dfd8; border-radius: 12px; background: #fffefa; }}
.card h2 {{ margin: 0 0 10px; font-size: 18px; }} .chart {{ min-height: 315px; }} svg {{ display: block; width: 100%; height: auto; }} .axis {{ fill: #526b6f; font-size: 10px; }} .axis-title {{ fill: #48666b; font-size: 10px; font-weight: bold; }} .label {{ fill: #122f35; font-size: 10px; font-weight: bold; }}
.callout {{ padding: 15px; border-radius: 10px; background: #075951; color: white; }} .callout .eyebrow {{ color: #bde1d1; }} .callout h2 {{ color: white; font-size: 22px; line-height: 1.05; }} .callout p {{ color: #c9dfd7; font-size: 11px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 11px; }} th, td {{ padding: 7px 5px; border-bottom: 1px solid #d7dfd8; text-align: left; }} thead th {{ color: #526b6f; font-size: 9px; text-transform: uppercase; letter-spacing: 1px; }} tbody th {{ font-weight: normal; }} .sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }} .note {{ margin: 11px 0 0; font-size: 10px; }} .footer {{ position: fixed; right: 0; bottom: 0; left: 0; color: #526b6f; font-size: 9px; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 4px 12px; margin: 2px 0 0; color: #526b6f; font-size: 9px; }} .legend span {{ white-space: nowrap; }} .legend i {{ display: inline-block; width: 7px; height: 7px; margin-right: 4px; border-radius: 50%; }}
</style></head><body>
<header class="top"><div><div class="eyebrow">Pacific Dataviz Challenge · 2026</div><h1>The Pacific’s transition is not one story.</h1><p class="lede">A common-year comparison of renewable energy share and greenhouse gas emissions per person across seven Pacific island states.</p></div><div class="badge">STATIC FALLBACK · 2022</div></header>
<main class="grid"><section class="card"><h2>Three signals, different pressures</h2><div class="chart">{scatter(rows)}</div><p class="legend" aria-label="Country key">{"".join(f'<span><i style="background:{COLORS[row["country_code"]]}"></i>{html.escape(row["country_code"])} {html.escape(row["country"])}</span>' for row in rows)}</p><p class="note">Right = higher renewable share. Up = higher GHG emissions per person. The axes are descriptive signals, not a score.</p></section>
<aside><section class="callout"><div class="eyebrow">What the snapshot says</div><h2>{html.escape(highest["country"])} has the highest renewable share.</h2><p>{fmt(highest["renewable_share_percent"], 2)}% in 2022. {html.escape(lowest_ghg["country"])} records the lowest emissions in the comparison at {fmt(lowest_ghg["ghg_tonnes_per_capita"])} tonnes per person.</p></section><section class="card" style="margin-top:18px"><h2>2022 comparison</h2><table><caption class="sr-only">2022 renewable energy, greenhouse gas emissions and sea-surface-temperature comparison by country</caption><thead><tr><th scope="col">Country</th><th scope="col">Renewable</th><th scope="col">GHG / person</th><th scope="col">SST anomaly</th></tr></thead><tbody>{table}</tbody></table></section></aside></main>
<footer class="footer">Source: Pacific Data Hub .Stat, GHG_EMI_CAPITA, SST_ANOM and EG_FEC_RNEW. Snapshot downloaded {snapshot_date}. Rank is descriptive only. See data/data_dictionary.md for definitions and API queries.</footer>
</body></html>'''
    output = submission / "fallback.html"
    output.write_text(document, encoding="utf-8")
    pdf = submission / "fallback.pdf"
    weasyprint.HTML(string=document, base_url=str(root)).write_pdf(pdf)
    png_stem = submission / "fallback"
    subprocess.run(["pdftoppm", "-png", "-r", "160", "-singlefile", str(pdf), str(png_stem)], check=True)
    version_result = subprocess.run(["pdftoppm", "-v"], check=True, capture_output=True, text=True)
    poppler_version = (version_result.stderr or version_result.stdout).splitlines()[0]
    (submission / "build-environment.txt").write_text(
        f"Python: {platform.python_version()}\n"
        f"WeasyPrint: {weasyprint.__version__}\n"
        f"pdftoppm/Poppler: {poppler_version}\n",
        encoding="utf-8",
    )
    print(f"wrote {output.name}, {pdf.name}, {png_stem.name}.png for {len(rows)} countries")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
