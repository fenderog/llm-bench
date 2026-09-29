# 0010. Rankings are written only locally; the site is read-only

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

The metrics measure cost and effort, not quality, and for games and images quality takes human judgment. The
owner wanted to rank the runs of a page in the browser. The published site is static (0001) and can't store anything.

## Decision

- **Only `bench serve` can save a ranking**:
  - `PUT api/rank?p=<slug>` writes `data/<slug>/ranking.json`, then rebuilds.
  - `rebuild` copies each run's rank into `results.json`. `run.json` never holds a rank (0003).
- **Cross-site writes are refused**:
  - The request must be `Content-Type: application/json`, so another site can't send it without a CORS preflight,
    which the server doesn't answer. Otherwise it gets 415.
  - Any `Origin` header must match `Host`, otherwise 403.
  - Input is validated: the slug pattern, run ids belonging to the page, and whole-number ranks.
- The viewer shows rank pickers only when served from localhost and `GET api/local` answers. Everyone else sees
  rankings read-only.
- **The published site never gets a way to write data.**

## Alternatives considered

- **A `bench rank` CLI command**: clumsy, because ranking needs the games and outputs in front of you.
- **Public, arena-style A/B voting**: interesting, but needs a write API outside Pages (for example a
  Cloudflare Worker), plus abuse handling and storage. Deliberately not built.
- **Writing ranks into `run.json`**: a ranking belongs to the whole page, and runs get removed. A separate file
  is easier to rebuild and to prune.

## Consequences

- Rankings are the owner's judgment, published through git like everything else.
- The local server is a small attack surface. The Content-Type and Origin checks are what stop a web page open
  in another tab from writing through it. Keep them, with tests.
- Public voting would mean superseding this ADR.
