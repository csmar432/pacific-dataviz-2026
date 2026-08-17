# Submission form text

## Project title

**Two speeds of transition**

## Problem addressed

Climate conversations often compress the Pacific into one story: small island countries are treated as a single category, even though their energy systems and per-person greenhouse gas emissions differ. That makes it harder to ask a fair policy question. A country with lower emissions is not automatically less exposed to climate impacts, and a higher renewable share is not a complete measure of resilience.

## How the dataviz responds

This interactive visualisation places three official indicators side by side for seven Pacific island states: per-capita emissions, renewable energy share and mean sea-surface-temperature anomaly over each country’s EEZ. The 2022 scatter plot gives a common-year comparison; the country selector then shows each country’s available time series. A plain-language table, definitions, sources and limitations remain visible beside the charts so readers can inspect the evidence rather than treat the visual as a ranking.

The intended takeaway is simple: transition planning needs country-specific starting points. The next question is not who is “winning”, but which investments can make clean energy dependable and affordable without shifting costs onto communities already exposed to climate risk.

## Data used

1. Pacific Data Hub `.Stat`, `GHG_EMI_CAPITA` and `SST_ANOM`, `DF_CLIMATE_CHANGE` (official Challenge dataset list).
2. Pacific Data Hub `.Stat`, `EG_FEC_RNEW`, `DF_SDG` (official Challenge dataset list).

Full definitions and API queries: [`../data/data_dictionary.md`](../data/data_dictionary.md).

## Format

Interactive dataviz: publish the project root with `src/index.html` as the entry page (or configure equivalent routes for `data/` and `submission/`). Keep the URL accessible until at least 31 August 2029, as required by the official rules.

## Human contribution / AI disclosure

The research question, geographic scope, indicator selection, interpretation, caveats and final design decisions must be reviewed and owned by the entrant. AI was used only as a coding and editing assistant; it did not replace the entrant’s data verification or creative judgement. See [`ai-disclosure.md`](ai-disclosure.md).
