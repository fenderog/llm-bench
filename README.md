# llm-bench

LLM benchmark runs published as a static GitHub Pages site: playable Godot web builds, full agent
transcripts, the source each model wrote, and cost/token metrics, side by side per effort level.

**Site:** https://fenderog.github.io/llm-bench/

This repo contains both the `bench` CLI (`src/bench/`, standard-library Python) and the site
(`docs/`, vanilla JS with no build step). The CLI writes JSON and files into `docs/`, and the pages
render it in the browser. See [SPEC.md](SPEC.md) for the data contract.

## Running a benchmark

```sh
uv run bench run "a spinning low-poly windmill in a small field" -m openai-codex/gpt-6-sol:low..high
```

This runs one agent per model × effort level on this machine, in parallel. Each Godot project is
exported and checked in headless Chrome, and everything is imported into one page. Nothing is pushed
until you run `bench publish` or pass `--publish`.

- `-m MODEL[:LEVELS]` can be repeated. LEVELS can be `low,high`, `low..max`, `all`, or `off`. With no
  suffix, it runs every level the model supports except `off`. `-e LEVELS` sets the default for every
  `-m` without a suffix.
- Every level is checked against the harness before anything starts. `bench models [SEARCH]` lists
  models and their levels.
- Before starting, it shows the planned runs and asks for confirmation. `--dry-run` only shows the plan,
  and `--yes` skips the question.
- `--page`, `--title`, `-j N` (maximum agents at once), `--timeout 30m`, and `--brief FILE` (your own
  brief template, with `{prompt}` replaced by the prompt).
- Ctrl-C stops every running agent. `bench run --resume <batch dir>` finishes the batch without rerunning
  agents that already completed.

Each agent gets your prompt verbatim plus a fixed set of Godot rules (`src/bench/briefs/godot.md`), and
runs in an empty folder under `[run].dir` (default `~/dev/bench-runs`, set in `bench.toml`).

Requirements:
- [pi](https://github.com/earendil-works/pi) is the harness, and the only one for now.
- `godot` must be on PATH, with the matching web export templates installed.
- Google Chrome and Playwright are only needed for the check step (`pip install bench[verify]`; they're
  already in the dev dependencies).

## Importing existing runs

```sh
uv run bench import ~/dev/effort-runs/2026-09-26-001158-gpt6sol-voxel-horse   # one run per effort level
uv run bench serve                  # preview at http://localhost:8000 (served like GitHub Pages)
uv run bench publish -m "voxel horse: gpt-6-sol"   # git add docs && commit && push
```

Other commands:
- `bench list` lists pages and their runs.
- `bench rm <page> [<run>]` removes a run, or a whole page.
- `bench rebuild` regenerates the indexes and drops unused engines.

`import` options:
- `--page SLUG` sets the page instead of deriving it from the folder name.
- `--dry-run` shows what would be written without writing it.
- `--redact` masks secrets instead of aborting.
- `--allow-threads` accepts threaded Godot exports, which only play in full screen.

## What `import` does

- **Godot engine dedupe:** the 38 MB engine is stored once in `docs/engines/<sha12>/`, and each run's
  `index.html` is rewritten to load it. A run adds about 400 KB.
- **Session cleaning:** encrypted reasoning blobs and machine-specific keys are removed. Home and volume
  paths are rewritten (see `bench.toml`).
- **Secret scan:** any hit aborts the import before anything is written.
- Games play in a sandboxed iframe (`allow-scripts` without `allow-same-origin`), and only after a click.

## Tests

```sh
uv run pytest    # CLI (bench run uses a fake pi, no model calls), viewer (Playwright on installed Chrome), Godot export + boot
```

The integration test imports the real voxel-horse run and is skipped when that folder isn't present.
