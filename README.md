# llm-bench

Run one prompt through several LLMs at every reasoning-effort level, on your own machine, and publish the
results side by side as a static site: what each model made (a playable Godot game, or images and
videos), its full agent transcript, the source it wrote, and what it cost.

**Site:** https://fenderog.github.io/llm-bench/

This repo is both the `bench` CLI (`src/bench/`, standard-library Python) and the site (`docs/`, vanilla
JS, no build step, served by GitHub Pages from `main:/docs`). The CLI writes JSON and files into `docs/`,
and the pages render them in the browser. [SPEC.md](SPEC.md) is the full contract; [AGENTS.md](AGENTS.md)
is the starting point for coding agents working on this repo.

## The site

- **Home:** one card per prompt (a *page*), marked Game or Media, with its models and run count.
- **Page:** the prompt and the full brief the agents got, a summary row (the cheapest, fastest and
  fewest-tokens run, how many were verified, total spend), a gallery for image/video pages, and a sortable
  runs table: effort shown as a meter, the best values starred, your ranking (🥇🥈🥉) first. Click a row
  to play its game or see its files inline. On phones the table becomes a list of cards.
- **Run:** the output (game or files), a switcher to jump between the prompt's other runs, stat tiles
  ranked against the other runs ("cheapest of 11"), and tabs for the transcript (every tool call, with
  errors and edits highlighted), the source files and all metrics. Tabs can be linked (`#transcript`).
- **Compare:** every run of a prompt in a grid, with its game or files, key metrics and the best starred.

Games play in a sandboxed iframe (`allow-scripts` without `allow-same-origin`) and only after a click.
Fullscreen links open the same sandbox in `play.html`. Model-made SVGs are only ever shown as images,
so any script in them can't run. The viewer uses local assets, including its pinned Markdown parser,
and enforces a same-origin Content Security Policy. Light and dark mode.

## Running a benchmark

```sh
uv run bench run "a spinning low-poly windmill in a small field" -m openai-codex/gpt-6-sol:low..high
```

This runs one agent per model × effort level, in parallel, on this machine. Each result is checked, and
everything is imported into one page. Nothing is pushed until you run `bench publish` (or pass
`--publish`); preview first with `bench serve`.

- `-m MODEL[:LEVELS]` can be repeated. LEVELS can be `low,high`, `low..max`, `all`, or `off`. With no
  suffix, it runs every level the model supports except `off`. `-e LEVELS` sets the default for every
  model without a suffix.
- Every model and level is checked against the harness before anything starts (so a typo or an
  unsupported level fails up front). `bench models [SEARCH]` lists models and their levels.
- It shows the planned runs and asks for confirmation. `-n/--dry-run` only shows the plan; `-y/--yes`
  skips the question.
- `-p/--page`, `-t/--title`, `-j N` (maximum agents at once), `-T/--timeout 30m`, and `-b/--brief FILE` (your
  own brief template, with `{prompt}` replaced by the prompt). Every long option has a single-dash short form;
  `bench run -h` lists them.
- Ctrl-C stops every running agent. `bench run --resume <batch dir>` finishes the batch without rerunning
  agents that already completed.

Each agent gets your prompt verbatim plus a fixed brief for the kind of task (`src/bench/kinds/<kind>.md`), and
works in an empty folder (`<run id>/work/`) under `[run].dir` (default `~/dev/bench-runs`, set in `bench.toml`).

### Claude Code as the harness

Models run through [pi](https://github.com/earendil-works/pi) by default. Prefix a model with `claude-code:` to run it
through Claude Code instead; one batch (or model set) can mix both, so the same model can be compared across
harnesses:

```sh
uv run bench run "a voxel horse" -m claude-code:claude-opus-5-5:high -m openai-codex/gpt-6-sol:high
uv run bench models --harness claude-code        # its models and effort levels
```

Claude Code models: `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-sonnet-5`,
`claude-haiku-4-5` (or `fable`,
`opus`, `sonnet`, `haiku`), at low, medium, high, xhigh or max. Each run is one direct agent with only file and
shell tools, like pi: no sub-agents, web, skills or scheduling, and none of your CLAUDE.md, memory, plugins, hooks or
MCP servers (your login is used). Its cost is Claude Code's estimate at API prices, also on a subscription.

### Pinning the OpenRouter upstream

For a pi `openrouter/` model, `@slug` pins which upstream provider serves the run, so the same model
can be benchmarked on different upstreams side by side on one page:

```sh
uv run bench run "a voxel horse" -m openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8:low \
                   -m openrouter/deepseek/deepseek-v4.1-flash@fireworks:low
```

Slugs are OpenRouter's endpoint tags, variants included (`deepinfra/fp8`, `fireworks/us`); list them with
`curl -s https://openrouter.ai/api/v1/models/<model id>/endpoints`. `@deepinfra,fireworks` lets OpenRouter pick among the listed upstreams. Pinning uses fallbacks off,
so the run really used what its name says; the upstream is part of the recorded model name
(`…flash@deepinfra`, shown as a `via …` chip) and `route.requested`/`route.served` are on the run's
Metrics tab. Works in `-m`, `--set` entries and set files alike; anything else with `@` is an error.

Cost: every OpenRouter run's cost, pinned or not, is what OpenRouter actually charged (reported in each
response), not pi's estimate, which prices every OpenRouter call at one catalog rate whatever upstream served
it and came out 2–7× too low on real runs. Both are on the Metrics tab (`route.cost_usd`, `route.pi_cost_usd`),
with the upstream(s) that served the run (`route.served`). With BYOK (your own provider key in OpenRouter)
the reported cost is only OpenRouter's fee.

### Adding runs to an existing page

Name the page and leave out the prompt; its prompt and kind are reused:

```sh
uv run bench run --page an-svg-of-a-chair-holding -m openrouter/deepseek/deepseek-v4.1-flash:low,high
```

Existing runs, the title and your ranking stay as they are; the new runs are added (unranked). Because a
page shows one prompt for all its runs, giving a *different* prompt for an existing page is refused;
pass `--change-prompt` if you really mean to replace it for the whole page.

### Model sets

Save a list of models and levels once and run it with `--set NAME` (or `-s`) instead of repeating `-m`:

```toml
# bench.toml
[sets]
cheap = ["openai-codex/gpt-6-luna:minimal,low", "openrouter/deepseek/deepseek-v4.1-flash:low..high"]
```

```sh
uv run bench run "a windmill" --set cheap
```

Entries are exactly what `-m` takes. `--set` also accepts a file path with one `MODEL[:LEVELS]` per line
(`#` starts a comment). Sets can be repeated and combined with `-m`, and `-e` applies to entries without
levels.

### Games (default), images/videos (`--kind media`) and web pages (`--kind web`)

**Godot games** (`--kind godot`, the default): each project is exported to a web build and booted in
headless Chrome to check it runs. The Godot engine (~38 MB) is stored once in `docs/engines/` and shared
by every run, so a run adds only a few hundred KB.

**Images and videos** (`--kind media`):

```sh
uv run bench run --kind media "a pelican riding a bicycle, as a hand-written SVG" -m openai-codex/gpt-6-sol
```

The agent saves its result in `./output/`: one or more images (`.png .jpg .webp .gif .svg`) and/or videos
(`.mp4 .webm`), at most 8 files of up to 2 MB each, and videos of at most 10 seconds. How it makes them is
up to your prompt ("hand-written SVG", "use Python", ...). The brief lists the tools installed on this
machine, from `[run].tools` in `bench.toml`, with their versions. Afterwards every file is checked with
ffprobe; videos are trimmed to 10 s and re-encoded to H.264 mp4 when needed and get a poster frame, and
oversized images become JPEG. Problems are shown on the run, not fatal.

**Web pages** (`--kind web`):

```sh
uv run bench run --kind web "a running voxel horse with three.js" -m openai-codex/gpt-6-sol
```

The agent writes `index.html` plus ES modules and may `npm install` packages (three.js, ...) and import them by
name. Afterwards esbuild bundles every script and stylesheet the page references, with everything they import,
into one self-contained `index.html` (typically a few hundred KB with three.js). That file is then loaded in
headless Chrome inside the same sandboxed iframe the site uses, with the network blocked: a page that fetches
anything from outside, or needs localStorage, fails verification. `node_modules/` is never published.

A page holds one kind: a media prompt can't be added to a Godot page.

## Ranking runs

Rank the runs of a page yourself, in the browser:

```sh
uv run bench serve        # then open http://localhost:8000 and pick a page
```

When the site is served by `bench serve`, each row of the runs table gets a rank picker (– or 1st, 2nd, …;
ties allowed). Every change is saved to `docs/data/<page>/ranking.json` right away. `bench publish` puts
it online, where it's read-only: ranked runs sort first and show 🥇🥈🥉 (then #4, #5…) on the page,
gallery, compare and run pages. The published site can't change rankings; only `bench serve` on your
machine accepts them.

## Importing runs

`bench run` imports its batch when it finishes. To publish a run (or a whole batch) again, for example after
`bench rm`:

```sh
uv run bench import ~/dev/bench-runs/2026-09-29-171151-create-a-rubik-s-cube-in-3js   # a batch: one run per directory
uv run bench import ~/dev/bench-runs/<batch>/<run id>                                  # or a single run
uv run bench serve                  # preview at http://localhost:8000 (served like GitHub Pages)
uv run bench publish -m "voxel horse: gpt-6-sol"   # git add docs && commit && push
```

`import` options:
- `--page SLUG` sets the page instead of the one recorded in the run; `--title` sets its title.
- `--dry-run` shows what would be written without writing it.
- `--redact` masks secrets instead of aborting.
- `--allow-threads` accepts threaded Godot exports, which only play in full screen.

Every import (including the one at the end of `bench run`) cleans the transcript and every other published text file first: encrypted
reasoning blobs and machine-specific keys are removed, and home and volume paths are rewritten (see
`[clean]` in `bench.toml`). Then everything is secret-scanned, and any hit aborts before anything is
written.

## Other commands

- `bench list` lists pages and their runs.
- `bench rm <page> [<run>]` removes a run, or a whole page.
- `bench rebuild` regenerates the indexes and drops unused engines.
- `bench publish [-m MSG]` commits `docs/` and pushes; GitHub Pages is live about a minute later.

Only people with write access to this repo can publish to the site. Anyone else running `bench publish`
gets a permission error; to contribute runs they'd fork the repo and open a pull request.

## Requirements

- [uv](https://docs.astral.sh/uv/) to run the CLI (`uv run bench ...`). To type just `bench`, install it once from the
  repo root with `uv tool install --editable '.[verify]'`. It stays linked to this checkout, so code changes apply
  without reinstalling. Commands still run against the site in the current directory (or `--root`).
- [pi](https://github.com/earendil-works/pi) as the default agent harness; [Claude Code](https://claude.com/claude-code)
  (`claude`, logged in) for `claude-code:` models.
- `godot` on PATH with the matching web export templates (game runs).
- `ffmpeg` and `ffprobe` on PATH (media runs).
- `esbuild` and `npm` on PATH (web runs): `brew install esbuild node`.
- Google Chrome and Playwright for checking game builds and for the viewer tests (`pip install
  bench[verify]`; already in the dev dependencies).

## Tests

```sh
uv run pytest    # ~40s: CLI (bench run uses a fake pi, no model calls), media checks (ffmpeg),
                 # viewer (Playwright on installed Chrome), ranking, Godot export + boot
```

The integration test serves the published voxel-horse page and checks its real Godot builds boot in the sandbox.
