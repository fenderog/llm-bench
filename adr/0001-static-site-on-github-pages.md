# 0001. Static site on GitHub Pages, no backend

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

The site publishes benchmark runs: tables of metrics, transcripts, playable Godot builds and images/videos.
It has one owner, and new data arrives a few times a day at most. It should cost nothing to host, need no
upkeep, and survive being ignored for months.

## Decision

- The site is `docs/` on `main`, served by GitHub Pages (`main:/docs`), with no Actions workflow.
- Each view is a thin HTML shell (`index.html`, `page.html`, `run.html`, `compare.html`) that fetches JSON
  from `docs/data/` and renders it in the browser. There are no per-page HTML files.
- "Dynamic" means the data changes and the pages pick it up. Nothing is regenerated.
- `docs/.nojekyll` is always present, and every URL is relative because the site lives under `/llm-bench/`.
- `bench serve` reproduces Pages locally: `Access-Control-Allow-Origin: *`, `.wasm` served as `application/wasm`,
  and no COOP/COEP headers.

## Alternatives considered

- **A server with a database**: this would allow writes and search, but it costs money, needs upkeep and
  adds an attack surface.
- **A static site generator (Jekyll, Hugo, Astro...)**: this adds a build step and a toolchain. Rendering
  from JSON in the browser needs neither.
- **A Pages deploy through Actions**: the build output would be the same, with one more workflow to maintain.

## Consequences

- The site can't write anything. Rankings (0010) and public voting are shaped by this.
- Pages can't set headers. This forces the Godot no-threads export (0008), and its 10-minute cache
  causes stale assets after a deploy (0012).
- Pages has limits: 1 GB for the published site, a soft 100 GB/month of bandwidth, and 100 MB per file
  in git. Engine dedupe (0008) and media re-encoding exist to stay under them.
- Games and model output are served from `fenderog.github.io`, an origin shared by all the owner's
  Pages sites, which is why 0004 exists.
