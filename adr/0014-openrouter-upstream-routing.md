# 0014. Pin the OpenRouter upstream provider per run

- Status: Accepted
- Date: 2026-09-30

## Context

`bench run` could name an OpenRouter model but not which upstream provider serves it: the upstream was
whatever OpenRouter picked, and could differ between runs of one batch. The site didn't record it either,
so two runs of one model weren't necessarily comparable.

pi 0.87.1 already has the pieces: `OpenRouterRouting` (sent as the request's `provider` field),
a `before_provider_request` extension hook that can rewrite the request body, `provider_stream_event`
chunks that carry the serving upstream, and `-e <path>` extensions that still load under bench's `-ne`.

## Decision

- **Syntax**: an `@UPSTREAMS` suffix on the model part of a `-m` spec, before the levels:
  `[harness:]MODEL@SLUG[,SLUG...][:LEVELS]`. `@deepinfra` pins to one upstream (fallbacks off);
  `@deepinfra,fireworks` lets OpenRouter pick among the listed ones. Only valid for pi `openrouter/`
  models; anything else is an error before any run starts.
- **Mechanism**: bench ships `src/bench/pi_ext/openrouter_routing.ts`. The runner passes it with an
  explicit `-e` and sets `BENCH_OPENROUTER_ROUTING` + `BENCH_ROUTE_LOG` in that run's environment.
  The extension merges the routing into the request's `provider` field and logs the serving upstream
  per response.
- **Identity**: the upstream is part of the recorded model name (`openrouter/…/flash@deepinfra`), so
  two upstreams are separate rows/compare cards (vendor tint unchanged); run ids use `-via-`.
  `run.json` carries `route.requested`/`route.served`.
- A served value outside `requested.only` is appended to the run's `error` so it's visible.

## Alternatives considered

- **Global `models.json` `modelOverrides`**: affects every pi session on the machine, and can't compare
  upstreams inside one batch. Rejected.
- **Per-run `PI_CODING_AGENT_DIR` pointing at a temp agent dir**: loses `auth.json`/settings, fragile.
  Rejected.
- **A separate `--openrouter-provider` flag**: can't differ per model and doesn't work in sets. Rejected.

## Consequences

- pi computes `usage.cost.total` from its catalog rates (`calculateCost(model, usage)` in pi-ai's
  `models.js`), not from what OpenRouter actually charged — verified by reading pi's source, no model
  call needed. Upstreams are priced differently, so **costs of pinned runs may be wrong**: compare
  cross-upstream costs in the OpenRouter dashboard, not on the page. No follow-up can fix this in bench
  (the true charge is only in OpenRouter's generation API); the caveat is in README.md.
- The served upstream is recorded from stream chunks, trusting pi to surface OpenRouter's `provider`
  field there. If a future pi changes that shape, routed runs will show an empty `served`.
- No new Python dependencies; the extension is plain TypeScript that pi loads itself, shipped in the
  wheel like `briefs/*.md`.
