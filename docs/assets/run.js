import { qs, el, getJSON, getText, fmtNum, fmtDuration, fmtCost, fmtDate, showMessage, badge, runDir, buildGameFrame } from "./common.js";
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
  strip.append(
    verifiedBadge,
    metric("duration", fmtDuration(m.duration_ms)),
    metric("cost", fmtCost(m.cost_usd)),
    metric("tokens", fmtNum(m.tokens_total)),
    metric("tool calls", fmtNum(m.tool_calls)),
    metric("started", fmtDate(run.started_at))
  );

  renderGame(run, base);
  renderMetrics(run, base);
  renderSource(run, base);
  renderTranscriptSection(run, base);
}

// Each section keeps its <h2>; content goes into a body div below it.
function sectionBody(name) {
  const body = el("div", { class: "section-body" });
  document.getElementById(`section-${name}`).append(body);
  return body;
}

function metric(label, value) {
  return el("span", {}, [el("strong", { text: value }), el("span", { text: ` ${label}` })]);
}

function renderGame(run, base) {
  const panel = sectionBody("game");
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

async function renderTranscriptSection(run, base) {
  const panel = sectionBody("transcript");
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

async function renderSource(run, base) {
  const panel = sectionBody("source");
  const source = run.source;
  if (!source || !source.files || !source.files.length) {
    showMessage(panel, "No source files recorded for this run.");
    return;
  }
  const texts = await Promise.all(
    source.files.map((f) => getText(base + source.root + f).catch((err) => `Could not load ${f}: ${err.message}`))
  );
  source.files.forEach((f, i) => {
    panel.append(el("details", { class: "source-file", attrs: { open: "" } }, [el("summary", { text: f }), el("pre", { text: texts[i] })]));
  });
}

function renderMetrics(run, base) {
  const panel = sectionBody("metrics");
  const rows = [
    ["id", run.id],
    ["model", run.model],
    ["effort", run.effort],
    ["started_at", run.started_at],
    ["verified", run.verified == null ? "–" : String(run.verified)],
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
