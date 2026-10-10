// What a run is on the site: effort and model labels, vendors, the page owner's ranks, sorting and highlights.

import { el, badge } from "./dom.js";

export function runDir(slug, runId) {
  return `data/${slug}/runs/${runId}/`;
}

// Effort levels in increasing order, so tables sort low → max instead of alphabetically.
export const EFFORTS = ["off", "minimal", "low", "medium", "high", "xhigh", "max"];

export function effortIndex(effort) {
  const i = EFFORTS.indexOf(effort);
  return i === -1 ? EFFORTS.length : i;
}

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

export function vendorOptions(model) {
  const v = vendorOf(model);
  let hue = VENDOR_HUES[v];
  if (hue == null) {
    let h = 0;
    for (const ch of v) h = (h * 31 + ch.charCodeAt(0)) % 360;
    hue = h;
  }
  return { attrs: { "data-vendor": v }, style: { "--vh": String(hue) } };
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

// The pop-out viewer: one run's output alone in a window (play.html, always sandboxed).
export function playUrl(slug, id) {
  return `play.html?p=${encodeURIComponent(slug)}&r=${encodeURIComponent(id)}`;
}

// Default run order everywhere: by model, then effort from low to high.
export function byModelThenEffort(a, b) {
  return String(a.model).localeCompare(String(b.model)) || effortIndex(a.effort) - effortIndex(b.effort) || String(a.id).localeCompare(String(b.id));
}

// Metrics where lower is better, used for "best" highlights. Only completed runs compete.
export const LOWER_IS_BETTER = { duration_ms: "fastest", cost_usd: "cheapest", tokens_total: "fewest tokens" };

// Two separate questions: isComplete() is about the agent (state), outputOk() about what the kind step made
// of its work (a game that exported, a page that packaged, media files that were kept).
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

// Which runs hold the best (lowest) value of each LOWER_IS_BETTER metric among `runs`: { metric: Set(run id) }.
export function bestSets(runs) {
  const best = {};
  for (const key of Object.keys(LOWER_IS_BETTER)) {
    const ranks = rankBy(runs, key);
    best[key] = new Set([...ranks].filter(([, rank]) => rank === 1).map(([id]) => id));
  }
  return best;
}

// A run with nothing to look at: the agent didn't complete, or the kind step made no usable output.
export function isFailed(run) {
  return !isComplete(run) || run.output?.ok !== true;
}

// The page's filter bar: `f` = { vendors, efforts, models } (arrays, empty = any) and { verified, hideFailed } (booleans).
export function filterRuns(runs, f) {
  const any = (list, value) => !list?.length || list.includes(value);
  return runs.filter((r) =>
    any(f.vendors, vendorOf(r.model)) && any(f.efforts, r.effort) && any(f.models, r.model) &&
    (!f.verified || r.output?.verified === true) && (!f.hideFailed || !isFailed(r)));
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
