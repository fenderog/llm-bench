// Marked only tokenizes; untrusted Markdown becomes DOM nodes, never HTML.
import { lexer } from "./vendor/marked.esm.js";
import { el } from "./common.js";

function text(value) {
  const entities = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0" };
  return String(value ?? "").replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (match, key) => {
    if (!key.startsWith("#")) return entities[key.toLowerCase()] ?? match;
    const code = key[1].toLowerCase() === "x" ? parseInt(key.slice(2), 16) : Number(key.slice(1));
    return code > 0 && code <= 0x10ffff && !(code >= 0xd800 && code <= 0xdfff) ? String.fromCodePoint(code) : "\ufffd";
  });
}

function safeURL(href, image = false) {
  try {
    const url = new URL(text(href), location.href);
    if (!["http:", "https:"].includes(url.protocol)) return null;
    // Remote images stay as alt text: rendering a transcript never contacts another origin.
    return !image || url.origin === location.origin ? text(href) : null;
  } catch { return null; }
}

function nodes(tokens = []) {
  return tokens.flatMap((t) => {
    const children = () => t.tokens ? nodes(t.tokens) : [document.createTextNode(text(t.text))];
    switch (t.type) {
      case "space": return [];
      case "paragraph": return [el("p", {}, children())];
      case "heading": return [el(`h${t.depth}`, {}, children())];
      case "strong": case "em": case "del": return [el(t.type, {}, children())];
      case "codespan": return [el("code", { text: t.text })];
      case "code": return [el("pre", {}, [el("code", { text: t.text })])];
      case "br": case "hr": return [el(t.type)];
      case "blockquote": return [el("blockquote", {}, children())];
      case "link": {
        const href = safeURL(t.href);
        return [el("a", { attrs: { href, title: t.title ? text(t.title) : null } }, children())];
      }
      case "image": {
        const src = safeURL(t.href, true);
        return [src ? el("img", { attrs: { src, alt: text(t.text), title: t.title ? text(t.title) : null, loading: "lazy" } }) : document.createTextNode(text(t.text))];
      }
      case "list": return [el(t.ordered ? "ol" : "ul", { attrs: { start: t.ordered && t.start !== 1 ? t.start : null } }, t.items.map((item) => {
        const content = nodes(item.tokens);
        if (item.task) content.unshift(el("input", { attrs: { type: "checkbox", disabled: "", checked: item.checked ? "" : null } }));
        return el("li", {}, content);
      }))];
      case "table": {
        const row = (cells, tag) => el("tr", {}, cells.map((cell, i) => el(tag, { style: t.align[i] ? { "text-align": t.align[i] } : {} }, nodes(cell.tokens))));
        return [el("table", {}, [el("thead", {}, [row(t.header, "th")]), el("tbody", {}, t.rows.map((cells) => row(cells, "td")))])];
      }
      case "escape": return [document.createTextNode(t.text)];
      case "text": return children();
      // Raw HTML is visible text. Unknown tokens also stay inert.
      default: return [document.createTextNode(t.raw ?? t.text ?? "")];
    }
  });
}

export function renderMarkdown(container, source) {
  container.classList.add("content-md");
  container.replaceChildren(...nodes(lexer(String(source ?? ""))));
}
