import { qs, el, loadPage, showMessage, runDir, runUrl, renderOutput, modelLabel, effortPill, stateBadge, outputBadge } from "./common.js";

// play.html?p=<slug>&r=<run id>: one run's output alone in a window, shown by renderOutput() like everywhere else
// (games and pages sandboxed, never the raw entry URL: ADR-0004). It boots now: opening the window was the click.
const slug = qs("p");
const id = qs("r");
const main = document.getElementById("play");

const page = await loadPage(slug, main);
if (page) {
  const r = page.runs.find((x) => x.id === id);
  if (!id) showMessage(main, "Missing ?r=<run id>.", "error");
  else if (!r) showMessage(main, `No run "${id}" on page "${slug}".`, "error");
  else render(r);
}

function render(r) {
  document.title = `${r.model} · ${r.effort} – llm-bench`;
  document.getElementById("play-bar").append(...[modelLabel(r.model), effortPill(r.effort), stateBadge(r), outputBadge(r), el("a", { text: "Run page →", attrs: { href: runUrl(slug, id) } })].filter(Boolean));
  main.replaceChildren(...[r.error ? el("p", { class: "run-error", text: r.error }) : null, ...renderOutput(r, runDir(slug, id), { autoplay: true, frameClass: "play-frame" })].filter(Boolean));
}
