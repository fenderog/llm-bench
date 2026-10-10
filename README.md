# llm-bench

Give one prompt to several AI models, at each effort level, on your own computer. Then publish the
results side by side as a static site: what each model made (a playable Godot game, images/videos,
or a web page), its full transcript, the files it wrote, and what it cost.

**Site:** https://fenderog.github.io/llm-bench/

This repo holds both the `bench` tool (`src/bench/`, plain Python) and the site (`docs/`, plain
JS, no build step, hosted by GitHub Pages from `main:/docs`). The tool writes files into `docs/`,
and the pages show them in the browser. [SPEC.md](SPEC.md) has the full details; [AGENTS.md](AGENTS.md)
is the guide for coding agents working on this repo.

## The site

- **Home:** one card per prompt (a *page*), marked Game, Media or Web, with its models and run count.
- **Page:** the prompt and the full brief the agents got, a short summary (cheapest, fastest,
  fewest tokens, how many passed checks, total cost), a gallery for image/video pages, and a runs table
  you can sort. Effort shows as a meter, best values get a star, your ranking (🥇🥈🥉) comes first.
  Click a row to play its game or see its files. On phones the table becomes cards.
- **Run:** the output (game, files or web page), buttons to jump to the other runs for the same prompt,
  stats compared to the other runs ("cheapest of 11"), and tabs for the transcript (every tool call,
  with errors and edits marked), the source files, and all metrics. You can link to a tab (`#transcript`).
- **Compare:** every run for a prompt in a grid, with its game, files or web page, key numbers,
  and stars for the best.

Games play in a locked-down frame and only after you click. Fullscreen links use the same safe
frame in `play.html`. SVGs made by models are only shown as images, so scripts inside them cannot run.
The viewer uses only local files and blocks outside content. Light and dark mode.

## Running a benchmark

```sh
uv run bench run "a spinning low-poly windmill in a small field" -m openai-codex/gpt-6-sol:low..high
```

This runs one agent per model × effort level, at the same time, on this machine. Finished work
is packed up and, when possible, checked. Failed and timed-out tries are saved too.
Nothing goes online until you run `bench publish` (or pass `--publish`). Preview first with `bench serve`.

- `-m MODEL[:LEVELS]` can be repeated. LEVELS can be `low,high`, `low..max`, `all`, or `off`. With no
  suffix, it runs all levels the model supports except `off`. `-e LEVELS` sets the default for all
  models without a suffix.
- All models and levels are checked before anything starts, so typos fail fast.
  `bench models [SEARCH]` lists models and their levels.
- It shows the plan and asks you to confirm. `-n/--dry-run` only shows the plan;
  `-y/--yes` skips the question (needed for scripts).
- `-p/--page`, `-t/--title`, `-j N` (max agents at once), `-T/--timeout 30m`, and `-b/--brief FILE`
  (your own brief, with `{prompt}` replaced by the prompt). `bench run -h` lists them all.
- Ctrl-C stops all running agents. `bench run --resume <batch dir>` finishes a batch without
  redoing agents that already finished.

Each agent gets your prompt as-is plus a fixed brief for the task type (`src/bench/kinds/<kind>.md`),
and works in its own empty folder (`<run id>/work/`) under `[run].dir` (default `~/dev/bench-runs`,
set in `bench.toml`).

### Claude Code as the harness

Models run through [pi](https://github.com/earendil-works/pi) by default. Put `claude-code:` in front
to run through Claude Code instead. One batch can mix both, so you can compare the same model
across harnesses:

```sh
uv run bench run "a voxel horse" -m claude-code:claude-opus-5-5:high -m openai-codex/gpt-6-sol:high
uv run bench models --harness claude-code        # its models and effort levels
```

Claude Code models: `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-sonnet-5`,
`claude-haiku-4-5` (or `fable`, `opus`, `sonnet`, `haiku`), at low, medium, high, xhigh or max.
Each run is one plain agent with only file and shell tools, like pi: no sub-agents, web, skills
or scheduling, and none of your CLAUDE.md, memory, plugins, hooks or MCP servers (your login is used).
Its cost is Claude Code's estimate at API prices, also on a subscription.

### Pinning the OpenRouter upstream

For a pi `openrouter/` model, `@slug` picks which provider serves the run, so you can compare
the same model on different providers side by side on one page:

```sh
uv run bench run "a voxel horse" -m openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8:low \
                   -m openrouter/deepseek/deepseek-v4.1-flash@fireworks:low
```

Slugs are OpenRouter's endpoint tags, variants included (`deepinfra/fp8`, `fireworks/us`). List them with
`curl -s https://openrouter.ai/api/v1/models/<model id>/endpoints`. `@deepinfra,fireworks` lets OpenRouter
pick from the list. Pinning turns off fallbacks, so the run really used the named provider. The provider
is part of the saved model name (`…flash@deepinfra`, shown as a `via …` chip) and `route.requested` /
`route.served` are on the run's Metrics tab. Works in `-m`, `--set` entries and set files alike;
any other use of `@` is an error.

Cost: every OpenRouter run's cost, pinned or not, is what OpenRouter really charged (from each
response), not pi's guess, which prices all OpenRouter calls at one rate and was 2–7× too low on
real runs. Both numbers are on the Metrics tab (`route.cost_usd`, `route.pi_cost_usd`),
with the providers that served the run (`route.served`). With BYOK (your own provider key in OpenRouter)
the shown cost is only OpenRouter's fee.

### Adding runs to an existing page

Find the page slug in its URL (or with `uv run bench list`), check the new model's ID and levels,
then name the page and skip the prompt. Its prompt and kind are reused:

```sh
uv run bench models deepseek                         # lists matching model IDs and supported levels
uv run bench run --dry-run --page an-svg-of-a-chair-holding -m openrouter/deepseek/deepseek-v4.1-flash:low
uv run bench run --page an-svg-of-a-chair-holding -m openrouter/deepseek/deepseek-v4.1-flash:low
uv run bench serve                                   # preview at http://localhost:8000
uv run bench publish -m "Add DeepSeek run to chair page"  # commit docs/ and push, if you have write access
```

The real `bench run` costs money; `--dry-run` does not. Without `:LEVELS`, `-m` runs all
supported levels except `off`, not just one. Old runs, the title and your ranking stay as they are;
new runs start unranked. Re-importing the same run ID replaces that run. Since a page shows one
prompt for all its runs, a *different* prompt for an old page is refused. Pass
`--change-prompt` if you really want to replace it for the whole page.

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

Entries are the same as `-m`. `--set` also takes a file path with one `MODEL[:LEVELS]` per line
(`#` starts a comment). Sets can be repeated and mixed with `-m`, and `-e` applies to entries
without levels.

### Games (default), images/videos (`--kind media`) and web pages (`--kind web`)

**Godot games** (`--kind godot`, the default): each project is exported to a web build and started
in headless Chrome to check it runs. The Godot engine (~38 MB) is stored once in `docs/engines/` and shared
by all runs, so a run adds only a few hundred KB.

**Images and videos** (`--kind media`):

```sh
uv run bench run --kind media "a pelican riding a bicycle, as a hand-written SVG" -m openai-codex/gpt-6-sol
```

The agent saves its work in `./output/`: one or more images (`.png .jpg .jpeg .webp .gif .svg`) and/or
videos (`.mp4 .webm .mov`). Up to 8 files are kept, each at most 2 MB after processing; videos max
10 seconds. How it makes them is up to your prompt ("hand-written SVG", "use Python", ...).
The brief lists the tools on this machine, from `[run].tools` in `bench.toml`, with their
versions. Then images and videos are checked with ffprobe, while SVGs are parsed as XML;
videos are cut to 10 s and re-saved to H.264 mp4 when needed, and get a still image preview. Big
non-GIF images become JPEG. Good files are still published if others fail; problems show
on the run, and checks fail if any file has an error.

**Web pages** (`--kind web`):

```sh
uv run bench run --kind web "a running voxel horse with three.js" -m openai-codex/gpt-6-sol
```

The agent writes `index.html` plus ES modules and may `npm install` packages (three.js, ...) and import them by
name. Then esbuild packs local module scripts and stylesheets with their imports into one file,
and local classic script files are inlined as data URLs (keeping their globals). The result is one
`index.html` (max 20 MB). Remote URLs and import maps stay as they are, but the headless-Chrome check
loads the page offline inside the same safe frame the site uses: a page that loads anything from
outside, or needs localStorage, fails the check. `node_modules/` is never published.

A page holds one kind: a media prompt can't be added to a Godot page.

## Ranking runs

Rank the runs of a page yourself, in the browser:

```sh
uv run bench serve        # then open http://localhost:8000 and pick a page
```

When served by `bench serve`, each row of the runs table gets a rank picker (– or 1st, 2nd, …;
ties allowed). Each change is saved to `docs/data/<page>/ranking.json` at once. `bench publish` puts
it online, where it can't be changed: ranked runs sort first and show 🥇🥈🥉 (then #4, #5…) on the page,
gallery, compare and run pages. The live site can't change rankings; only `bench serve` on your
machine can.

## Importing runs

`bench run` imports its batch when done. To publish a run (or a whole batch) again, for example after
`bench rm`:

```sh
uv run bench import ~/dev/bench-runs/2026-09-29-171151-create-a-rubik-s-cube-in-3js   # a batch: one run per directory
uv run bench import ~/dev/bench-runs/<batch>/<run id>                                  # or a single run
uv run bench serve                  # preview at http://localhost:8000 (served like GitHub Pages)
uv run bench publish -m "voxel horse: gpt-6-sol"   # git add docs && commit && push
```

`import` options:
- `--page SLUG` sets the page instead of the one saved in the run; `--title` sets its title.
- `--dry-run` shows what would be written without writing it.
- `--redact` masks secrets instead of stopping.
- `--allow-threads` accepts threaded Godot exports, which only play in full screen.

Every import (including the one at the end of `bench run`) cleans the transcript and all other text files first:
hidden reasoning data and machine-only keys are removed, and home and volume paths are rewritten (see
`[clean]` in `bench.toml`). Then all files are scanned for secrets, and any hit stops the import before
anything is written.

## Other commands

- `bench list` lists pages and their runs.
- `bench rm <page> [<run>]` deletes a run, or a whole page.
- `bench rename <page> <new-slug> [-t TITLE]` moves a page to a new slug. The title follows only if it was
  built from the old slug (or you pass `-t`).
- `bench rebuild` rebuilds the indexes and drops unused engines.
- `bench publish [-m MSG]` commits `docs/` and pushes; GitHub Pages is live about a minute later.

Only people with write access to this repo can publish to the site. Anyone else who runs `bench publish`
gets a permission error. To add runs without access, fork the repo and open a pull request.

## Requirements

- [uv](https://docs.astral.sh/uv/) to run the tool (`uv run bench ...`). To type just `bench`, install it once from the
  repo root with `uv tool install --editable '.[verify]'`. It stays linked to this checkout, so code changes apply
  with no reinstall. Commands still use the site in the current folder (or `--root`).
- [pi](https://github.com/earendil-works/pi) as the default agent; [Claude Code](https://claude.com/claude-code)
  (`claude`, logged in) for `claude-code:` models.
- `godot` on PATH with matching web export templates (game runs).
- `ffmpeg` and `ffprobe` on PATH (media runs).
- `esbuild` and `npm` on PATH (web runs): `brew install esbuild node`.
- Google Chrome and Playwright for browser checks of Godot and web runs, and for the viewer tests
  (`pip install bench[verify]`; already in the dev tools). Without Playwright, browser checks
  are skipped and the run's `output.verified` is null, not false.

## Tests

```sh
uv run pytest    # ~40s: tool tests (bench run uses a fake pi, no model calls), media checks (ffmpeg),
                 # viewer (Playwright on installed Chrome), ranking, Godot export + boot
```

The full test serves the published voxel-horse page and checks its real Godot builds start in the safe frame.
