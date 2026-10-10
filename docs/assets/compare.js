import { qsList, qs, loadPage, showMessage } from "./dom.js";
import { byRankThenModel } from "./runs.js";
import { renderRunGrid, setupPlayAll } from "./card.js";

// compare.html?p=<slug> shows every run of the page; &r=<id>,<id> limits it to those runs.
// Up to 4 runs are equal columns across the page; more are grouped by vendor.
const GROUP_FROM = 5;
const slug = qs("p");
const ids = qsList("r");
const columnsEl = document.getElementById("columns");

const page = await loadPage(slug);
if (page) {
  const link = document.getElementById("page-link");
  link.textContent = page.title;
  link.href = `page.html?p=${encodeURIComponent(slug)}`;
  document.title = `Compare – ${page.title} – art-crit`;
  document.getElementById("title").textContent = page.title;
  if (page.prompt) {
    const p = document.getElementById("compare-prompt");
    p.textContent = page.prompt;
    p.hidden = false;
  }
  const shown = (ids.length ? page.runs.filter((r) => ids.includes(r.id)) : page.runs).sort(byRankThenModel); // your ranking first, when there is one
  document.getElementById("compare-count").textContent = `${shown.length} run${shown.length === 1 ? "" : "s"} side by side · ★ best among them`;
  if (!shown.length) showMessage(columnsEl, "No matching runs to compare.", "error");
  else renderRunGrid(columnsEl, slug, shown, { groupFrom: GROUP_FROM, fillFew: true });
  setupPlayAll(document.getElementById("play-all"), columnsEl);
}
