# llm-bench

LLM benchmark runs published as a static GitHub Pages site: playable Godot web builds, full agent
transcripts, the source each model wrote, and cost/token metrics, side by side per effort level.

**Site:** https://fenderog.github.io/llm-bench/

This repo contains both the `bench` CLI (`src/bench/`, standard-library Python) and the site
(`docs/`, vanilla JS with no build step). The CLI writes JSON and files into `docs/`, and the pages
render it in the browser. See [SPEC.md](SPEC.md) for the data contract.

## Usage

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
uv run pytest    # CLI, viewer (Playwright on installed Chrome), and an end-to-end Godot boot test
```

The integration test imports the real voxel-horse run and is skipped when that folder isn't present.
