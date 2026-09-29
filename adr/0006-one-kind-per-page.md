# 0006. A page is one prompt with one kind

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

The point of the site is comparison: the same task, attempted by different models at different effort levels.
The first design (DESIGN.md) was generic: a run could hold any mix of artifacts (`image`, `video`, `site`,
`wasm`, `file`, ...), and each page had configurable metrics and charts.

## Decision

- **A page is one prompt.** Its runs are model × effort attempts, added over time by `bench import` or `bench run`.
  - `bench run --page` reuses the page's prompt.
  - A different prompt needs `--change-prompt`, because the page's prompt applies to all its runs.
- **A page has exactly one kind**, and every run of the page has it:
  - `godot`: a project published as a playable web build.
  - `media`: images/videos the agent saved to `./output/`.
  
  Importing a run of another kind is an error.
- Each kind has its own brief template (`src/bench/briefs/<kind>.md`), post-processing step (export + verify, or
  media normalization) and viewer (Game tab or Output tab).
- The metrics are fixed (duration, tokens, cost, tool calls, turns), not configured per page.

## Alternatives considered

- **Generic artifacts per run** (the DESIGN.md model): more flexible, but runs of one page could then have
  outputs that can't be compared, and the viewer would need a renderer per artifact type.
- **Mixed kinds on a page**: compare and gallery views would have to handle every combination.

## Consequences

- Compare, gallery and highlights stay simple, because all runs of a page look alike.
- Adding a kind is a contained change: a brief, a processing step in `runner.py`, a viewer tab, and a row in
  the 0004 table. Native image/video models would be a new harness writing to `./output/`, not a new kind.
- Custom per-task scoring doesn't fit. The owner's ranking (0010) plays that role today.
