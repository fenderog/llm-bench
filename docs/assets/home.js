import { el, getJSON, fmtDate, showMessage } from "./common.js";

const cards = document.getElementById("cards");

try {
  const pages = await getJSON("data/pages.json");
  if (!pages.length) {
    showMessage(cards.parentElement, "No pages imported yet.");
  } else {
    for (const p of pages) cards.append(renderCard(p));
  }
} catch (err) {
  showMessage(cards.parentElement, `Could not load pages: ${err.message}`, "error");
}

function renderCard(p) {
  const thumb = p.thumb
    ? el("img", { class: "thumb", attrs: { src: p.thumb, alt: "" } })
    : el("div", { class: "thumb-ph", text: "no preview" });
  return el("a", { class: "card", attrs: { href: `page.html?p=${encodeURIComponent(p.slug)}` } }, [
    thumb,
    el("div", { class: "card-body" }, [
      el("div", { class: "card-title", text: p.title }),
      el("div", { class: "card-meta", text: `${p.n_runs} run${p.n_runs === 1 ? "" : "s"} · ${(p.models || []).join(", ")}` }),
      el("div", { class: "card-meta", text: `updated ${fmtDate(p.updated)}` }),
    ]),
  ]);
}
