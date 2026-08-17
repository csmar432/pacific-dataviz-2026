(() => {
  "use strict";

  const numberOrNull = (value) => {
    if (value === "" || value == null) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const data = (window.PACIFIC_DATA || []).map((row) => ({
    ...row,
    year: Number(row.year),
    ghg_tonnes_per_capita: numberOrNull(row.ghg_tonnes_per_capita),
    renewable_share_percent: numberOrNull(row.renewable_share_percent),
    sst_anomaly_celsius: numberOrNull(row.sst_anomaly_celsius),
  }));
  const countries = [
    { code: "FJ", name: "Fiji", short: "Fiji" },
    { code: "KI", name: "Kiribati", short: "Kiribati" },
    { code: "WS", name: "Samoa", short: "Samoa" },
    { code: "SB", name: "Solomon Islands", short: "Solomon" },
    { code: "TO", name: "Tonga", short: "Tonga" },
    { code: "TV", name: "Tuvalu", short: "Tuvalu" },
    { code: "VU", name: "Vanuatu", short: "Vanuatu" },
  ];
  const colors = { FJ: "#147c73", KI: "#d66c52", WS: "#7c61a8", SB: "#2d8caa", TO: "#c88c2f", TV: "#4f8d61", VU: "#bd5b65" };
  const latestOverlap = 2022;
  const indicatorLabels = {
    renewable_share_percent: "renewable energy share",
    ghg_tonnes_per_capita: "GHG emissions per person",
    sst_anomaly_celsius: "sea-surface temperature anomaly",
  };
  const active = new Set(countries.map((country) => country.code));
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
  const fmt = (value, digits = 1) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(digits).replace(/\.0+$/, "") : "No observation";
  };
  const byCode = (code) => countries.find((country) => country.code === code);
  const rowsFor = (code) => data.filter((row) => row.country_code === code).sort((a, b) => a.year - b.year);
  const snapshot = data.filter((row) => row.year === latestOverlap && row.ghg_tonnes_per_capita !== null && row.renewable_share_percent !== null && row.sst_anomaly_celsius !== null);

  function formatYearRanges(years) {
    const ranges = [];
    let rangeStart = years[0];
    let previousYear = years[0];
    years.slice(1).forEach((year) => {
      if (year === previousYear + 1) {
        previousYear = year;
        return;
      }
      ranges.push(rangeStart === previousYear ? `${rangeStart}` : `${rangeStart}–${previousYear}`);
      rangeStart = year;
      previousYear = year;
    });
    ranges.push(rangeStart === previousYear ? `${rangeStart}` : `${rangeStart}–${previousYear}`);
    return ranges.join(", ");
  }

  function svgText(x, y, text, className = "") {
    return `<text x="${x}" y="${y}" class="${className}">${esc(text)}</text>`;
  }

  function renderFilters() {
    const container = $("#country-filters");
    container.innerHTML = countries.map((country) => `<button type="button" class="country-filter" data-code="${country.code}" aria-pressed="${active.has(country.code)}"><span class="filter-dot" style="background:${colors[country.code]}" aria-hidden="true"></span>${country.name}</button>`).join("");
    container.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        const code = button.dataset.code;
        if (active.has(code) && active.size === 1) return;
        if (active.has(code)) active.delete(code);
        else active.add(code);
        button.setAttribute("aria-pressed", String(active.has(code)));
        renderScatter();
        renderTable();
        updateTakeaway();
      });
    });
  }

  function renderSnapshotStatus() {
    const status = $("#snapshot-data-status");
    if (!status) return;
    const available = new Set(snapshot.map((row) => row.country_code));
    const selected = snapshot.filter((row) => active.has(row.country_code)).length;
    status.textContent = available.size === countries.length
      ? `Showing ${selected} of ${countries.length} countries with complete 2022 observations.`
      : `Showing ${selected} of ${countries.length} expected countries; ${countries.length - available.size} with missing values are excluded.`;
  }

  function renderScatter() {
    const width = 760;
    const height = 430;
    const margin = { top: 20, right: 24, bottom: 58, left: 58 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;
    const xMax = 55;
    const yMax = 3.6;
    const x = (value) => margin.left + (value / xMax) * chartWidth;
    const y = (value) => margin.top + chartHeight - (value / yMax) * chartHeight;
    const ticksX = [0, 10, 20, 30, 40, 50];
    const ticksY = [0, 1, 2, 3];
    const gridX = ticksX.map((tick) => `<line x1="${x(tick)}" y1="${margin.top}" x2="${x(tick)}" y2="${margin.top + chartHeight}" class="chart-grid-line"/>${svgText(x(tick), height - 28, `${tick}%`, "axis-label axis-label-center")}`).join("");
    const gridY = ticksY.map((tick) => `<line x1="${margin.left}" y1="${y(tick)}" x2="${width - margin.right}" y2="${y(tick)}" class="chart-grid-line"/>${svgText(margin.left - 12, y(tick) + 4, `${tick}`, "axis-label axis-label-end")}`).join("");
    const visibleRows = snapshot.filter((row) => active.has(row.country_code));
    renderSnapshotStatus();
    if (!visibleRows.length) {
      $("#scatter-chart").innerHTML = '<p class="chart-empty" role="status">No complete 2022 observations are available for the selected countries.</p>';
      return;
    }
    const points = visibleRows.map((row) => {
      const label = byCode(row.country_code).short;
      return `<g class="scatter-point"><circle cx="${x(row.renewable_share_percent)}" cy="${y(row.ghg_tonnes_per_capita)}" r="9" fill="${colors[row.country_code]}" fill-opacity=".9" stroke="#fffefa" stroke-width="3"><title>${esc(byCode(row.country_code).name)}: ${fmt(row.renewable_share_percent, 2)}% renewable, ${fmt(row.ghg_tonnes_per_capita, 1)} tonnes per person</title></circle>${svgText(x(row.renewable_share_percent) + 13, y(row.ghg_tonnes_per_capita) + 4, label, "point-label")}</g>`;
    }).join("");
    $("#scatter-chart").innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="scatter-title scatter-desc"><title id="scatter-title">Renewable energy share and greenhouse gas emissions per capita in 2022</title><desc id="scatter-desc">The horizontal axis shows renewable share of final energy consumption. The vertical axis shows tonnes of greenhouse gas emissions per person. Highlighted countries are shown as coloured dots.</desc><g>${gridX}${gridY}<line x1="${margin.left}" y1="${margin.top + chartHeight}" x2="${width - margin.right}" y2="${margin.top + chartHeight}" class="axis-line"/>${svgText(width / 2, height - 5, "Renewable share of total final energy consumption", "axis-title axis-label-center")}${svgText(16, margin.top + chartHeight / 2, "GHG emissions / person", "axis-title axis-label-center axis-y-title")}${points}</g></svg>`;
  }

  function lineChart(code, field, color, yMin, yMax, yUnit) {
    const allRows = rowsFor(code);
    const observedRows = allRows.filter((row) => row[field] !== null);
    const indicator = indicatorLabels[field];
    if (!observedRows.length) {
      return `<p class="chart-empty" role="status">No ${esc(indicator)} observations available for ${esc(byCode(code).name)} in the local snapshot.</p>`;
    }
    const firstYear = observedRows[0].year;
    const lastYear = observedRows[observedRows.length - 1].year;
    const rowsByYear = new Map(allRows.map((row) => [row.year, row]));
    const rows = Array.from({ length: lastYear - firstYear + 1 }, (_, offset) => {
      const year = firstYear + offset;
      return rowsByYear.get(year) || { year, [field]: null };
    });
    const width = 700;
    const height = 280;
    const margin = { top: 22, right: 22, bottom: 42, left: 48 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;
    const x = (index) => margin.left + (index / Math.max(rows.length - 1, 1)) * chartWidth;
    const y = (value) => margin.top + chartHeight - ((value - yMin) / (yMax - yMin)) * chartHeight;
    const yTicks = field === "renewable_share_percent" ? [0, 20, 40, 60] : field === "sst_anomaly_celsius" ? [-1, -0.5, 0, 0.5, 1, 1.5] : [0, 1, 2, 3, 4];
    const xTickIndexes = rows.length > 10 ? [0, Math.floor(rows.length / 2), rows.length - 1] : rows.map((_, index) => index);
    const grid = yTicks.map((tick) => `<line x1="${margin.left}" y1="${y(tick)}" x2="${width - margin.right}" y2="${y(tick)}" class="chart-grid-line"/>${svgText(margin.left - 10, y(tick) + 4, `${tick}`, "axis-label axis-label-end")}`).join("");
    const xLabels = xTickIndexes.map((index) => svgText(x(index), height - 14, rows[index].year, "axis-label axis-label-center")).join("");
    const segments = [];
    let segment = [];
    rows.forEach((row, index) => {
      if (row[field] == null) {
        if (segment.length) segments.push(segment);
        segment = [];
      } else {
        segment.push(`${x(index)},${y(row[field])}`);
      }
    });
    if (segment.length) segments.push(segment);
    const lines = segments.map((points) => `<polyline points="${points.join(" ")}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`).join("");
    const dots = rows.map((row, index) => row[field] == null ? "" : `<circle cx="${x(index)}" cy="${y(row[field])}" r="3.2" fill="${color}"><title>${row.year}: ${fmt(row[field], field === "renewable_share_percent" ? 2 : 1)} ${yUnit}</title></circle>`).join("");
    const tableRows = rows.map((row) => `<tr><th scope="row">${row.year}</th><td>${row[field] == null ? "No observation" : `${fmt(row[field], field === "renewable_share_percent" ? 2 : 1)} ${esc(yUnit)}`}</td></tr>`).join("");
    const missingYears = rows.filter((row) => row[field] == null).map((row) => row.year);
    const missingNotice = missingYears.length
      ? `<p class="chart-gap-note" role="status">${missingYears.length === 1 ? "No observation" : "No observations"} for ${formatYearRanges(missingYears)}; ${missingYears.length === 1 ? "the line is" : "the lines are"} intentionally broken.</p>`
      : "";
    return `<div class="chart-with-data">${missingNotice}<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(byCode(code).name)} ${esc(indicator)} over time"><g>${grid}<line x1="${margin.left}" y1="${margin.top + chartHeight}" x2="${width - margin.right}" y2="${margin.top + chartHeight}" class="axis-line"/>${xLabels}${lines}${dots}</g></svg><details class="accessible-data"><summary>View yearly values as a table</summary><div class="table-wrap"><table><caption>${esc(byCode(code).name)} ${esc(indicator)} by year</caption><thead><tr><th scope="col">Year</th><th scope="col">Value</th></tr></thead><tbody>${tableRows}</tbody></table></div></details></div>`;
  }

  function renderTrends() {
    const code = $("#country-select").value || countries[0].code;
    const country = byCode(code) || countries[0];
    const renewable = rowsFor(code).filter((row) => row.renewable_share_percent !== null);
    const emissions = rowsFor(code).filter((row) => row.ghg_tonnes_per_capita !== null);
    const sst = rowsFor(code).filter((row) => row.sst_anomaly_celsius !== null);
    $("#renewable-chart").innerHTML = lineChart(code, "renewable_share_percent", colors[code], 0, 60, "%");
    $("#emissions-chart").innerHTML = lineChart(code, "ghg_tonnes_per_capita", colors[code], 0, 4, "tonnes per person");
    $("#sst-chart").innerHTML = lineChart(code, "sst_anomaly_celsius", colors[code], -1, 1.5, "°C");
    const caption = (rows, field, unit, digits, suffix = "") => {
      if (!rows.length) return `${country.name}: no ${indicatorLabels[field]} observations are available in the local snapshot.`;
      const start = rows[0];
      const end = rows[rows.length - 1];
      return `${country.name}: ${fmt(start[field], digits)}${unit} in ${start.year} → ${fmt(end[field], digits)}${unit} in ${end.year}${suffix}.`;
    };
    $("#renewable-caption").textContent = caption(renewable, "renewable_share_percent", "%", 2);
    $("#emissions-caption").textContent = caption(emissions, "ghg_tonnes_per_capita", " tonnes", 1);
    $("#sst-caption").textContent = caption(sst, "sst_anomaly_celsius", "°C", 1, ", relative to the 1971–2000 average");
    const overlap = snapshot.find((row) => row.country_code === code);
    $("#trend-summary").textContent = overlap ? `${country.name} in 2022 · ${fmt(overlap.renewable_share_percent, 2)}% renewable · ${fmt(overlap.ghg_tonnes_per_capita, 1)} t/person` : country.name;
    const snapshotDate = window.PACIFIC_METADATA && window.PACIFIC_METADATA.downloaded_on;
    if (snapshotDate && $("#snapshot-date")) $("#snapshot-date").textContent = snapshotDate;
  }

  function renderTable() {
    const rows = snapshot.filter((row) => active.has(row.country_code)).sort((a, b) => b.renewable_share_percent - a.renewable_share_percent);
    $("#comparison-table").innerHTML = rows.length
      ? rows.map((row, index) => `<tr><th scope="row"><span class="rank-name"><span class="rank-number">${index + 1}</span>${esc(row.country)}</span></th><td><span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:${Math.min(row.renewable_share_percent / 55 * 100, 100)}%"></span></span><span class="value-strong">${fmt(row.renewable_share_percent, 2)}%</span></td><td>${fmt(row.ghg_tonnes_per_capita, 1)} t</td><td>${fmt(row.sst_anomaly_celsius, 1)}°C</td></tr>`).join("")
      : '<tr><td colspan="4">No complete 2022 observations are available for the selected countries.</td></tr>';
  }

  function updateTakeaway() {
    const rows = snapshot.filter((row) => active.has(row.country_code));
    if (!rows.length) {
      $("#snapshot-takeaway").textContent = "No complete 2022 comparison is available.";
      $("#snapshot-detail").textContent = "Select a country with complete observations, or open the local CSV to inspect the available years.";
      return;
    }
    const highestRenew = [...rows].sort((a, b) => b.renewable_share_percent - a.renewable_share_percent)[0];
    const lowestGhg = [...rows].sort((a, b) => a.ghg_tonnes_per_capita - b.ghg_tonnes_per_capita)[0];
    const highestGhg = [...rows].sort((a, b) => b.ghg_tonnes_per_capita - a.ghg_tonnes_per_capita)[0];
    $("#snapshot-takeaway").textContent = `${highestRenew.country} has the highest renewable share in this 2022 comparison.`;
    $("#snapshot-detail").textContent = `${fmt(highestRenew.renewable_share_percent, 2)}% of final energy consumption is renewable, while ${lowestGhg.country} records the lowest emissions at ${fmt(lowestGhg.ghg_tonnes_per_capita, 1)} tonnes per person. ${highestGhg.country} is highest on that emissions measure at ${fmt(highestGhg.ghg_tonnes_per_capita, 1)} tonnes. These are descriptive contrasts, not a policy ranking.`;
  }

  function renderEmptyState(message) {
    $("#country-filters").innerHTML = `<p class="chart-empty" role="status">${esc(message)}</p>`;
    $("#scatter-chart").innerHTML = `<p class="chart-empty" role="status">${esc(message)}</p>`;
    $("#country-select").innerHTML = `<option value="">No local data snapshot</option>`;
    $("#country-select").disabled = true;
    $("#trend-summary").textContent = message;
    ["#renewable-chart", "#emissions-chart", "#sst-chart"].forEach((selector) => {
      $(selector).innerHTML = `<p class="chart-empty" role="status">${esc(message)}</p>`;
    });
    $("#comparison-table").innerHTML = `<tr><td colspan="4">${esc(message)}</td></tr>`;
    $("#snapshot-takeaway").textContent = "The local snapshot is unavailable.";
    $("#snapshot-detail").textContent = message;
    const statusElement = $("#snapshot-data-status");
    if (statusElement) statusElement.textContent = message;
  }

  function init() {
    const hasObservation = data.some((row) => [row.ghg_tonnes_per_capita, row.renewable_share_percent, row.sst_anomaly_celsius].some((value) => value !== null));
    if (!data.length || !hasObservation) {
      renderEmptyState(data.length ? "No usable observations found in the local snapshot. Open the CSV or run the fetch script." : "No local data snapshot found. Open the CSV or run the fetch script.");
      return;
    }
    renderFilters();
    renderScatter();
    renderTable();
    updateTakeaway();
    const select = $("#country-select");
    select.innerHTML = countries.map((country) => `<option value="${country.code}">${country.name}</option>`).join("");
    select.addEventListener("change", renderTrends);
    renderTrends();
  }

  init();
})();
