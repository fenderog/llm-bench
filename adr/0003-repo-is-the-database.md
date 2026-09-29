# 0003. The repo is the database; `docs/data` is generated

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

With no backend (0001), the data has to live somewhere Pages can serve it. It also needs history,
backups and a way to undo mistakes.

## Decision

- Git is the store. Every published byte lives under `docs/data/` or `docs/engines/`, is committed, and
  is pushed.
- **`bench import` is the only thing that writes run data.** Its input is an effort-run folder (`fe-model-effort-fanout/1`,
  or `bench-run/1` from `bench run`), and it:
  - cleans and secret-scans the data (0005),
  - writes the run to a temp location first, then moves it into place,
  - is idempotent: importing the same run again replaces it.
- **`run.json` is the source of truth for a run.** These files are derived from it and can be rebuilt at any
  time (`bench rebuild`):
  - `results.json`
  - `pages.json`
  - each run's `rank`
- Nobody edits `docs/data` by hand. To fix a run, re-import it.
- **Inputs are never modified**: `~/dev/effort-runs/` is read-only, and `bench run` writes to `~/dev/bench-runs/`.
- Git LFS isn't used, because Pages serves the LFS pointer instead of the file.

## Alternatives considered

- **An external object store (R2 or S3) for large files**: it would take pressure off the repo size, but adds
  an account, credentials and a second source of truth. Kept as a later option if videos grow.
- **A `gh-pages` branch that the CLI owns and squashes**: it would keep the history small, but hides the
  data from the normal branch. Deferred.
- **Hand-curated JSON**: easy to break, and it would skip cleaning and the secret scan.

## Consequences

- History, diffs, reverts and backups come for free with git.
- The repo only grows, since every video stays in history. Media is capped at 2 MB per file and 8 files
  per run, and Godot engines are stored once (0008).
- A schema change means a migration or a re-import. The viewer tolerates older runs, for example a
  missing `kind` is treated as `godot`, and a missing `harness` as pi.
