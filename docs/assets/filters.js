// The filter bar above the runs of page.html. The state lives in the URL's query string, so a filtered view can be
// shared: ?vendor=anthropic,openai &effort=high &model=a/b,c/d &verified=1 &failed=hide. The filtering itself is
// filterRuns() in runs.js; the grid and the table both draw whatever it returns.

import { el, qsList, qs, setQuery } from "./dom.js";
import { effortIndex, vendorOf, vendorName, vendorOptions, modelParts } from "./runs.js";

export function readFilters() {
  return { vendors: qsList("vendor"), efforts: qsList("effort"), models: qsList("model"), verified: qs("verified") === "1", hideFailed: qs("failed") === "hide" };
}

export function hasFilters(f) {
  return Boolean(f.vendors.length || f.efforts.length || f.models.length || f.verified || f.hideFailed);
}

const toggled = (list, value) => (list.includes(value) ? list.filter((x) => x !== value) : [...list, value]);

// Fills `box` with one chip per vendor, effort and model of `runs`, plus the two toggles and a clear button. A click
// updates `filters` in place, writes the URL and calls `onChange`. The controls are built once and only their state
// is synced, so keyboard focus stays where it was.
export function renderFilterBar(box, runs, filters, onChange) {
  const vendors = [...new Set(runs.map((r) => vendorOf(r.model)))].sort();
  const efforts = [...new Set(runs.map((r) => r.effort))].sort((a, b) => effortIndex(a) - effortIndex(b) || String(a).localeCompare(String(b)));
  const models = [...new Set(runs.map((r) => r.model))].sort();
  const syncs = [];

  const update = (change) => {
    Object.assign(filters, change);
    setQuery({ vendor: filters.vendors.join(","), effort: filters.efforts.join(","), model: filters.models.join(","), verified: filters.verified, failed: filters.hideFailed ? "hide" : null });
    syncs.forEach((sync) => sync());
    onChange();
  };
  // A chip for one value of a list filter (`key` = vendors / efforts / models).
  const chip = (key, value, text, extra = {}) => {
    const node = el("button", { class: "chip filter-chip", text, style: extra.style, attrs: { type: "button", ...extra.attrs }, on: { click: () => update({ [key]: toggled(filters[key], value) }) } });
    syncs.push(() => {
      const on = filters[key].includes(value);
      node.classList.toggle("chip-active", on);
      node.setAttribute("aria-pressed", String(on));
    });
    return node;
  };
  const toggle = (key, text) => {
    const input = el("input", { attrs: { type: "checkbox" }, on: { change: () => update({ [key]: input.checked }) } });
    syncs.push(() => (input.checked = filters[key]));
    return el("label", { class: "filter-toggle" }, [input, text]);
  };
  const group = (label, chips) => (chips.length > 1 ? el("div", { class: "filter-group" }, [el("span", { class: "filter-label", text: label }), ...chips]) : null);
  const clear = el("button", { class: "filter-clear", text: "Clear filters", attrs: { type: "button" }, on: { click: () => update({ vendors: [], efforts: [], models: [], verified: false, hideFailed: false }) } });
  syncs.push(() => (clear.hidden = !hasFilters(filters)));

  const sample = (vendor) => runs.find((r) => vendorOf(r.model) === vendor).model;
  box.replaceChildren(...[
    group("Vendor", vendors.map((v) => chip("vendors", v, vendorName(v), vendorOptions(sample(v))))),
    group("Effort", efforts.map((e) => chip("efforts", e, e ?? "–"))),
    group("Model", models.map((m) => chip("models", m, modelParts(m).short, { attrs: { title: m } }))),
    el("div", { class: "filter-group" }, [toggle("verified", "Verified only"), toggle("hideFailed", "Hide failed"), clear]),
  ].filter(Boolean));
  box.hidden = runs.length < 2;
  syncs.forEach((sync) => sync());
}
