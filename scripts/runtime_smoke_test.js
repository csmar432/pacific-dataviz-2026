#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const ROOT = require("node:path").resolve(__dirname, "..");
const dataSource = fs.readFileSync(`${ROOT}/src/data.js`, "utf8");
const appSource = fs.readFileSync(`${ROOT}/src/app.js`, "utf8");

class Element {
  constructor(id) {
    this.id = id;
    this.html = "";
    this.textContent = "";
    this.value = "";
    this.dataset = {};
    this.buttons = [];
    this.attributes = {};
    this.listeners = new Map();
  }

  set innerHTML(value) {
    this.html = String(value);
    if (this.id === "country-filters") {
      this.buttons = [...this.html.matchAll(/<button[^>]+data-code="([A-Z]{2})"/g)].map((match) => {
        const button = new Element("country-filter");
        button.dataset.code = match[1];
        return button;
      });
    }
  }

  get innerHTML() {
    return this.html;
  }

  querySelectorAll(selector) {
    return selector === "button" ? this.buttons : [];
  }

  addEventListener(type, handler) {
    this.listeners.set(type, handler);
  }

  dispatchEvent(event) {
    this.listeners.get(event.type)?.(event);
  }

  click() {
    this.dispatchEvent({ type: "click" });
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  getAttribute(name) {
    return this.attributes[name];
  }
}

function createDocument() {
  const ids = [
    "country-filters", "scatter-chart", "renewable-chart", "emissions-chart", "sst-chart",
    "country-select", "renewable-caption", "emissions-caption", "sst-caption", "trend-summary",
    "snapshot-date", "comparison-table", "snapshot-takeaway", "snapshot-detail",
    "snapshot-data-status",
  ];
  const elements = new Map(ids.map((id) => [`#${id}`, new Element(id)]));
  return { querySelector: (selector) => elements.get(selector), elements };
}

function run(rows, metadata) {
  const document = createDocument();
  const sandbox = { window: { PACIFIC_DATA: rows, PACIFIC_METADATA: metadata }, document, console };
  vm.runInNewContext(appSource, sandbox, { filename: "src/app.js" });
  return document;
}

const dataSandbox = { window: {}, console };
vm.runInNewContext(dataSource, dataSandbox, { filename: "src/data.js" });
const rows = dataSandbox.window.PACIFIC_DATA;
const metadata = dataSandbox.window.PACIFIC_METADATA;
const normal = run(rows, metadata);
assert.match(normal.elements.get("#scatter-chart").innerHTML, /<svg/);
assert.match(normal.elements.get("#sst-chart").innerHTML, /View yearly values as a table/);
assert.match(normal.elements.get("#comparison-table").innerHTML, /<th scope="row">/);
assert.equal(normal.elements.get("#country-filters").buttons.length, 7);
assert.match(normal.elements.get("#snapshot-date").textContent, /^20\d\d-\d\d-\d\d$/);

const filters = normal.elements.get("#country-filters").buttons;
filters[0].click();
assert.equal(filters[0].getAttribute("aria-pressed"), "false");
assert.doesNotMatch(normal.elements.get("#comparison-table").innerHTML, /Fiji/);
const select = normal.elements.get("#country-select");
select.value = "KI";
select.dispatchEvent({ type: "change" });
assert.match(normal.elements.get("#trend-summary").textContent, /Kiribati in 2022/);

const missingRenewable = rows.map((row) => {
  if (row.country_code !== "FJ") return row;
  const copy = { ...row };
  delete copy.renewable_share_percent;
  return copy;
});
const partial = run(missingRenewable, metadata);
assert.match(partial.elements.get("#renewable-chart").innerHTML, /No renewable energy share observations/);
assert.match(partial.elements.get("#renewable-caption").textContent, /no renewable energy share observations/);

const middleMissing = rows.map((row) => {
  if (row.country_code !== "FJ" || ![2015, 2017].includes(row.year)) return row;
  const copy = { ...row };
  delete copy.renewable_share_percent;
  return copy;
});
const gap = run(middleMissing, metadata);
assert.equal((gap.elements.get("#renewable-chart").innerHTML.match(/<polyline/g) || []).length, 3);
assert.match(gap.elements.get("#renewable-chart").innerHTML, /No observations for 2015, 2017/);

const nonFinite = rows.map((row) => {
  if (row.country_code !== "FJ" || row.year !== 2022) return row;
  return { ...row, ghg_tonnes_per_capita: "NaN" };
});
const invalid = run(nonFinite, metadata);
assert.doesNotMatch(invalid.elements.get("#scatter-chart").innerHTML, /NaN/);
assert.doesNotMatch(invalid.elements.get("#comparison-table").innerHTML, /NaN/);
assert.match(invalid.elements.get("#snapshot-data-status").textContent, /6 of 7/);

const empty = run([], metadata);
assert.match(empty.elements.get("#country-filters").innerHTML, /No local data snapshot found/);
assert.match(empty.elements.get("#renewable-chart").innerHTML, /No local data snapshot found/);
assert.match(empty.elements.get("#comparison-table").innerHTML, /No local data snapshot found/);
assert.equal(empty.elements.get("#country-select").disabled, true);

const unusable = run(rows.map((row) => ({ ...row, ghg_tonnes_per_capita: "Infinity", renewable_share_percent: "NaN", sst_anomaly_celsius: "-Infinity" })), metadata);
assert.match(unusable.elements.get("#country-filters").innerHTML, /No usable observations found/);
assert.match(unusable.elements.get("#scatter-chart").innerHTML, /No usable observations found/);
assert.match(unusable.elements.get("#emissions-chart").innerHTML, /No usable observations found/);

console.log(JSON.stringify({ rows: rows.length, countries: 7, emptySeriesHandled: true, gapsRendered: true, accessibleTables: true, interactiveEvents: true }));
