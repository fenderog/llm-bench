import { appendFileSync } from "node:fs";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

// Pins the OpenRouter upstream for a bench run. The runner passes `-e` this file (explicit `-e`
// paths still load under pi's `-ne`) and sets BENCH_OPENROUTER_ROUTING (e.g.
// `{"only": ["deepinfra"], "allow_fallbacks": false}`) plus BENCH_ROUTE_LOG in that run's
// environment. The routing is merged into the request's `provider` field; the upstream that
// actually served each response is appended to the log (one line per response).
export default function (pi: ExtensionAPI) {
  const routing = JSON.parse(process.env.BENCH_OPENROUTER_ROUTING ?? "null") as Record<string, unknown> | null;
  const log = process.env.BENCH_ROUTE_LOG;
  if (!routing) return;
  pi.on("before_provider_request", (event) => {
    const body = event.payload as Record<string, unknown>;
    return { ...body, provider: { ...((body.provider as object) ?? {}), ...routing } };
  });
  let lastId: unknown = null;
  pi.on("provider_stream_event", (event) => {
    const data = event.data as { id?: unknown; provider?: string } | null;
    const served = data?.provider;
    if (log && served && data?.id !== lastId) {
      lastId = data?.id;
      appendFileSync(log, JSON.stringify({ provider: served }) + "\n");
    }
  });
}
