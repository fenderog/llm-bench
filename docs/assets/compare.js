import {
  qsList, qs, el, loadPage, fmtDuration, fmtCost, fmtNum, showMessage, runDir, buildGameFrame, harnessLabel, stateBadge, mediaGallery,
  effortPill, modelLabel, runUrl, byModelThenEffort, rankBy, LOWER_IS_BETTER, isComplete, byRankThenModel, rankChip, vendorOptions, groupByVendor,
  playUrl,
} from "./common.js";

// compare.html?p=<slug> shows every run of the page; &r=<id>,<id> limits it to those runs.
const slug = qs("p");
const ids = qsList("r");
const main = document.getElementById("main");
const columnsEl = document.getElementById("columns");

const page = await loadPage(slug);
if (page) {
  const runs = page.runs;
  const link = document.getElementById("page-link");
  link.textContent = page.title;
  link.href = `page.html?p=${encodeURIComponent(slug)}`;
  document.title = `Compare – ${page.title} – llm-bench`;
  document.getElementById("title").textContent = page.title;
  if (page.prompt) {
    const p = document.getElementById("compare-prompt");
    p.textContent = page.prompt;
    p.hidden = false;
  }
  const shown = (ids.length ? runs.filter((r) => ids.includes(r.id)) : runs).sort(byRankThenModel); // your ranking first, when there is one
  document.getElementById("compare-count").textContent = `${shown.length} run${shown.length === 1 ? "" : "s"} side by side · ★ best among them`;
  if (!shown.length) showMessage(columnsEl, "No matching runs to compare.", "error");
  const best = {};
  for (const key of Object.keys(LOWER_IS_BETTER)) {
    const ranks = rankBy(shown, key);
    best[key] = new Set([...ranks].filter(([, rank]) => rank === 1).map(([id]) => id));
  }
  for (const g of groupByVendor(shown)) { // one labelled grid per vendor; the stars above still compare all shown runs
    const grid = el("div", { class: "compare-columns" }, g.runs.map((r) => column(r, best)));
    columnsEl.append(
      el("section", { class: "vendor-group", ...vendorOptions(g.runs[0].model), attrs: { ...vendorOptions(g.runs[0].model).attrs, "aria-label": g.name } }, [
        el("h2", { class: "vendor-head" }, [
          el("span", { class: "vendor-name", text: g.name }),
          el("span", { class: "vendor-count", text: `${g.runs.length} run${g.runs.length === 1 ? "" : "s"}` }),
        ]),
        grid,
      ])
    );
  }
  setupPlayAll();
}

// Starts every game at once by pressing each column's play overlay. Each sandboxed game
// has its own opaque origin, so each downloads and runs its own copy of the engine.
function setupPlayAll() {
  const btn = document.getElementById("play-all");
  btn.hidden = !columnsEl.querySelector(".game-frame"); // media pages have nothing to play
  const update = () => (btn.disabled = !columnsEl.querySelector("[data-play]"));
  btn.addEventListener("click", () => {
    for (const overlay of columnsEl.querySelectorAll("[data-play]")) overlay.click();
    update();
  });
  columnsEl.addEventListener("click", () => setTimeout(update)); // a game started from its own overlay
  update();
}

// "pi 0.87.1 · 1m 5s · 29,343 tokens · $0.0037", with the best values among the shown runs starred.
function metricsLine(r, best) {
  const m = r.metrics || {};
  const line = el("div", { class: "compare-metrics" }, [el("span", { text: harnessLabel(r) })]);
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

function column(r, best) {
  const base = runDir(slug, r.id);
  const sb = stateBadge(r);
  // ↗ opens the run alone in a popup window, through the sandboxed play.html (never the raw entry URL)
  const url = playUrl(slug, r.id);
  const pop = r.game || r.media ? el("a", {
    class: "popout", text: "↗",
    attrs: { href: url, target: "_blank", rel: "noopener", title: "Open in its own window", "aria-label": `Open ${r.model} ${r.effort} in its own window` },
    on: { click: (e) => { e.preventDefault(); window.open(url, "_blank", "popup,noopener,width=1280,height=800"); } },
  }) : null;
  const heading = [el("a", { attrs: { href: runUrl(slug, r.id) } }, [modelLabel(r.model)]), el("span", {}, [rankChip(r.rank), r.rank != null ? " " : null, effortPill(r.effort), sb ? " " : null, sb, pop ? " " : null, pop])];
  const body = el("div", { class: "compare-body" });
  if (r.error) body.append(el("p", { class: "run-error", text: r.error }));
  if (r.media) body.append(mediaGallery(r, base));
  else if (r.game) body.append(buildGameFrame(base + r.game.entry, r.thumb ? base + r.thumb : null));
  else body.append(el("p", { class: "msg", text: r.kind === "media" ? "No output files recorded." : "No game recorded." }));
  return el("div", { class: isComplete(r) ? "compare-col" : "compare-col is-failed", ...vendorOptions(r.model) }, [el("h3", {}, heading), metricsLine(r, best), body]);
}
