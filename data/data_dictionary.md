# Data dictionary and provenance

Snapshot downloaded **2026-08-16** from the Pacific Data Hub `.Stat` REST API. The page uses no fabricated values, interpolation or silent substitution.

## Licence and attribution gate

The [Pacific Data Hub terms of use](https://pacificdata.org/terms-use) state that datasets can have different licences and that the applicable dataset page controls the required attribution. The current `.Stat` dataflow responses used for this snapshot do not expose a licence field, so this package deliberately does not guess a licence or invent attribution language. Before publication, open the metadata for each official dataflow, record the exact licence name/version and required attribution in the submission form, and retain a dated copy or URL as evidence. The official challenge requires all data sources to be listed.

## Dataset 1 — greenhouse gas emissions per capita

- **Official indicator:** `GHG_EMI_CAPITA`
- **Dataflow:** `SPC:DF_CLIMATE_CHANGE (1.0)`
- **Unit:** tonnes per person (`TON` in the API response)
- **Coverage in this snapshot:** 1990–2024, annual
- **Query template:**
  `https://stats-nsi-stable.pacificdata.org/rest/data/SPC,DF_CLIMATE_CHANGE,1.0/A.GHG_EMI_CAPITA.{GEO_PICT}?startPeriod=1990&endPeriod=2024&dimensionAtObservation=AllDimensions`
- **Official explorer:** [GHG emissions per capita](https://stats.pacificdata.org/vis?av=true&df%5Bag%5D=SPC&df%5Bds%5D=SPC2&df%5Bid%5D=DF_CLIMATE_CHANGE&df%5Bvs%5D=1.0&dq=A.GHG_EMI_CAPITA.&lc=en&pd=%2C&to%5BTIME_PERIOD%5D=false)

## Dataset 2 — mean sea surface temperature anomaly

- **Official indicator:** `SST_ANOM`
- **Dataflow:** `SPC:DF_CLIMATE_CHANGE (1.0)`
- **Unit:** degrees Celsius (`CELSIUS` in the API response)
- **Coverage in this snapshot:** 1990–2024, annual
- **Definition:** Difference between mean annual sea surface temperature over a country’s Exclusive Economic Zone and the 1971–2000 reference-period average.
- **Query template:**
  `https://stats-nsi-stable.pacificdata.org/rest/data/SPC,DF_CLIMATE_CHANGE,1.0/A.SST_ANOM.{GEO_PICT}?startPeriod=1990&endPeriod=2024&dimensionAtObservation=AllDimensions`
- **Official explorer:** [Mean sea surface temperature anomalies](https://stats.pacificdata.org/vis?av=true&df%5Bag%5D=SPC&df%5Bds%5D=SPC2&df%5Bid%5D=DF_CLIMATE_CHANGE&df%5Bvs%5D=1.0&dq=A.SST_ANOM.&lc=en&pd=%2C&to%5BTIME_PERIOD%5D=false)

This is a regional climate signal over the EEZ, not a direct measure of household exposure, damage or vulnerability. It should not be read as a causal effect of the two energy indicators.

## Dataset 3 — renewable energy share

- **Official indicator:** `EG_FEC_RNEW`
- **Dataflow:** `SPC:DF_SDG (3.0)`
- **Unit:** percent of total final energy consumption (`PERCENT` in the API response)
- **Coverage in this snapshot:** 2010–2022, annual
- **Breakdowns:** total population/energy series (`_T` dimensions and `_Z` composite breakdown as returned by the official Data Explorer query)
- **Query template:**
  `https://stats-nsi-stable.pacificdata.org/rest/data/SPC,DF_SDG,3.0/A.EG_FEC_RNEW.{GEO_PICT}._T._T._T._T._T._T._Z._T?startPeriod=2010&endPeriod=2022&dimensionAtObservation=AllDimensions`
- **Data source reported by the API:** Energy Balances, UN Statistics Division (2024)
- **Official explorer:** [Renewable energy share](https://stats.pacificdata.org/vis?bp=true&df%5Bag%5D=SPC&df%5Bds%5D=ds%3ASPC2&df%5Bid%5D=DF_SDG&df%5Bvs%5D=3.0&dq=A.EG_FEC_RNEW.._T._T._T._T._T._T._Z._T&fc=Development+indicators&fs%5B0%5D=Development+indicators%2C0%7CSustainable+Development+Goals%23SDG%23&pd=%2C&pg=0&snb=18&to%5BTIME_PERIOD%5D=false)

## Geographic scope

| Code | Country |
|---|---|
| FJ | Fiji |
| KI | Kiribati |
| WS | Samoa |
| SB | Solomon Islands |
| TO | Tonga |
| TV | Tuvalu |
| VU | Vanuatu |

## How the page uses the data

1. The scatter plot keeps only rows with emissions, renewable share and sea-surface anomaly in **2022**, the latest common year for all three indicators in this snapshot.
2. The trend selector shows all available observations for one country and one indicator.
3. The table ranks the selected 2022 countries by renewable share only for visual reading and displays the climate signal as a separate, non-ranking column.
4. Missing indicator values remain missing; the page does not impute, extrapolate or convert units.
5. The page does not claim that renewable energy causes emissions to rise or fall, and it does not use either indicator as a proxy for climate vulnerability.

## API documentation

- [Pacific Data Hub API overview](https://docs.pacificdata.org/dotstat/api)
- [Pacific Data Hub API interface](https://docs.pacificdata.org/dotstat/api/interface)
- [Pacific Dataviz Challenge 2026 official datasets](https://pacificdatavizchallenge.org/)
