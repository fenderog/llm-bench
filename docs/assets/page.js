import { qs, el, loadPage, showMessage, badge, setQuery } from "./dom.js";
import { fmtNum, fmtDuration, fmtCost, fmtDate, fmtDateShort } from "./fmt.js";
import { runDir, harnessLabel, stateBadge, effortPill, effortIndex, modelLabel, modelParts, runUrl, byModelThenEffort, rankBy, bestSets, filterRuns, LOWER_IS_BETTER, isComplete, rankLabel, canEditRanks, saveRanks, vendorOptions, playUrl } from "./runs.js";
import { COLUMN_HELP, rowHelp } from "./help.js";
import { outputBadge, outputVerified, isPlayable, renderOutput, kindUi, mediaCount } from "./output.js";
import { renderRunGrid, setupPlayAll } from "./card.js";
import { createSelection, selectBox } from "./selection.js";
import { readFilters, renderFilterBar } from "./filters.js";

const slug = qs("p");
const main = document.getElementById("main");
const VIEW_KEY = "art-crit.view"; // "grid" (default) or "table", remembered in localStorage; ?view= wins
const GROUP_FROM = 15; // fewer runs than this are one flat grid; more are grouped by vendor

function initialView() {
  const views = ["grid", "table"];
  if (views.includes(qs("view"))) return qs("view");
  try {
    const saved = localStorage.getItem(VIEW_KEY);
    if (views.includes(saved)) return saved;
  } catch {} // storage blocked
  return "grid";
}

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

const COLUMNS = [
  { key: "rank", label: "Rank", get: (r) => r.rank ?? null, num: false },
  { key: "model", label: "Model", get: (r) => r.model, num: false },
  { key: "effort", label: "Effort", get: (r) => r.effort, sortVal: (r) => effortIndex(r.effort), num: false },
  { key: "harness", label: "Harness", get: (r) => harnessLabel(r), num: false },
  { key: "started_at", label: "Run at", get: (r) => r.started_at ?? null, num: false },
  { key: "verified", label: "Verified", get: (r) => outputVerified(r), num: false },
  { key: "duration_ms", label: "Duration", get: (r) => r.metrics.duration_ms, num: true, fmt: fmtDuration },
  { key: "tokens_total", label: "Tokens", get: (r) => r.metrics.tokens_total, num: true, fmt: fmtNum },
  { key: "tokens_reasoning", label: "Reasoning", get: (r) => r.metrics.tokens_reasoning, num: true, fmt: fmtNum },
  { key: "cost_usd", label: "Cost", get: (r) => r.metrics.cost_usd, num: true, fmt: fmtCost },
  { key: "tool_calls", label: "Tool calls", get: (r) => r.metrics.tool_calls, num: true, fmt: fmtNum },
];

const page = await loadPage(slug);
if (page) render(page, page.runs, await canEditRanks());

function render(page, runs, editable) {
  document.title = `${page.title} – art-crit`;
  document.getElementById("title").textContent = page.title;
  if (page.prompt) {
    document.getElementById("prompt").textContent = page.prompt;
    document.getElementById("prompt-box").hidden = false;
  }
  if (page.final_prompt) {
    document.getElementById("final-prompt").textContent = page.final_prompt;
    document.getElementById("final-prompt-box").hidden = false;
  }
  const isMedia = page.kind === "media";
  renderMeta(page, runs);
  renderHighlights(runs);

  if (isMedia) main.classList.add("media-page");

  // What is shown: the runs left by the filter bar, as a grid of cards (default) or the table. Both views share the
  // filters (in the URL) and the ticked runs (selection.js).
  const filters = readFilters();
  const selection = createSelection(slug, runs.map((r) => r.id));
  const grid = document.getElementById("grid");
  const tableWrap = document.getElementById("table-wrap");
  const updatePlayAll = setupPlayAll(document.getElementById("play-all"), grid);
  let view = initialView();
  let shown = runs;
  selection.onChange = syncSelection;
  renderFilterBar(document.getElementById("filters"), runs, filters, draw);
  for (const btn of document.querySelectorAll("[data-view]")) {
    btn.addEventListener("click", () => {
      view = btn.dataset.view;
      try { localStorage.setItem(VIEW_KEY, view); } catch {}
      setQuery({ view });
      draw();
    });
  }
  document.getElementById("select-clear").addEventListener("click", () => selection.clear());

  function draw() {
    shown = filterRuns(runs, filters);
    document.getElementById("runs-count").textContent = shown.length === runs.length ? plural(runs.length, "run") : `${shown.length} of ${plural(runs.length, "run")}`;
    for (const btn of document.querySelectorAll("[data-view]")) btn.setAttribute("aria-pressed", String(btn.dataset.view === view));
    const empty = !shown.length;
    grid.hidden = view !== "grid" && !empty;
    tableWrap.hidden = view !== "table" || empty;
    if (empty) showMessage(grid, "No runs match the filters.");
    else if (view === "grid") renderRunGrid(grid, slug, shown, { groupFrom: GROUP_FROM, selection, dense: true });
    else drawTable();
    updatePlayAll();
  }

  // The "N selected · Compare · Clear" bar, and every checkbox on screen.
  function syncSelection() {
    const ids = selection.ids;
    document.getElementById("select-bar").hidden = !ids.length;
    document.getElementById("select-count").textContent = `${ids.length} selected`;
    document.getElementById("compare-selected").href = `compare.html?p=${encodeURIComponent(slug)}&r=${ids.map(encodeURIComponent).join(",")}`;
    for (const box of document.querySelectorAll("input.run-select")) box.checked = selection.has(box.dataset.id);
  }

  // Default order: your ranking when there is one; otherwise by model, then effort low → high,
  // so effort levels of one model read as a sequence.
  let sortKey = runs.some((r) => r.rank != null) ? "rank" : "model";
  if (editable) {
    main.classList.add("can-rank");
    document.getElementById("runs-count").after(el("span", { class: "rank-status", attrs: { id: "rank-status", role: "status" }, text: "ranking: saved locally, publish to share" }));
  }
  let sortDir = 1;
  const table = document.getElementById("runs-table");
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");

  const headRow = el("tr", {}, [
    el("th", { attrs: { "data-help": rowHelp(isMedia).expand } }),
    el("th", { attrs: { "data-key": "thumb", "data-help": rowHelp(isMedia).thumb } }),
    ...COLUMNS.map((c) =>
      el("th", { text: c.label, class: c.num ? "has-help is-num" : "has-help", attrs: { "data-key": c.key, "data-help": `${COLUMN_HELP[c.key]}\n\nClick to sort.` }, on: { click: () => sortBy(c.key) } })
    ),
  ]);
  thead.append(headRow);
  addHelpTooltips(headRow.querySelectorAll("th[data-help]"));

  function sortBy(key) {
    sortDir = key === sortKey ? -sortDir : 1;
    sortKey = key;
    drawTable();
  }

  function drawTable() {
    for (const th of headRow.querySelectorAll("th[data-key]")) {
      th.removeAttribute("aria-sort");
      if (th.dataset.key === sortKey) th.setAttribute("aria-sort", sortDir === 1 ? "ascending" : "descending");
    }
    const col = COLUMNS.find((c) => c.key === sortKey);
    const val = col.sortVal || col.get;
    const best = bestSets(shown); // the stars compare the runs on screen
    const rows = [...shown].sort((a, b) => {
      const va = val(a);
      const vb = val(b);
      if (va == null && vb == null) return byModelThenEffort(a, b);
      if (va == null) return 1;
      if (vb == null) return -1;
      if (va < vb) return -1 * sortDir;
      if (va > vb) return 1 * sortDir;
      return byModelThenEffort(a, b);
    });

    const maxes = {};
    for (const c of COLUMNS) if (c.num) maxes[c.key] = Math.max(1, ...shown.map((r) => c.get(r) || 0));

    tbody.replaceChildren();
    for (const r of rows) {
      const url = runUrl(slug, r.id);
      const thumb = r.thumb
        ? el("a", { attrs: { href: url, "aria-label": "Open run" } }, [el("img", { class: "row-thumb", attrs: { src: runDir(slug, r.id) + r.thumb, alt: "", loading: "lazy" } })])
        : el("span", { class: "thumb-none", text: "–" });
      const files = r.output?.kind === "media" ? (r.output.items || []).length : 0; // "×3" when a media run made several
      const tds = [
        el("td", { class: "select-cell" }, [selectBox(r, selection), el("span", { class: "caret", text: "▶" })]),
        el("td", { class: "thumb-cell", attrs: { "data-col": "thumb" } }, [el("div", { class: "thumb-box" }, [thumb, files > 1 ? el("span", { class: "media-count", text: `×${files}`, attrs: { title: mediaCount(r.output.items) } }) : null])]),
      ];
      for (const c of COLUMNS) {
        const v = c.get(r);
        const attrs = { "data-col": c.key, "data-label": c.label };
        if (c.key === "rank") {
          tds.push(el("td", { class: "rank-cell", attrs }, [editable ? rankPicker(r) : el("span", { class: v == null ? "muted" : "rank", text: rankLabel(v) ?? "–" })]));
        } else if (c.key === "model") {
          tds.push(el("td", { attrs }, [el("a", { attrs: { href: url } }, [modelLabel(v)])]));
        } else if (c.key === "effort") {
          tds.push(el("td", { attrs }, [effortPill(v)]));
        } else if (c.key === "harness") {
          const h = r.harness;
          tds.push(el("td", { class: "harness-cell", attrs }, [
            h && h.name
              ? el("span", { class: "harness" }, [el("span", { text: h.name }), h.version ? el("span", { class: "harness-version", text: h.version }) : null])
              : "–",
          ]));
        } else if (c.key === "started_at") {
          tds.push(el("td", { class: "started-cell", attrs: { ...attrs, title: fmtDate(v) } }, [fmtDateShort(v)]));
        } else if (c.key === "verified") {
          const sb = stateBadge(r) || outputBadge(r);
          tds.push(el("td", { attrs }, [sb || (v === true ? badge("✓", "good") : v === false ? badge("✗", "bad") : el("span", { class: "muted", text: "–" }))]));
        } else if (c.num) {
          const pct = Math.max(0, Math.min(100, ((v || 0) / maxes[c.key]) * 100));
          const isBest = best[c.key] && best[c.key].has(r.id);
          if (isBest) attrs.title = LOWER_IS_BETTER[c.key];
          tds.push(
            el("td", { class: isBest ? "is-num is-best" : "is-num", attrs }, [
              el("div", { class: "bar-cell" }, [
                el("span", { class: "val", text: c.fmt ? c.fmt(v) : v ?? "–" }),
                el("span", { class: "track" }, [el("span", { class: "bar", style: { width: `${pct}%` } })]),
              ]),
            ])
          );
        } else {
          tds.push(el("td", { text: v ?? "–", attrs }));
        }
      }
      const tr = el("tr", { class: isComplete(r) ? "run-row" : "run-row is-failed", ...vendorOptions(r.model), attrs: { ...vendorOptions(r.model).attrs, tabindex: "0", "aria-expanded": "false" } }, tds);
      const toggle = () => {
        const open = tr.getAttribute("aria-expanded") === "true";
        tr.setAttribute("aria-expanded", String(!open));
        if (open) tr.nextElementSibling.remove(); // removing the iframe stops the game
        else tr.after(detailRow(r, url));
      };
      tr.addEventListener("click", (e) => {
        if (!e.target.closest("a, button, input, select")) toggle();
      });
      tr.addEventListener("keydown", (e) => {
        if (e.target === tr && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          toggle();
        }
      });
      tbody.append(tr);
    }
  }

  // Local ranking: one select per run (– or 1…N, ties allowed). Every change saves the whole page's
  // ranking through `art-crit serve`, which rewrites ranking.json and page.json.
  function rankPicker(r) {
    const select = el("select", { class: "rank-select", attrs: { "aria-label": `Rank for ${r.model} ${r.effort}` } }, [
      el("option", { text: "–", attrs: { value: "" } }),
      ...runs.map((_, i) => el("option", { text: rankLabel(i + 1), attrs: { value: String(i + 1) } })),
    ]);
    select.value = r.rank == null ? "" : String(r.rank);
    select.addEventListener("click", (e) => e.stopPropagation()); // don't expand the row
    select.addEventListener("change", async () => {
      const previous = r.rank ?? null;
      r.rank = select.value ? Number(select.value) : null;
      const status = document.getElementById("rank-status");
      status.textContent = "saving…";
      try {
        await saveRanks(slug, Object.fromEntries(runs.map((x) => [x.id, x.rank ?? null])));
        status.textContent = "saved · publish to share";
        status.classList.remove("is-error");
      } catch (err) {
        r.rank = previous;
        select.value = previous == null ? "" : String(previous);
        status.textContent = `not saved: ${err.message}`;
        status.classList.add("is-error");
      }
    });
    return select;
  }

  // Expanded row: the game boots right away (the row click is the explicit play action).
  function detailRow(r, url) {
    const links = el("div", { class: "game-links" }, [
      el("a", { text: "Open run page →", attrs: { href: url } }),
    ]);
    const errorLine = r.error ? [el("p", { class: "run-error", text: r.error })] : [];
    if (isPlayable(r)) links.append(el("a", { text: "Open full screen ↗", attrs: { href: playUrl(slug, r.id), target: "_blank", rel: "noopener noreferrer" } }));
    const body = [...errorLine, ...renderOutput(r, runDir(slug, r.id), { autoplay: true }), links];
    return el("tr", { class: "run-detail" }, [el("td", { attrs: { colspan: String(COLUMNS.length + 2) } }, [el("div", { class: "detail-inner" }, body)])]);
  }
  draw();
  syncSelection();
}

// "Game · 11 runs · 3 models · updated Sep 27, 2026"
function renderMeta(page, runs) {
  const models = new Set(runs.map((r) => r.model));
  const latest = runs.map((r) => r.started_at).filter(Boolean).sort().pop();
  const meta = document.getElementById("page-meta");
  meta.append(
    el("span", { class: "kind-chip", text: kindUi(page.kind).label }),
    el("span", { text: `${runs.length} run${runs.length === 1 ? "" : "s"}` }),
    el("span", { text: `${models.size} model${models.size === 1 ? "" : "s"}` }),
  );
  if (latest) meta.append(el("span", { class: "last-run", text: `last run ${fmtDate(latest)}` }));
}

// At-a-glance summary: the cheapest, fastest and leanest completed run, and how many runs were verified.
function renderHighlights(runs) {
  const box = document.getElementById("highlights");
  const tiles = [];
  const specs = [
    ["cost_usd", "Cheapest", fmtCost],
    ["duration_ms", "Fastest", fmtDuration],
    ["tokens_total", "Fewest tokens", fmtNum],
  ];
  for (const [key, label, fmt] of specs) {
    const ranks = rankBy(runs, key);
    const winner = runs.find((r) => ranks.get(r.id) === 1);
    if (!winner) continue;
    tiles.push(
      el("a", { class: "hl hl-good", attrs: { href: runUrl(slug, winner.id) } }, [
        el("span", { class: "hl-label", text: label }),
        el("span", { class: "hl-value", text: fmt(winner.metrics[key]) }),
        el("span", { class: "hl-sub" }, [effortPill(winner.effort), el("span", { class: "name", text: modelParts(winner.model).short, attrs: { title: winner.model } })]),
      ])
    );
  }
  if (!tiles.length) return;
  const checked = runs.filter((r) => outputVerified(r) != null);
  const verified = runs.filter((r) => outputVerified(r) === true).length;
  const failed = runs.filter((r) => !isComplete(r)).length;
  const total = runs.reduce((s, r) => s + (r.metrics.cost_usd || 0), 0);
  tiles.push(
    el("div", { class: "hl" }, [
      el("span", { class: "hl-label", text: "Verified" }),
      el("span", { class: "hl-value", text: checked.length ? `${verified} / ${runs.length}` : "–" }),
      el("span", { class: "hl-sub", text: `${failed ? `${failed} failed · ` : ""}${fmtCost(total)} total spend` }),
    ])
  );
  box.append(...tiles);
  box.hidden = false;
}

// Column help as a custom tooltip: native title tooltips can't be shown sooner than ~1-2s.
const TIP_DELAY_MS = 500;

function addHelpTooltips(cells) {
  const tip = el("div", { class: "col-tip", attrs: { role: "tooltip", id: "col-tip" } });
  document.body.append(tip);
  let timer;
  const hideVisible = () => tip.classList.remove("show"); // hide without cancelling a pending show
  const hide = () => {
    clearTimeout(timer);
    hideVisible();
  };
  const show = (cell) => {
    tip.textContent = cell.dataset.help;
    tip.classList.add("show");
    const r = cell.getBoundingClientRect();
    tip.style.left = `${Math.max(8, Math.min(r.left, innerWidth - tip.offsetWidth - 8))}px`;
    tip.style.top = `${r.bottom + 6}px`;
  };
  for (const cell of cells) {
    cell.setAttribute("aria-description", cell.dataset.help);
    cell.addEventListener("mouseenter", () => {
      clearTimeout(timer);
      timer = setTimeout(() => show(cell), TIP_DELAY_MS);
    });
    cell.addEventListener("mouseleave", hide);
  }
  // A page scroll (including the incidental one browsers fire while scrolling a
  // hovered cell into view) should only dismiss an already-visible tip, not cancel
  // a still-pending one — otherwise that show never happens while the mouse stays put.
  addEventListener("scroll", hideVisible, true);
}
