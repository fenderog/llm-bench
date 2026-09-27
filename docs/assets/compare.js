import { qsList, qs, el, getJSON, fmtDuration, fmtCost, fmtNum, showMessage, runDir, buildGameFrame } from "./common.js";

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
  } catch (err) {
    showMessage(main, `Could not load comparison: ${err.message}`, "error");
  }
}

function column(r) {
  const base = runDir(slug, r.id);
  const m = r.metrics || {};
  return el("div", { class: "compare-col" }, [
    el("h3", {}, [el("a", { text: `${r.model} · ${r.effort}`, attrs: { href: `run.html?p=${encodeURIComponent(slug)}&r=${encodeURIComponent(r.id)}` } })]),
    el("div", { class: "muted compare-metrics", text: `${fmtDuration(m.duration_ms)} · ${fmtNum(m.tokens_total)} tokens · ${fmtCost(m.cost_usd)}` }),
    r.game ? buildGameFrame(base + r.game.entry, r.thumb ? base + r.thumb : null) : el("p", { class: "muted", text: "No game recorded." }),
  ]);
}
