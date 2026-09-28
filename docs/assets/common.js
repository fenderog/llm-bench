// Shared helpers: fetch, formatting, query params, tiny DOM builder, markdown.

export function qs(name) {
  return new URLSearchParams(location.search).get(name);
}

export function qsList(name) {
  const v = qs(name);
  if (!v) return [];
  return v.split(",").map((s) => s.trim()).filter(Boolean);
}

export function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Tiny DOM builder. `text` is always set via textContent (never HTML).
export function el(tag, opts = {}, children = []) {
  const node = document.createElement(tag);
  if (opts.class) node.className = opts.class;
  if (opts.text != null) node.textContent = opts.text;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) if (v != null) node.setAttribute(k, v);
  if (opts.data) for (const [k, v] of Object.entries(opts.data)) node.dataset[k] = v;
  if (opts.on) for (const [k, fn] of Object.entries(opts.on)) node.addEventListener(k, fn);
  for (const c of children) if (c) node.append(c);
  return node;
}

export function fmtNum(n) {
  if (n == null || Number.isNaN(n)) return "–";
  return Number(n).toLocaleString();
}

export function fmtDuration(ms) {
  if (ms == null || Number.isNaN(ms)) return "–";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const totalSec = ms / 1000;
  if (totalSec < 60) return `${totalSec.toFixed(1)}s`;
  const totalSecR = Math.round(totalSec);
  const m = Math.floor(totalSecR / 60);
  const s = totalSecR % 60;
  return `${m}m ${s}s`;
}

export function fmtCost(usd) {
  if (usd == null || Number.isNaN(usd)) return "–";
  return `$${Number(usd).toFixed(usd < 0.01 ? 4 : 3)}`;
}

export function fmtDate(iso) {
  if (!iso) return "–";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// Elapsed time since session start, as "+m:ss".
export function fmtElapsed(ms) {
  if (ms == null || Number.isNaN(ms) || ms < 0) return null;
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `+${m}:${String(s).padStart(2, "0")}`;
}

export function runDir(slug, runId) {
  return `data/${slug}/runs/${runId}/`;
}

export async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
  return res.json();
}

export async function getText(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
  return res.text();
}

export function showMessage(container, text, kind = "info") {
  container.replaceChildren(el("p", { class: `msg msg-${kind}`, text }));
}

// Optional markdown rendering via the pinned `marked` CDN module. Falls back to
// plain text if it can't be loaded. Model output is untrusted: raw HTML in the
// markdown is rendered as visible text, and links/images may only use http(s)
// or relative URLs.
function loadMarked() {
  const importPromise = import("https://cdn.jsdelivr.net/npm/marked@15.0.12/lib/marked.esm.js")
    .then(({ Marked }) => new Marked({ renderer: { html: (t) => escapeHtml(typeof t === "string" ? t : t.text) } }))
    .catch(() => null);
  const timeout = new Promise((resolve) => setTimeout(() => resolve(null), 1800));
  return Promise.race([importPromise, timeout]);
}

export const markedReady = loadMarked();

const SAFE_URL = /^(https?:|#|\.{0,2}\/|[^:]*$)/i;

export async function renderMarkdown(container, text) {
  const source = text == null ? "" : String(text);
  const marked = await markedReady;
  container.replaceChildren();
  if (marked) {
    container.classList.add("content-md");
    container.innerHTML = marked.parse(source);
    for (const node of container.querySelectorAll("[href], [src]")) {
      for (const attr of ["href", "src"]) {
        if (node.hasAttribute(attr) && !SAFE_URL.test(node.getAttribute(attr).trim())) node.removeAttribute(attr);
      }
    }
  } else {
    container.classList.add("content-plain");
    container.textContent = source;
  }
}

export function badge(text, kind) {
  return el("span", { class: `badge badge-${kind}`, text });
}

// "pi 0.87.1" (name only when version is null), "–" when harness is missing entirely.
export function harnessLabel(run) {
  const h = run && run.harness;
  if (!h || !h.name) return "–";
  return h.version ? `${h.name} ${h.version}` : h.name;
}

// A red badge for a run whose state isn't "complete" (e.g. "failed", "timeout"),
// or null when the run completed normally / has no state recorded.
export function stateBadge(run) {
  if (!run || !run.state || run.state === "complete") return null;
  return badge(run.state, "bad");
}

// The one place games are embedded: sandboxed without allow-same-origin, so game
// code gets an opaque origin and can't touch this site's storage or cookies.
export function sandboxedGame(entryUrl) {
  return el("iframe", {
    attrs: { src: entryUrl, sandbox: "allow-scripts allow-pointer-lock", allow: "fullscreen; autoplay; gamepad" },
  });
}

// Builds a click-to-play `.game-frame`: an overlay (thumb + play button,
// carrying `data-play`) that is replaced in place by a sandboxed iframe on
// click. Games never boot on their own. Returns the frame element.
export function buildGameFrame(entryUrl, thumbUrl) {
  const frame = el("div", { class: "game-frame" });
  const overlay = el(
    "button",
    {
      class: "play-overlay",
      attrs: { type: "button", "data-play": "1", "aria-label": "Play" },
    },
    [el("span", { class: "play-icon", text: "▶" }), el("span", { class: "play-label", text: "Click to play" })]
  );
  if (thumbUrl) overlay.style.backgroundImage = `url("${thumbUrl}")`;
  overlay.addEventListener("click", () => overlay.replaceWith(sandboxedGame(entryUrl)));
  frame.append(overlay);
  return frame;
}

function fmtBytes(n) {
  if (n == null) return null;
  return n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
}

// One media output (run.media item). Model-made SVGs may contain scripts, so every image,
// SVG included, is shown through <img> (which never runs them) and never inlined or framed.
// Videos never autoplay: like games, they start on an explicit click.
export function mediaElement(item, base) {
  if (item.type === "video") {
    return el("video", {
      attrs: { src: base + item.path, poster: item.poster ? base + item.poster : null, controls: "", preload: "none", playsinline: "", loop: "" },
    });
  }
  return el("img", { attrs: { src: base + item.path, alt: "", loading: "lazy" } });
}

// A run's outputs as captioned figures (file name, size, duration) with download links.
// Downloads use the `download` attribute so an SVG is saved, never opened as a page here.
export function mediaGallery(run, base) {
  const grid = el("div", { class: "media-grid" });
  for (const item of run.media || []) {
    const name = item.path.split("/").pop();
    const dims = item.width && item.height ? `${item.width}×${item.height}` : null;
    const dur = item.duration_s != null ? `${Number(item.duration_s).toFixed(1)}s` : null;
    const caption = el("figcaption", {}, [
      el("span", { text: [name, dims, dur, fmtBytes(item.bytes)].filter(Boolean).join(" · ") }),
      " ",
      el("a", { text: "download", attrs: { href: base + item.path, download: name } }),
    ]);
    grid.append(el("figure", { class: "media-item" }, [el("div", { class: "media-box" }, [mediaElement(item, base)]), caption]));
  }
  return grid;
}
