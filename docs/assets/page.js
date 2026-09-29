import {
  qs, el, getJSON, fmtNum, fmtDuration, fmtCost, fmtDate, showMessage, badge, runDir, sandboxedGame, harnessLabel, stateBadge,
  mediaGallery, effortPill, effortIndex, modelLabel, modelParts, runUrl, byModelThenEffort, rankBy, LOWER_IS_BETTER, isComplete,
  rankLabel, canEditRanks, saveRanks, byRankThenModel, rankChip, vendorAttrs, KIND_LABEL,
} from "./common.js";

const slug = qs("p");
const main = document.getElementById("main");

const COLUMNS = [
  { key: "rank", label: "Rank", get: (r) => r.rank ?? null, num: false,
    help: "The page owner's own ranking of the runs (🥇🥈🥉, then #4, #5…; ties allowed). – means not ranked." },
  { key: "model", label: "Model", get: (r) => r.model, num: false,
    help: "The model that ran the task (provider/model)." },
  { key: "effort", label: "Effort", get: (r) => r.effort, sortVal: (r) => effortIndex(r.effort), num: false,
    help: "Reasoning effort the model was run at (minimal / low / medium / high / xhigh / max; the bars show the level). Higher effort lets it think longer before acting. Level names are the harness's; the same name can mean different budgets at different providers." },
  { key: "harness", label: "Harness", get: (r) => harnessLabel(r), num: false,
    help: "The agent program that ran the model and executed its tool calls (pi or claude-code), with its version. Every run is one direct agent with only file and shell tools." },
  { key: "verified", label: "Verified", get: (r) => r.verified, num: false,
    help: "Game pages: whether the exported web build booted in headless Chrome (a WebGL canvas rendered, two screenshots differed, no page errors). Web pages: whether the packaged page loaded offline in a sandboxed iframe with no page errors and no network requests. Media pages: whether every output file was a readable image or video within the limits. – means no check was recorded." },
  { key: "duration_ms", label: "Duration", get: (r) => r.metrics.duration_ms, num: true, fmt: fmtDuration,
    help: "Wall-clock time of the agent session, from start to finish. ★ marks the fastest completed run." },
  { key: "tokens_total", label: "Tokens", get: (r) => r.metrics.tokens_total, num: true, fmt: fmtNum,
    help: "Input + output tokens reported by the provider. Excludes input served from the prompt cache. ★ marks the completed run that used the fewest." },
  { key: "tokens_output", label: "Output tok", get: (r) => r.metrics.tokens_output, num: true, fmt: fmtNum,
    help: "Tokens the model generated: messages, tool-call arguments and file contents it wrote. Includes reasoning tokens when the provider counts them as output (OpenAI does)." },
  { key: "tokens_reasoning", label: "Reasoning tok", get: (r) => r.metrics.tokens_reasoning, num: true, fmt: fmtNum,
    help: "Tokens spent on hidden internal reasoning (thinking) before answering. Not shown in the transcript beyond short summaries, but billed as output." },
  { key: "cost_usd", label: "Cost", get: (r) => r.metrics.cost_usd, num: true, fmt: fmtCost,
    help: "Cost in USD for the whole session as reported by the provider, including cached input at its discounted rate. For Claude Code runs it's Claude Code's own estimate at API prices (also when run on a subscription). ★ marks the cheapest completed run." },
  { key: "tool_calls", label: "Tool calls", get: (r) => r.metrics.tool_calls, num: true, fmt: fmtNum,
    help: "Number of tools the agent invoked (bash, read, write, edit, ls, …)." },
  { key: "turns", label: "Turns", get: (r) => r.metrics.turns, num: true, fmt: fmtNum,
    help: "Number of model responses in the session. Each turn can make tool calls; the last one is usually the final answer." },
];

if (!slug) {
  showMessage(main, "Missing ?p=<slug> – pick a page from the home page.", "error");
} else {
  try {
    const [page, runs] = await Promise.all([
      getJSON(`data/${slug}/page.json`),
      getJSON(`data/${slug}/results.json`),
    ]);
    render(page, runs, await canEditRanks());
  } catch (err) {
    showMessage(main, `Could not load page "${slug}": ${err.message}`, "error");
  }
}

function render(page, runs, editable) {
  document.title = `${page.title} – llm-bench`;
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

  document.getElementById("compare-all").href = `compare.html?p=${encodeURIComponent(slug)}`;
  document.getElementById("runs-count").textContent = `${runs.length} run${runs.length === 1 ? "" : "s"}`;
  if (isMedia) {
    main.classList.add("media-page");
    renderGallery(runs);
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
  const best = {};
  for (const key of Object.keys(LOWER_IS_BETTER)) {
    const ranks = rankBy(runs, key);
    best[key] = new Set([...ranks].filter(([, rank]) => rank === 1).map(([id]) => id));
  }

  const headRow = el("tr", {}, [
    el("th", { attrs: { "data-help": isMedia ? "Click a row to expand it and see that run's output files." : "Click a row to expand it and play that run's game inline." } }),
    el("th", { attrs: { "data-help": isMedia ? "The run's first output (a video shows its poster frame). Click to open the run." : "Screenshot of the running game taken during verification. Click to open the run." } }),
    ...COLUMNS.map((c) =>
      el("th", { text: c.label, class: c.num ? "has-help is-num" : "has-help", attrs: { "data-key": c.key, "data-help": `${c.help}\n\nClick to sort.` }, on: { click: () => sortBy(c.key) } })
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
    const rows = [...runs].sort((a, b) => {
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
    for (const c of COLUMNS) if (c.num) maxes[c.key] = Math.max(1, ...runs.map((r) => c.get(r) || 0));

    tbody.replaceChildren();
    for (const r of rows) {
      const url = runUrl(slug, r.id);
      const thumb = r.thumb
        ? el("a", { attrs: { href: url, "aria-label": "Open run" } }, [el("img", { class: "row-thumb", attrs: { src: runDir(slug, r.id) + r.thumb, alt: "", loading: "lazy" } })])
        : el("span", { class: "thumb-none", text: "–" });
      const tds = [el("td", {}, [el("span", { class: "caret", text: "▶" })]), el("td", { class: "thumb-cell" }, [thumb])];
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
          tds.push(el("td", { class: "harness-cell", text: v ?? "–", attrs }));
        } else if (c.key === "verified") {
          const sb = stateBadge(r);
          tds.push(el("td", { attrs }, [sb || (v === true ? badge("✓", "good") : v === false ? badge("✗", "bad") : el("span", { class: "muted", text: "–" }))]));
        } else if (c.num) {
          const pct = Math.max(0, Math.min(100, ((v || 0) / maxes[c.key]) * 100));
          const isBest = best[c.key] && best[c.key].has(r.id);
          if (isBest) attrs.title = LOWER_IS_BETTER[c.key];
          tds.push(
            el("td", { class: isBest ? "is-num is-best" : "is-num", attrs }, [
              el("div", { class: "bar-cell" }, [
                el("span", { class: "val", text: c.fmt ? c.fmt(v) : v ?? "–" }),
                el("span", { class: "track" }, [el("span", { class: "bar", attrs: { style: `width:${pct}%` } })]),
              ]),
            ])
          );
        } else {
          tds.push(el("td", { text: v ?? "–", attrs }));
        }
      }
      const tr = el("tr", { class: isComplete(r) ? "run-row" : "run-row is-failed", attrs: { tabindex: "0", "aria-expanded": "false", ...vendorAttrs(r.model) } }, tds);
      const toggle = () => {
        const open = tr.getAttribute("aria-expanded") === "true";
        tr.setAttribute("aria-expanded", String(!open));
        if (open) tr.nextElementSibling.remove(); // removing the iframe stops the game
        else tr.after(detailRow(r, url));
      };
      tr.addEventListener("click", (e) => {
        if (!e.target.closest("a, button")) toggle();
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
  // ranking through `bench serve`, which rewrites ranking.json and results.json.
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
    let body;
    if (r.media) {
      body = [...errorLine, mediaGallery(r, runDir(slug, r.id)), links];
    } else if (r.game) {
      const entry = runDir(slug, r.id) + r.game.entry;
      links.append(el("a", { text: "Open full screen ↗ (unsandboxed)", attrs: { href: entry, target: "_blank", rel: "noopener noreferrer" } }));
      body = [...errorLine, el("div", { class: "game-frame" }, [sandboxedGame(entry)]), links];
    } else {
      const none = isMedia ? "No output files recorded for this run." : "No playable build recorded for this run.";
      body = [...errorLine, el("p", { class: "msg", text: none }), links];
    }
    return el("tr", { class: "run-detail" }, [el("td", { attrs: { colspan: String(COLUMNS.length + 2) } }, [el("div", { class: "detail-inner" }, body)])]);
  }
  drawTable();
}

// "Game · 11 runs · 3 models · updated Sep 27, 2026"
function renderMeta(page, runs) {
  const models = new Set(runs.map((r) => r.model));
  const latest = runs.map((r) => r.started_at).filter(Boolean).sort().pop();
  const meta = document.getElementById("page-meta");
  meta.append(
    el("span", { class: "kind-chip", text: KIND_LABEL[page.kind] ?? "Game" }),
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
        el("span", { class: "hl-sub" }, [effortPill(winner.effort), el("span", { class: "name", text: modelParts(winner.model).name, attrs: { title: winner.model } })]),
      ])
    );
  }
  if (!tiles.length) return;
  const checked = runs.filter((r) => r.verified != null);
  const verified = runs.filter((r) => r.verified === true).length;
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

// Media pages: one card per run (its first output, or poster frame), linking to the run page.
function renderGallery(runs) {
  const grid = el("div", { class: "card-grid gallery", attrs: { id: "gallery" } });
  for (const r of [...runs].sort(byRankThenModel)) {
    const n = (r.media || []).length;
    const sb = stateBadge(r);
    const thumb = r.thumb
      ? el("img", { class: "thumb", attrs: { src: runDir(slug, r.id) + r.thumb, alt: "", loading: "lazy" } })
      : el("div", { class: "thumb-ph", text: "no output" });
    grid.append(
      el("a", { class: "card", attrs: { href: runUrl(slug, r.id) } }, [
        thumb,
        el("div", { class: "card-body" }, [
          el("div", { class: "card-head" }, [rankChip(r.rank), effortPill(r.effort), sb || (n > 1 ? el("span", { class: "card-more", text: `${n} files` }) : null)]),
          el("div", { class: "card-meta", text: modelParts(r.model).name, attrs: { title: r.model } }),
          el("div", { class: "card-meta", text: `${fmtCost(r.metrics.cost_usd)} · ${fmtDuration(r.metrics.duration_ms)}` }),
        ]),
      ])
    );
  }
  const section = el("section", { class: "section" }, [
    el("div", { class: "section-head" }, [el("h2", { text: "Gallery" }), el("span", { class: "count", text: "click an image to open its run" })]),
    grid,
  ]);
  document.getElementById("runs-section").before(section);
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
