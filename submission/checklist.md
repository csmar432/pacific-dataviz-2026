# Pre-submission checklist

The official [2026 rules](https://pacificdatavizchallenge.org/sites/default/files/2026-05/Pacific-Dataviz-Challenge-2026-rules-reglement.pdf) should be treated as authoritative if they change.

## Already covered by this submission

- [x] Climate change theme.
- [x] At least one dataset from the official list; this submission uses two.
- [x] All datasets named with indicator IDs and source links.
- [x] Problem statement and explanation of how the dataviz responds.
- [x] Interactive public-page format is supported.
- [x] English-language page and supporting explanation.
- [x] Local CSV snapshot, data dictionary and reproducible fetch script.
- [x] Explicit limitations and non-causal language.
- [x] Responsive layout, keyboard-visible controls, chart titles/descriptions, print CSS and CSV fallback.

## Must be completed by the entrant

- [ ] Confirm the latest official rules and dataset metadata immediately before submission.
- [ ] Refresh the snapshot with `python3 scripts/fetch_official_data.py` and record the new download date.
- [ ] Check the licence/attribution terms for both datasets and keep the required attribution on the public page.
- [ ] Record the exact dataset-specific licence name/version and required attribution from the metadata page; the package does not infer a licence when the `.Stat` response omits it.
- [ ] Replace the generic creator/team line with the entrant’s real name/team and contact details in the registration form.
- [x] Publish the project root at <https://csmar432.github.io/pacific-dataviz-2026/src/> with HTTPS; keep it accessible through **31 August 2029**.
- [x] Capture live-page screenshots from Chrome at `submission/screenshots/online-desktop.png` and `submission/screenshots/online-mobile.png`.
- [ ] Recheck the hosted page from a logged-out or incognito browser.
- [x] Export a high-quality PDF/PNG fallback and inspect it at 100% scale (`fallback.pdf`, `fallback.png`).
- [x] Keep live-page screenshots, the CSV and the data dictionary beside the project archive.
- [ ] Proofread every claim and independently verify the values against the official source.
- [ ] Confirm the prepared AI disclosure matches the entrant’s actual workflow and submit it with the entry.
- [ ] Submit before **31 August 2026, 23:00 Fiji time**.
