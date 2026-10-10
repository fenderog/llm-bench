// Run cards: one run's model, rank, effort, metrics and output as a card. page.html's Grid view and compare.html
// both draw their runs through renderRunGrid(), so there is one implementation.

import { el } from "./dom.js";
import { fmtDuration, fmtCost, fmtNum } from "./fmt.js";
import { runDir, harnessLabel, stateBadge, effortPill, modelLabel, runUrl, LOWER_IS_BETTER, isComplete, byRankThenModel, rankChip, vendorOptions, groupByVendor, bestSets, playUrl } from "./runs.js";
import { outputBadge, outputOk, renderOutput } from "./output.js";
import { selectBox } from "./selection.js";

const FEW = 4; // with `fillFew`, up to this many runs are equal columns filling the page

// Draws `runs` into `container`: ranked runs first, then by model. From `groupFrom` runs up, and when they span
// several vendors, there is one labelled grid per vendor; fewer are one flat grid. The ★ best values compare all
// of `runs`. `selection` adds a checkbox to every card, `dense` makes narrower cards, `fillFew` stretches 2-4 runs
// across the page.
export function renderRunGrid(container, slug, runs, { groupFrom, selection = null, dense = false, fillFew = false }) {
  const sorted = [...runs].sort(byRankThenModel);
  const best = bestSets(sorted);
  const grid = (list, extra) => el("div", { class: `compare-columns${dense ? " is-dense" : ""}${extra ? " is-few" : ""}`, style: extra }, list.map((r) => runCard(slug, r, best, selection)));
  const groups = groupByVendor(sorted);
  if (sorted.length < groupFrom || groups.length < 2) {
    const few = fillFew && sorted.length > 1 && sorted.length <= FEW;
    container.replaceChildren(grid(sorted, few ? { "--cols": String(sorted.length), "--cols-mid": String(Math.min(sorted.length, 2)) } : null));
    return;
  }
  container.replaceChildren(...groups.map((g) =>
    el("section", { class: "vendor-group", ...vendorOptions(g.runs[0].model), attrs: { ...vendorOptions(g.runs[0].model).attrs, "aria-label": g.name } }, [
      el("h2", { class: "vendor-head" }, [
        el("span", { class: "vendor-name", text: g.name }),
        el("span", { class: "vendor-count", text: `${g.runs.length} run${g.runs.length === 1 ? "" : "s"}` }),
      ]),
      grid(g.runs),
    ])
  ));
}

// Starts every game at once by pressing each card's play overlay. Each sandboxed game has its own opaque origin,
// so each downloads and runs its own copy of the engine. The button hides when there is nothing to play (media
// pages, or `container` hidden) and disables once everything runs. Returns the function to call after a redraw.
export function setupPlayAll(btn, container) {
  const update = () => {
    btn.hidden = container.hidden || !container.querySelector(".game-frame");
    btn.disabled = !container.querySelector("[data-play]");
  };
  btn.addEventListener("click", () => {
    for (const overlay of container.querySelectorAll("[data-play]")) overlay.click();
    update();
  });
  container.addEventListener("click", () => setTimeout(update)); // a game started from its own overlay
  update();
  return update;
}

// "pi 0.87.1 · 1m 5s · 29,343 tokens · $0.0037", with the best values among the shown runs starred.
function metricsLine(r, best) {
  const m = r.metrics || {};
  const line = el("div", { class: "compare-metrics" }, [el("span", { class: "harness-label", text: harnessLabel(r) })]);
  const part = (key, value, suffix) => {
    const isBest = best[key] && best[key].has(r.id);
    line.append(
      el("span", { class: "sep", text: "·" }),
      el("span", { class: isBest ? "is-best" : null, attrs: isBest ? { title: LOWER_IS_BETTER[key] } : {} }, [el("b", { text: `${isBest ? "★ " : ""}${value}` }), suffix]),
    );
  };
  part("duration_ms", fmtDuration(m.duration_ms), "");
  part("tokens_total", fmtNum(m.tokens_total), " tokens");
  part("cost_usd", fmtCost(m.cost_usd), "");
  return line;
}

export function runCard(slug, r, best, selection = null) {
  const base = runDir(slug, r.id);
  const sb = stateBadge(r) || outputBadge(r);
  // ↗ opens the run alone in a popup window, through the sandboxed play.html (never the raw entry URL)
  const url = playUrl(slug, r.id);
  const pop = outputOk(r) ? el("a", {
    class: "popout", text: "↗",
    attrs: { href: url, target: "_blank", rel: "noopener", title: "Open in its own window", "aria-label": `Open ${r.model} ${r.effort} in its own window` },
    on: { click: (e) => { e.preventDefault(); window.open(url, "_blank", "popup,noopener,width=1280,height=800"); } },
  }) : null;
  const heading = [
    el("span", { class: "card-title" }, [selection ? selectBox(r, selection) : null, el("a", { attrs: { href: runUrl(slug, r.id) } }, [modelLabel(r.model)])]),
    el("span", { class: "card-tags" }, [rankChip(r.rank), r.rank != null ? " " : null, effortPill(r.effort), sb ? " " : null, sb, pop ? " " : null, pop]),
  ];
  const body = el("div", { class: "compare-body" });
  if (r.error) body.append(el("p", { class: "run-error", text: r.error }));
  body.append(...renderOutput(r, base, { compact: true, href: runUrl(slug, r.id) }));
  return el("div", { class: isComplete(r) ? "compare-col" : "compare-col is-failed", ...vendorOptions(r.model) }, [el("h3", {}, heading), metricsLine(r, best), body]);
}
