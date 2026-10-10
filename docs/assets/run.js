import { qs, el, loadPage, getJSON, getText, showMessage, badge } from "./dom.js";
import { fmtNum, fmtDuration, fmtCost, fmtDate } from "./fmt.js";
import { runDir, harnessLabel, stateBadge, effortPill, modelParts, rankBy, ordinal, LOWER_IS_BETTER, isComplete, rankChip, playUrl } from "./runs.js";
import { outputBadge, outputVerified, isPlayable, renderOutput, kindUi } from "./output.js";

const slug = qs("p");
const runId = qs("r");
const main = document.getElementById("main");

const page = await loadPage(slug);
if (page) {
  const run = page.runs.find((r) => r.id === runId);
  if (!runId) showMessage(main, "Missing ?r=<run_id> in the URL.", "error");
  else if (!run) showMessage(main, `No run "${runId}" on page "${slug}".`, "error");
  else {
    const link = document.getElementById("page-link");
    link.textContent = page.title;
    link.href = `page.html?p=${encodeURIComponent(slug)}`;
    render(run, runDir(slug, runId), page.runs);
  }
}

function render(run, base, siblings) {
  document.title = `${run.model} · ${run.effort} – llm-bench`;
  const { provider, name, via } = modelParts(run.model);
  document.getElementById("run-provider").textContent = via ? `${provider} · via ${via}` : provider;
  const myRank = run.rank;
  // (replaceChildren would print a null/undefined chip as text, so only real nodes go in)
  document.getElementById("title").replaceChildren(...[el("span", { text: name, attrs: { title: run.model } }), effortPill(run.effort), rankChip(myRank)].filter(Boolean));

  // Stat tiles, each with this run's rank among the page's completed runs ("fastest of 11", "3rd of 11").
  const strip = document.getElementById("metric-strip");
  const m = run.metrics || {};
  const ranked = siblings.some((r) => r.id === run.id) && isComplete(run);
  const tile = (label, key, value) => {
    let rank = null;
    if (ranked && key) {
      const ranks = rankBy(siblings, key);
      const n = ranks.size;
      const r = ranks.get(run.id);
      if (r) {
        const word = LOWER_IS_BETTER[key];
        rank = el("span", {
          class: r === 1 && word ? "stat-rank is-best" : "stat-rank",
          text: r === 1 ? `${word || "lowest"} of ${n}` : `${ordinal(r)} of ${n}`,
          attrs: { title: "Rank among this prompt's completed runs, lowest first" },
        });
      }
    }
    return el("div", { class: "stat" }, [el("span", { class: "stat-label", text: label }), el("span", { class: "stat-value", text: value }), rank]);
  };
  const tiles = el("div", { class: "stat-tiles" }, [
    tile("Cost", "cost_usd", fmtCost(m.cost_usd)),
    tile("Duration", "duration_ms", fmtDuration(m.duration_ms)),
    tile("Tokens", "tokens_total", fmtNum(m.tokens_total)),
    tile("Output tokens", "tokens_output", fmtNum(m.tokens_output)),
    tile("Tool calls", "tool_calls", fmtNum(m.tool_calls)),
    tile("Turns", "turns", fmtNum(m.turns)),
  ]);
  const verified = outputVerified(run);
  const verifiedBadge =
    verified === true ? badge("✓ verified", "good") : verified === false ? badge("✗ not verified", "bad") : el("span", { class: "muted", text: "not verified" });
  const meta = el("div", { class: "run-meta" }, [
    stateBadge(run),
    outputBadge(run),
    verifiedBadge,
    el("span", {}, [el("span", { class: "k", text: "harness" }), el("span", { text: harnessLabel(run) })]),
    el("span", {}, [el("span", { class: "k", text: "started" }), el("span", { text: fmtDate(run.started_at) })]),
  ]);
  strip.append(tiles, meta);
  if (run.error) strip.after(el("p", { class: "run-error", text: run.error }));

  // Counts on the tabs (never on the Game/Output tab, whose label is its whole text).
  if (m.turns != null) tabCount("transcript", fmtNum(m.turns));
  if (run.source && run.source.files) tabCount("source", String(run.source.files.length));

  setupTabs();
  renderGame(run, base);
  renderTranscriptTab(run, base);
  renderSource(run, base);
  renderMetrics(run, base);
}

function tabCount(tab, text) {
  document.querySelector(`#tabs button[data-tab="${tab}"]`).append(el("span", { class: "tab-count", text }));
}

// Tabs; the open tab is kept in the URL hash (#transcript) so it can be linked.
function setupTabs() {
  const buttons = [...document.querySelectorAll("#tabs button")];
  const open = (b) => {
    for (const other of buttons) {
      other.classList.toggle("active", other === b);
      other.setAttribute("aria-selected", String(other === b));
    }
    for (const panel of document.querySelectorAll(".tab-panel")) panel.hidden = panel.id !== `panel-${b.dataset.tab}`;
  };
  for (const b of buttons) {
    b.addEventListener("click", () => {
      open(b);
      history.replaceState(null, "", b.dataset.tab === "game" ? location.pathname + location.search : `#${b.dataset.tab}`);
    });
  }
  const fromHash = buttons.find((b) => `#${b.dataset.tab}` === location.hash);
  open(fromHash || buttons[0]);
}

function renderGame(run, base) {
  const panel = document.getElementById("panel-game");
  document.querySelector('#tabs button[data-tab="game"]').textContent = kindUi(run.kind).tab;
  panel.append(...renderOutput(run, base, { full: true }));
  if (isPlayable(run)) {
    panel.append(
      el("div", { class: "game-links" }, [
        el("a", { text: "Open full screen ↗", attrs: { href: playUrl(slug, run.id), target: "_blank", rel: "noopener noreferrer" } }),
      ])
    );
  }
}

async function renderTranscriptTab(run, base) {
  const panel = document.getElementById("panel-transcript");
  const session = run.session;
  if (!session || !session.conversation) {
    showMessage(panel, "No transcript recorded for this run.");
    return;
  }
  try {
    const conversation = await getJSON(base + session.conversation);
    const { renderTranscript } = await import("./transcript.js");
    renderTranscript(panel, conversation);
  } catch (err) {
    showMessage(panel, `Could not load transcript: ${err.message}`, "error");
  }
}

function renderSource(run, base) {
  const panel = document.getElementById("panel-source");
  const source = run.source;
  if (!source || !source.files || !source.files.length) {
    showMessage(panel, "No source files recorded for this run.");
    return;
  }
  const layout = el("div", { class: "source-layout" });
  const list = el("div", { class: "source-files" });
  const view = el("div", { class: "source-view" }, [el("pre", { text: "Select a file…" })]);
  layout.append(list, view);
  panel.append(layout);

  let latest = 0; // only the most recently clicked file may fill the view
  for (const f of source.files) {
    const btn = el("button", { text: f, attrs: { type: "button" } });
    btn.addEventListener("click", async () => {
      const req = ++latest;
      for (const b of list.children) b.classList.remove("active");
      btn.classList.add("active");
      let text;
      try {
        text = await getText(base + source.root + f);
      } catch (err) {
        text = `Could not load ${f}: ${err.message}`;
      }
      if (req === latest) view.replaceChildren(el("pre", { text }));
    });
    list.append(btn);
  }
  // Open the first code file right away (skipping READMEs/configs when there's a script).
  const first = source.files.findIndex((f) => /\.(gd|js|ts|py|html|svg)$/i.test(f));
  list.children[first === -1 ? 0 : first].click();
}

function renderMetrics(run, base) {
  const panel = document.getElementById("panel-metrics");
  const route = run.route;
  const rows = [
    ["id", run.id],
    ["model", run.model],
    ["effort", run.effort],
    ["kind", run.kind ?? "godot"],
    ["harness", harnessLabel(run)],
    ["started_at", run.started_at],
    ["state", run.state ?? "–"],
    ["error", run.error ?? "–"],
    ["output.ok", run.output ? String(run.output.ok) : "–"],
    ["output.verified", outputVerified(run) == null ? "–" : String(outputVerified(run))],
    ["output.error", run.output?.error ?? "–"],
    ...(route ? [["route.requested", route.requested ? JSON.stringify(route.requested) : "– (OpenRouter's choice)"], ["route.served", (route.served || []).join(", ") || "–"], ["route.cost_usd", route.cost_usd], ["route.pi_cost_usd", route.pi_cost_usd]] : []),
    ...Object.entries(run.metrics || {}),
  ];
  const table = el("table", { class: "metrics" });
  // Raw values, with a readable form alongside where it helps (durations, costs, big counts).
  const hint = (k, v) => {
    if (typeof v !== "number") return null;
    if (k.endsWith("_ms")) return fmtDuration(v);
    if (k.endsWith("_usd")) return fmtCost(v);
    if (v >= 10000) return fmtNum(v);
    return null;
  };
  for (const [k, v] of rows) {
    const h = hint(k, v);
    table.append(el("tr", {}, [el("td", { text: k }), el("td", {}, [v == null ? "–" : String(v), h ? el("span", { class: "hint", text: h }) : null])]));
  }
  panel.append(table);

  if (run.session) {
    const dl = el("div", { class: "downloads" }, [el("span", { class: "k", text: "Raw session files" })]);
    for (const [label, path] of Object.entries(run.session)) {
      if (!path) continue;
      dl.append(el("a", { text: label, attrs: { href: base + path, download: "" } }));
    }
    if (dl.children.length > 1) panel.append(dl);
  }
}
