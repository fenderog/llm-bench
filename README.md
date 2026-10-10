# art-crit

A crit for LLMs: pick a visual or spatial prompt, run it across models and effort levels, and hang
the results side by side. It's for the comparisons a score can't make: which horse looks like a
horse, which game feels right, which pelican can actually ride a bike.
For every run you get the thing the model made — a playable Godot game, images or video,
or a packaged web page — plus the full transcript, the source files, and what it cost.

**Live site:** https://fenderog.github.io/art-crit/

This repo is two things: the `art-crit` CLI in `src/art_crit/` (plain Python, stdlib only) and the
site in `docs/` (plain JS, no build step, hosted from `main:/docs` on GitHub Pages). The CLI
writes files to `docs/`; the site renders them. [SPEC.md](SPEC.md) is the full contract.
[AGENTS.md](AGENTS.md) is where coding agents should start.

## What you'll see on the site

- **Home:** one card per prompt — called a *page* — labeled Game, Media, or Web, with its models and run count.
- **Page:** the prompt, the exact brief the agents saw, a summary (cheapest, fastest, fewest
  tokens, how many passed checks, total spend), a gallery for media pages, and a sortable runs
  table. Effort is a meter, best numbers get a star, your own ranking comes first. Click a row
  to play the game or open the files. On phones the table collapses into cards.
- **Run:** the output front and center, quick links to the same prompt's other runs, stats in
  context ("cheapest of 11"), and tabs for transcript, source, and metrics. The transcript shows
  every tool call with errors and edits called out. Tabs are linkable (`#transcript`).
- **Compare:** all runs for a prompt in one grid, with outputs, key numbers, and stars for the best.

Safety notes, briefly: games only start when you click, inside a sandboxed frame. Fullscreen
uses the same sandbox via `play.html`. Model-made SVGs render as images only, so embedded scripts
never run. The viewer ships its own assets (including the Markdown parser) and runs under a
same-origin CSP. Light and dark mode both work.

## Run a benchmark

```sh
uv run art-crit run "a spinning low-poly windmill in a small field" -m openai-codex/gpt-6-sol:low..high
```

That spins up one agent per model × effort level, in parallel, on your machine. When they finish,
their work is packaged and checked where a check exists. Failures and timeouts are kept too —
they're part of the comparison. Preview with `art-crit serve`; nothing goes public until
`art-crit publish` (or pass `--publish` to publish each run as it lands, handy for long batches).

A few things worth knowing:

- `-m MODEL[:LEVELS]` repeats. Levels look like `low,high`, `low..max`, `all`, or `off`.
  Leave the suffix off and you get every level except `off`. `-e LEVELS` sets the fallback for
  models without one.
- Models and levels are validated up front, so a typo fails before you spend anything.
  `art-crit models [SEARCH]` shows what's available.
- You'll see the plan and confirm it. `-n/--dry-run` prints the plan and stops.
  `-y/--yes` skips the prompt for scripts.
- Useful flags: `-p/--page`, `-t/--title`, `-j N` (how many agents at once),
  `-T/--timeout 30m`, `-b/--brief FILE` (your own brief template, `{prompt}` is your prompt),
  `-P/--publish`. `art-crit run -h` has the full list.
- Ctrl-C stops everything. `art-crit run --resume <batch dir>` picks up a batch without
  redoing finished agents.

Each agent starts in an empty `<run id>/work/` folder under `[run].dir`
(`~/dev/art-crit-runs` by default, configured in `art-crit.toml`) and gets your prompt verbatim
plus the fixed brief for that task type in `src/art_crit/kinds/<kind>.md`.

### Using Claude Code

Default harness is [pi](https://github.com/earendil-works/pi). Prefix with `claude-code:` to use
[Claude Code](https://claude.com/claude-code) instead — you can mix both in one batch to compare
harnesses head to head:

```sh
uv run art-crit run "a voxel horse" -m claude-code:claude-opus-5-5:high -m openai-codex/gpt-6-sol:high
uv run art-crit models --harness claude-code
```

Claude Code models are `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5`,
`claude-sonnet-5`, and `claude-haiku-4-5` (`fable`, `opus`, `sonnet`, `haiku` work as shorthand),
at low, medium, high, xhigh, or max. Runs are single agents with file and shell tools only —
no subagents, web access, skills, scheduling, CLAUDE.md, memory, plugins, hooks, or MCP servers.
It uses your login, and cost is Claude Code's API-price estimate, subscription included.

### Pinning an OpenRouter provider

For `openrouter/` models, `@slug` locks the run to a specific upstream provider, so you can put
the same model on two providers on the same page:

```sh
uv run art-crit run "a voxel horse" -m openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8:low \
                   -m openrouter/deepseek/deepseek-v4.1-flash@fireworks:low
```

Slugs are OpenRouter endpoint tags, variants included (`deepinfra/fp8`, `fireworks/us`). Find them with
`curl -s https://openrouter.ai/api/v1/models/<model id>/endpoints`. Comma-separate to let OpenRouter
choose within your list (`@deepinfra,fireworks`). Pinning disables fallbacks, so the name on the run
is what actually served it — recorded in the model name (`…flash@deepinfra`, shown as a `via …` chip)
and in `route.requested` / `route.served` on the Metrics tab. Works in `-m`, `--set`, and set files;
`@` anywhere else is an error.

On cost: OpenRouter runs report what OpenRouter actually charged per response, not pi's estimate.
pi prices every OpenRouter call at one catalog rate, which ran 2–7× low in practice. Both figures
are on the Metrics tab (`route.cost_usd`, `route.pi_cost_usd`) alongside what served the run
(`route.served`). With BYOK (your own provider key), the reported cost is just OpenRouter's fee.

### Add runs to an existing page

Grab the page slug from its URL (or `uv run art-crit list`), confirm the model ID and levels, then
pass `--page` and skip the prompt — the page's prompt and kind carry over:

```sh
uv run art-crit models deepseek
uv run art-crit run --dry-run --page an-svg-of-a-chair-holding -m openrouter/deepseek/deepseek-v4.1-flash:low
uv run art-crit run --page an-svg-of-a-chair-holding -m openrouter/deepseek/deepseek-v4.1-flash:low
uv run art-crit serve
uv run art-crit publish -m "Add DeepSeek run to chair page"
```

Real runs cost money; `--dry-run` is free. Bare `-m` means all levels except `off`. Existing runs,
the title, and your rankings are left alone; new runs arrive unranked, and re-importing a run ID
replaces that run. A page has one prompt, so passing a different one is refused — use
`--change-prompt` if you're deliberately rewriting it for the whole page.

### Model sets

If you reuse the same lineup, save it once and pass `--set NAME` (or `-s`):

```toml
# art-crit.toml
[sets]
cheap = ["openai-codex/gpt-6-luna:minimal,low", "openrouter/deepseek/deepseek-v4.1-flash:low..high"]
```

```sh
uv run art-crit run "a windmill" --set cheap
```

Entries take the same form as `-m`. `--set` also accepts a file (one `MODEL[:LEVELS]` per line,
`#` for comments). Sets compose with each other and with `-m`; `-e` fills in entries missing levels.

### The three kinds of pages

**Godot games** (`--kind godot`, the default) get exported to a web build and booted in headless
Chrome to prove they run. The engine (~38 MB) lives once in `docs/engines/` and is shared, so each
run adds only a few hundred KB.

**Images and video** (`--kind media`):

```sh
uv run art-crit run --kind media "a pelican riding a bicycle, as a hand-written SVG" -m openai-codex/gpt-6-sol
```

The agent drops results in `./output/`: images (`.png .jpg .jpeg .webp .gif .svg`) and/or video
(`.mp4 .webm .mov`). Anything else there is ignored, though text files are kept as source. Limits
are 8 files, 2 MB each after processing, 10 seconds per video. The *how* is up to your prompt
("hand-written SVG", "use Python", …). The brief lists this machine's tools from `[run].tools` in
`art-crit.toml`, with versions. Afterward, rasters and video go through ffprobe and SVGs through an XML
parse; videos are trimmed to 10 s, re-encoded to H.264 mp4 if needed, and given a poster frame, and
oversized non-GIF rasters become JPEG. Good files still publish when others fail; per-file problems
appear on the run, and verification fails if any image or video is unreadable or over the limits.

**Web pages** (`--kind web`):

```sh
uv run art-crit run --kind web "a running voxel horse with three.js" -m openai-codex/gpt-6-sol
```

The agent writes `index.html` plus ES modules, `npm install`s what it needs (three.js, …), and imports
packages by name. esbuild then bundles local module scripts, stylesheets, and their imports, and inlines
local classic scripts as data URLs to preserve their globals — leaving you with a single `index.html`
(max 20 MB). Remote URLs and import maps stay untouched, but the check loads the page offline in the
same sandboxed frame the site uses. Anything fetched from outside, or any need for localStorage, fails
verification. `node_modules/` never ships.

One kind per page: you can't add a media prompt to a Godot page, and so on.

## Rank runs

Rankings are yours, done in the browser:

```sh
uv run art-crit serve        # open http://localhost:8000, pick a page
```

Under `art-crit serve`, each runs-table row gets a picker (– or 1st, 2nd, …, ties fine). It saves to
`docs/data/<page>/ranking.json` as you go. `art-crit publish` puts it online read-only: ranked runs
sort first and show 🥇🥈🥉 (then #4, #5…) across the page, gallery, compare, and run views. The live
site can't write rankings — only your local `art-crit serve` can.

## Import runs

`art-crit run` imports its batch when it finishes. To re-publish a run or batch — say after `art-crit rm`:

```sh
uv run art-crit import ~/dev/art-crit-runs/2026-09-29-171151-create-a-rubik-s-cube-in-3js   # a batch
uv run art-crit import ~/dev/art-crit-runs/<batch>/<run id>                                  # one run
uv run art-crit serve                  # preview at http://localhost:8000, served like Pages
uv run art-crit publish -m "voxel horse: gpt-6-sol"
```

Options: `--page SLUG` overrides the recorded page, `--title` sets its title, `--dry-run` previews
without writing, `--redact` masks secrets instead of aborting, `--allow-threads` permits threaded
Godot exports (fullscreen-only playback).

Every import cleans first: hidden reasoning blobs and machine-specific keys go, home and volume paths
get rewritten per `[clean]` in `art-crit.toml`, then everything is secret-scanned. A hit stops the import
before anything is written.

## Other commands

- `art-crit list` — pages and their runs.
- `art-crit rm <page> [<run>]` — delete a run, or a whole page.
- `art-crit rename <page> <new-slug> [-t TITLE]` — move a page. The title follows only if it came
  from the old slug, unless you pass `-t`.
- `art-crit rebuild` — regenerate indexes, drop unused engines.
- `art-crit publish [-m MSG]` — commit `docs/` and push. Pages goes live about a minute later.

Publishing to this site needs write access — otherwise you'll get a permission error. Without it,
fork and open a pull request.

## Requirements

- [uv](https://docs.astral.sh/uv/) — run everything as `uv run art-crit ...`. For a bare `art-crit`,
  install once from the repo root: `uv tool install --editable '.[verify]'`. It stays linked to
  this checkout, so edits apply without reinstalling. Commands act on the current directory (or `--root`).
- [pi](https://github.com/earendil-works/pi) for default runs; [Claude Code](https://claude.com/claude-code)
  (`claude`, logged in) for `claude-code:` models.
- `godot` on PATH with matching web export templates (games).
- `ffmpeg` + `ffprobe` on PATH (media).
- `esbuild` + `npm` on PATH (web): `brew install esbuild node`.
- Google Chrome + Playwright for browser checks and viewer tests (`pip install art-crit[verify]`,
  already in dev deps). Without Playwright, browser checks are skipped and `output.verified`
  comes back null rather than false.

## Tests

```sh
uv run pytest    # ~40s: CLI (art-crit run uses a fake pi, so no model spend), media checks,
                 # viewer in Playwright on installed Chrome, ranking, Godot export + boot
```

The integration test serves the published voxel-horse page and boots its real Godot builds in the sandbox.
