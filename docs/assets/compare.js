import { qsList, qs, el, getJSON, fmtDuration, fmtCost, fmtNum, showMessage, runDir, buildGameFrame, harnessLabel, stateBadge, mediaGallery } from "./common.js";

// compare.html?p=<slug> shows every run of the page; &r=<id>,<id> limits it to those runs.
const slug = qs("p");
const ids = qsList("r");
const main = document.getElementById("main");
const columnsEl = document.getElementById("columns");

if (!slug) {
  showMessage(main, "Missing ?p=<slug> in the URL.", "error");
} else {
  try {
    const [page, runs] = await Promise.all([
      getJSON(`data/${slug}/page.json`).catch(() => null),
      getJSON(`data/${slug}/results.json`),
    ]);
    if (page) {
      const link = document.getElementById("page-link");
      link.textContent = page.title;
      link.href = `page.html?p=${encodeURIComponent(slug)}`;
      document.getElementById("title").textContent = `Compare – ${page.title}`;
    }
    const shown = ids.length ? runs.filter((r) => ids.includes(r.id)) : runs;
    if (!shown.length) showMessage(main, "No matching runs to compare.", "error");
    for (const r of shown) columnsEl.append(column(r));
    setupPlayAll();
  } catch (err) {
    showMessage(main, `Could not load comparison: ${err.message}`, "error");
  }
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

function column(r) {
  const base = runDir(slug, r.id);
  const m = r.metrics || {};
  const sb = stateBadge(r);
  const heading = [el("a", { text: `${r.model} · ${r.effort}`, attrs: { href: `run.html?p=${encodeURIComponent(slug)}&r=${encodeURIComponent(r.id)}` } })];
  if (sb) heading.push(" ", sb);
  const parts = [
    el("h3", {}, heading),
    el("div", { class: "muted compare-metrics", text: `${harnessLabel(r)} · ${fmtDuration(m.duration_ms)} · ${fmtNum(m.tokens_total)} tokens · ${fmtCost(m.cost_usd)}` }),
  ];
  if (r.error) parts.push(el("p", { class: "run-error", text: r.error }));
  if (r.media) parts.push(mediaGallery(r, base));
  else if (r.game) parts.push(buildGameFrame(base + r.game.entry, r.thumb ? base + r.thumb : null));
  else parts.push(el("p", { class: "muted", text: r.kind === "media" ? "No output files recorded." : "No game recorded." }));
  return el("div", { class: "compare-col" }, parts);
}
