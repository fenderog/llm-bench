import { appendFileSync } from "node:fs";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

// Loaded by bench for every OpenRouter run (`-e` this file; explicit `-e` paths still load under
// pi's `-ne`). BENCH_ROUTE_LOG is always set; BENCH_OPENROUTER_ROUTING (e.g.
// `{"only": ["deepinfra/fp8"], "allow_fallbacks": false}`) only for a pinned run (`MODEL@slug`), and
// is then merged into the request's `provider` field. For each response
// (generation id) the log gets `{id, provider}` from its first chunk (OpenRouter's display name of
// the upstream that served it, e.g. "DeepInfra") and `{id, cost}` from the final chunk's
// `usage.cost`: what OpenRouter actually charged, which pi's own catalog-rate cost doesn't reflect.
export default function (pi: ExtensionAPI) {
  const routing = JSON.parse(process.env.BENCH_OPENROUTER_ROUTING ?? "null") as Record<string, unknown> | null;
  const log = process.env.BENCH_ROUTE_LOG;
  if (routing) {
    pi.on("before_provider_request", (event) => {
      const body = event.payload as Record<string, unknown>;
      return { ...body, provider: { ...((body.provider as object) ?? {}), ...routing } };
    });
  }
  if (!log) return;
  const seen = new Set<unknown>();
  pi.on("provider_stream_event", (event) => {
    const data = event.data as { id?: unknown; provider?: string; usage?: { cost?: number } } | null;
    if (!data?.id) return;
    if (data.provider && !seen.has(data.id)) {
      seen.add(data.id);
      appendFileSync(log, JSON.stringify({ id: data.id, provider: data.provider }) + "\n");
    }
    if (typeof data.usage?.cost === "number") appendFileSync(log, JSON.stringify({ id: data.id, cost: data.usage.cost }) + "\n");
  });
}
