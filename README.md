# Two speeds of transition

An interactive, evidence-first submission for the [Pacific Dataviz Challenge 2026](https://pacificdatavizchallenge.org/).

## Story

**Question:** How can a region with very different carbon footprints plan a fair energy transition?

The page compares three official indicators across Fiji, Kiribati, Samoa, Solomon Islands, Tonga, Tuvalu and Vanuatu:

- greenhouse gas emissions per capita, 1990–2024;
- mean sea-surface-temperature anomaly over each country’s EEZ, 1990–2024;
- renewable energy share of total final energy consumption, 2010–2022.

The shared period ends in 2022, so the 2022 scatter plot is the main comparison. The page deliberately treats the three indicators as descriptive signals, not a policy score or causal estimate.

## Run locally

The interactive page has no build step or runtime third-party dependency. The optional PDF/PNG fallback build uses the installed WeasyPrint Python package and `pdftoppm`.

From this directory:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open <http://localhost:8000/src/>. Serve the project root (not only `src/`) so the data dictionary, fetch script, CSV and submission links remain available. The page also works as a local file in browsers that allow scripts from the same directory.

## Refresh the official snapshot

```bash
python3 scripts/run_pipeline.py
```

The pipeline refreshes the official snapshot, rebuilds the static fallback, creates the release archive and runs the delivery checks. Individual scripts remain available for debugging. It writes:

- `data/pacific_climate_transition.csv` — inspectable local snapshot;
- `src/data.js` — the same snapshot embedded for offline page use.

The pipeline also writes `data/snapshot_metadata.json`, which records the API snapshot date and hashes used to verify the local package. It refreshes `submission/fallback.html`, `submission/fallback.pdf` and `submission/fallback.png` from the same CSV, and records the fallback tool versions in `submission/build-environment.txt`.

The API queries, indicator IDs, units, coverage and missing-value policy are documented in [`data/data_dictionary.md`](data/data_dictionary.md).

## Project layout

- `src/index.html` — semantic page structure and competition narrative;
- `src/styles.css` — responsive, print-friendly visual system;
- `src/app.js` — dependency-free SVG charts and interactions;
- `src/data.js` — generated local snapshot used by the page;
- `data/` — CSV and data definitions;
- `scripts/fetch_official_data.py` — reproducible API fetcher;
- `scripts/build_static_fallback.py` — one-page fallback exporter;
- `scripts/build_release.py` — submission archive builder;
- `submission/` — problem statement, AI disclosure and pre-submission checklist.

## Before submission

The static fallback is already generated as `submission/fallback.pdf`, `submission/fallback.png` and `submission/fallback.html`; the full package is `submission/pacific-dataviz-2026-release.zip`. Complete the remaining items in [`submission/checklist.md`](submission/checklist.md): refresh and verify data, add creator/team details, check licences, and publish the interactive page at a stable public URL. Publish the project root with `/src/` as the entry path, or configure equivalent routes for the sibling evidence files. The official rules require an interactive URL to remain accessible until at least 31 August 2029.
