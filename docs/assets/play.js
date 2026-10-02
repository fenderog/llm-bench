import { qs, el, loadPage, showMessage, runDir, runUrl, sandboxedGame, mediaGallery, modelLabel, effortPill, stateBadge, noOutputText } from "./common.js";

// play.html?p=<slug>&r=<run id>: one run's output alone in a window. Games and web pages go through
// sandboxedGame() and media through mediaGallery(), exactly as elsewhere (ADR-0004), never the raw entry URL.
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
  document.getElementById("play-bar").append(...[modelLabel(r.model), effortPill(r.effort), stateBadge(r), el("a", { text: "Run page →", attrs: { href: runUrl(slug, id) } })].filter(Boolean));
  const base = runDir(slug, id);
  const out = [];
  if (r.error) out.push(el("p", { class: "run-error", text: r.error }));
  if (r.media) out.push(mediaGallery(r, base));
  else if (r.game) out.push(el("div", { class: "play-frame" }, [sandboxedGame(base + r.game.entry)])); // boots now: opening the window was the click
  else out.push(el("p", { class: "msg", text: noOutputText(r) }));
  main.replaceChildren(...out);
}
