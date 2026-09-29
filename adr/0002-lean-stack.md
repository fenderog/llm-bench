# 0002. Lean stack: stdlib-only CLI, vanilla JS, no build step

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

This is a one-person tool that should still work in a year without a dependency upgrade. The owner reviews
changes for bloat and wants to be able to read the whole codebase.

## Decision

- **CLI**: Python ≥ 3.12, standard library only (argparse, json, hashlib, tomllib, http.server, subprocess).
  `pyproject.toml` has `dependencies = []`.
- **Optional pieces are imported lazily and degrade gracefully when they're missing**:
  - Playwright (`bench[verify]`) is used only to boot-check Godot builds.
  - ffmpeg/ffprobe are external binaries used only by media pages.
- **Site**: vanilla JS ES modules, one CSS file, and system fonts. There's no framework and no bundler.
  - The only third-party code is `marked`, pinned to a version and loaded from a CDN. When it doesn't load,
    the page falls back to plain text.
- **Dependencies need the owner's approval.**

## Alternatives considered

- **typer for the CLI**: DESIGN.md planned it. It was dropped because argparse does the job and removes
  the only runtime dependency.
- **A JS framework plus a bundler**: it would make larger UI work easier, but it needs a build step
  (see 0001), a lockfile to maintain, and a toolchain that goes stale.
- **A chart library (Chart.js, Observable Plot)**: the tables with inline bars have been enough so far.

## Consequences

- Installing is `uv sync` and nothing else, and nothing in the stack can break from an upstream release.
- Some things take more code by hand, like the `el()` DOM helper, sortable tables and the markdown sanitizing
  in 0004. Keep those helpers small and in `common.js`.
- Bringing in a new library means revisiting this ADR, not just adding it.
