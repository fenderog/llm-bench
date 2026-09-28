import { qs, el, getJSON, getText, fmtNum, fmtDuration, fmtCost, fmtDate, showMessage, badge, runDir, buildGameFrame, harnessLabel, stateBadge, mediaGallery } from "./common.js";
import { renderTranscript } from "./transcript.js";

const slug = qs("p");
const runId = qs("r");
const main = document.getElementById("main");

if (!slug || !runId) {
  showMessage(main, "Missing ?p=<slug>&r=<run_id> in the URL.", "error");
} else {
  const base = runDir(slug, runId);
  try {
    const [page, run] = await Promise.all([
      getJSON(`data/${slug}/page.json`).catch(() => null),
      getJSON(`${base}run.json`),
    ]);
    if (page) {
      const link = document.getElementById("page-link");
      link.textContent = page.title;
      link.href = `page.html?p=${encodeURIComponent(slug)}`;
    }
    render(run, base);
  } catch (err) {
    showMessage(main, `Could not load run "${runId}" for page "${slug}": ${err.message}`, "error");
  }
}

function render(run, base) {
  document.title = `${run.model} · ${run.effort} – llm-bench`;
  document.getElementById("title").textContent = `${run.model} · ${run.effort}`;

  const strip = document.getElementById("metric-strip");
  const m = run.metrics || {};
  const verifiedBadge =
    run.verified === true ? badge("✓ verified", "good") : run.verified === false ? badge("✗ not verified", "bad") : el("span", { class: "muted", text: "verified: –" });
  const sb = stateBadge(run);
  strip.append(
    metric("harness", harnessLabel(run)),
    verifiedBadge,
    metric("duration", fmtDuration(m.duration_ms)),
    metric("cost", fmtCost(m.cost_usd)),
    metric("tokens", fmtNum(m.tokens_total)),
    metric("tool calls", fmtNum(m.tool_calls)),
    metric("started", fmtDate(run.started_at))
  );
  if (sb) strip.append(sb);
  if (run.error) document.getElementById("main").insertBefore(el("p", { class: "run-error", text: run.error }), strip.nextSibling);

  setupTabs();
  renderGame(run, base);
  renderTranscriptTab(run, base);
  renderSource(run, base);
  renderMetrics(run, base);
}

function metric(label, value) {
  return el("span", {}, [el("strong", { text: value }), el("span", { text: ` ${label}` })]);
}

function setupTabs() {
  const buttons = document.querySelectorAll("#tabs button");
  for (const b of buttons) {
    b.addEventListener("click", () => {
      for (const other of buttons) other.classList.toggle("active", other === b);
      for (const panel of document.querySelectorAll(".tab-panel")) panel.hidden = panel.id !== `panel-${b.dataset.tab}`;
    });
  }
}

function renderGame(run, base) {
  const panel = document.getElementById("panel-game");
  if (run.kind === "media") {
    document.querySelector('#tabs button[data-tab="game"]').textContent = "Output";
    if (run.media) panel.append(mediaGallery(run, base));
    else showMessage(panel, "No output files recorded for this run.");
    return;
  }
  if (!run.game) {
    showMessage(panel, "No game recorded for this run.");
    return;
  }
  const entryUrl = base + run.game.entry;
  const thumbUrl = run.thumb ? base + run.thumb : null;
  panel.append(buildGameFrame(entryUrl, thumbUrl));
  panel.append(
    el("div", { class: "game-links" }, [
      el("a", { text: "Open full screen ↗ (unsandboxed)", attrs: { href: entryUrl, target: "_blank", rel: "noopener noreferrer" } }),
    ])
  );
}

async function renderTranscriptTab(run, base) {
  const panel = document.getElementById("panel-transcript");
  const session = run.session;
  if (!session || !session.conversation) {
    showMessage(panel, "No transcript recorded for this run.");
    return;
  }
  try {
    const [conversation, eventsText] = await Promise.all([
      getJSON(base + session.conversation),
      session.events ? getText(base + session.events).catch(() => null) : Promise.resolve(null),
    ]);
    await renderTranscript(panel, conversation, eventsText);
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

  for (const f of source.files) {
    const btn = el("button", { text: f, attrs: { type: "button" } });
    btn.addEventListener("click", async () => {
      for (const b of list.children) b.classList.remove("active");
      btn.classList.add("active");
      try {
        const text = await getText(base + source.root + f);
        view.replaceChildren(el("pre", { text }));
      } catch (err) {
        view.replaceChildren(el("pre", { text: `Could not load ${f}: ${err.message}` }));
      }
    });
    list.append(btn);
  }
}

function renderMetrics(run, base) {
  const panel = document.getElementById("panel-metrics");
  const rows = [
    ["id", run.id],
    ["model", run.model],
    ["effort", run.effort],
    ["kind", run.kind ?? "godot"],
    ["harness", harnessLabel(run)],
    ["started_at", run.started_at],
    ["verified", run.verified == null ? "–" : String(run.verified)],
    ["state", run.state ?? "–"],
    ["error", run.error ?? "–"],
    ...Object.entries(run.metrics || {}),
  ];
  const table = el("table", { class: "metrics" });
  for (const [k, v] of rows) table.append(el("tr", {}, [el("td", { text: k }), el("td", { text: v == null ? "–" : String(v) })]));
  panel.append(table);

  if (run.session) {
    const dl = el("div", { class: "downloads" });
    for (const [label, path] of Object.entries(run.session)) {
      if (!path) continue;
      dl.append(el("a", { text: label, attrs: { href: base + path, download: "" } }));
    }
    if (dl.children.length) panel.append(dl);
  }
}
