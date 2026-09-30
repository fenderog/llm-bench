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

// Data JSON is always revalidated (a cheap 304 when unchanged): otherwise the browser's heuristic
// cache can show stale results after a publish, or after saving a ranking locally.
export async function getJSON(url) {
  const res = await fetch(url, { cache: "no-cache" });
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

// Effort levels in increasing order, so tables sort low → max instead of alphabetically.
export const EFFORTS = ["off", "minimal", "low", "medium", "high", "xhigh", "max"];

export function effortIndex(effort) {
  const i = EFFORTS.indexOf(effort);
  return i === -1 ? EFFORTS.length : i;
}

// Page kinds as the viewer names them.
export const KIND_LABEL = { godot: "Game", media: "Media", web: "Web" };

// The effort level as a pill with a 6-step meter (minimal = 1 .. max = 6). Its text is just the level.
export function effortPill(effort) {
  const i = EFFORTS.indexOf(effort);
  const node = el("span", { class: "effort", text: effort ?? "–", attrs: { "data-level": i === -1 ? "unknown" : effort } });
  if (i !== -1) node.style.setProperty("--lvl", String(i));
  return node;
}

// "openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8" → { provider: "openrouter/deepseek",
// name: "deepseek-v4.1-flash", via: "deepinfra/fp8", short: "deepseek-v4.1-flash via deepinfra/fp8" }.
// The @route (a pinned OpenRouter upstream) is split off first: it can contain "/" itself.
// `short` is for places with room for one line (chips, tiles, cards), so pinned upstreams stay apart.
export function modelParts(model) {
  const s = String(model ?? "–");
  const at = s.indexOf("@");
  const base = at === -1 ? s : s.slice(0, at);
  const via = at === -1 ? "" : s.slice(at + 1);
  const i = base.lastIndexOf("/");
  const [provider, name] = i === -1 ? ["", base] : [base.slice(0, i), base.slice(i + 1)];
  return { provider, name, via, short: via ? `${name} via ${via}` : name };
}

// Who made the model, for the quiet color grouping: "anthropic/claude-x" → "anthropic",
// "openai-codex/gpt-6" → "openai", "openrouter/deepseek/v4" → "deepseek" (the @upstream suffix is ignored).
export function vendorOf(model) {
  const base = String(model ?? "").split("@")[0];
  const parts = base.split("/");
  const first = parts.length > 2 && parts[0] === "openrouter" ? parts[1] : parts[0];
  return first.split("-")[0].toLowerCase() || "unknown";
}

// One hue per vendor (fixed for the common ones, hashed for the rest), applied as data-vendor + --vh.
const VENDOR_HUES = { anthropic: 25, openai: 160, google: 215, xai: 275, meta: 250, deepseek: 195, mistral: 35, qwen: 265 };
const VENDOR_NAMES = { anthropic: "Anthropic", openai: "OpenAI", google: "Google", deepseek: "DeepSeek", xai: "xAI", meta: "Meta", mistral: "Mistral", qwen: "Qwen" };
export function vendorName(key) {
  return VENDOR_NAMES[key] ?? key[0].toUpperCase() + key.slice(1);
}

// Groups runs (already sorted by byRankThenModel) by vendor. Groups go by their best rank, then unranked ones by name.
export function groupByVendor(runs) {
  const groups = new Map();
  for (const r of runs) {
    const key = vendorOf(r.model);
    if (!groups.has(key)) groups.set(key, { key, name: vendorName(key), runs: [] });
    groups.get(key).runs.push(r);
  }
  const best = (g) => Math.min(...g.runs.map((r) => r.rank ?? Infinity));
  return [...groups.values()].sort((a, b) => best(a) - best(b) || a.name.localeCompare(b.name));
}

export function vendorAttrs(model) {
  const v = vendorOf(model);
  let hue = VENDOR_HUES[v];
  if (hue == null) {
    let h = 0;
    for (const ch of v) h = (h * 31 + ch.charCodeAt(0)) % 360;
    hue = h;
  }
  return { "data-vendor": v, style: `--vh:${hue}` };
}

// Model name in bold with its provider prefix quiet below it. An OpenRouter `@upstream` suffix
// (e.g. "…flash@deepinfra") is shown as a quiet "via …" chip, via textContent only.
export function modelLabel(model) {
  const { provider, name, via } = modelParts(model);
  return el("span", { class: "model", attrs: { title: model } }, [
    el("span", { class: "model-name", text: name }),
    provider ? el("span", { class: "model-provider", text: provider }) : null,
    via ? el("span", { class: "model-via", text: `via ${via}` }) : null,
  ]);
}

export function runUrl(slug, id) {
  return `run.html?p=${encodeURIComponent(slug)}&r=${encodeURIComponent(id)}`;
}

// Default run order everywhere: by model, then effort from low to high.
export function byModelThenEffort(a, b) {
  return String(a.model).localeCompare(String(b.model)) || effortIndex(a.effort) - effortIndex(b.effort) || String(a.id).localeCompare(String(b.id));
}

// Metrics where lower is better, used for "best" highlights. Only completed runs compete.
export const LOWER_IS_BETTER = { duration_ms: "fastest", cost_usd: "cheapest", tokens_total: "fewest tokens" };

export function isComplete(run) {
  return !run.state || run.state === "complete";
}

// Ranks runs by a metric (ascending) among completed runs that have it: Map(run id → 1-based rank),
// with ties sharing a rank. Empty when fewer than two runs compete (nothing to compare).
export function rankBy(runs, key) {
  const vals = runs.filter((r) => isComplete(r) && r.metrics && typeof r.metrics[key] === "number");
  const ranks = new Map();
  if (vals.length < 2) return ranks;
  const sorted = [...vals].sort((a, b) => a.metrics[key] - b.metrics[key]);
  sorted.forEach((r, i) => {
    const prev = sorted[i - 1];
    ranks.set(r.id, prev && prev.metrics[key] === r.metrics[key] ? ranks.get(prev.id) : i + 1);
  });
  return ranks;
}

// Ranked runs first (by rank), then everything else by model and effort.
export function byRankThenModel(a, b) {
  const ra = a.rank ?? Infinity, rb = b.rank ?? Infinity;
  return ra !== rb ? ra - rb : byModelThenEffort(a, b);
}

export function rankChip(rank) {
  const text = rankLabel(rank);
  return text ? el("span", { class: "rank-chip", text, attrs: { title: `Ranked ${ordinal(rank)} by the page owner` } }) : null;
}

// Your ranking (run.rank, from data/<slug>/ranking.json): 🥇🥈🥉 for the top three, "#4" after that.
export function rankLabel(rank) {
  if (rank == null) return null;
  return ["🥇", "🥈", "🥉"][rank - 1] || `#${rank}`;
}

// Ranking is edited only through `bench serve` on this machine, which answers api/local;
// GitHub Pages has no such endpoint, so the published site is always read-only.
export async function canEditRanks() {
  if (!["localhost", "127.0.0.1", "[::1]"].includes(location.hostname)) return false;
  try {
    const res = await fetch("api/local", { cache: "no-store" });
    return res.ok && (await res.json()).rank === true;
  } catch {
    return false;
  }
}

export async function saveRanks(slug, ranks) {
  const res = await fetch(`api/rank?p=${encodeURIComponent(slug)}`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ranks }),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `HTTP ${res.status}`);
}

export function ordinal(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
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
      el("a", { text: "download", attrs: { href: base + item.path, download: name } }),
    ]);
    grid.append(el("figure", { class: "media-item" }, [el("div", { class: "media-box" }, [mediaElement(item, base)]), caption]));
  }
  return grid;
}
