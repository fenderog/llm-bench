// DOM and data plumbing: query params, the tiny `el()` builder (text is always textContent, never HTML), fetch helpers.

export function qs(name) {
  return new URLSearchParams(location.search).get(name);
}

export function qsList(name) {
  const v = qs(name);
  if (!v) return [];
  return v.split(",").map((s) => s.trim()).filter(Boolean);
}

// Tiny DOM builder. `text` is always set via textContent (never HTML).
export function el(tag, opts = {}, children = []) {
  const node = document.createElement(tag);
  if (opts.class) node.className = opts.class;
  if (opts.text != null) node.textContent = opts.text;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) if (v != null) node.setAttribute(k, v);
  if (opts.style) for (const [k, v] of Object.entries(opts.style)) node.style.setProperty(k, v);
  if (opts.data) for (const [k, v] of Object.entries(opts.data)) node.dataset[k] = v;
  if (opts.on) for (const [k, fn] of Object.entries(opts.on)) node.addEventListener(k, fn);
  for (const c of children) if (c) node.append(c);
  return node;
}

// Data JSON is always revalidated (a cheap 304 when unchanged): otherwise the browser's heuristic
// cache can show stale results after a publish, or after saving a ranking locally.
export async function getJSON(url) {
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
  return res.json();
}

// All page views share one request and the same URL/error handling.
export async function loadPage(slug, container = document.getElementById("main")) {
  if (!slug) {
    showMessage(container, "Missing ?p=<slug> in the URL.", "error");
    return null;
  }
  try {
    return await getJSON(`data/${encodeURIComponent(slug)}/page.json`);
  } catch (err) {
    showMessage(container, `Could not load page "${slug}": ${err.message}`, "error");
    return null;
  }
}

export async function getText(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
  return res.text();
}

export function showMessage(container, text, kind = "info") {
  container.replaceChildren(el("p", { class: `msg msg-${kind}`, text }));
}

export function badge(text, kind) {
  return el("span", { class: `badge badge-${kind}`, text });
}
