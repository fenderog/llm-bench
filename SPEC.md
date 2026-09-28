# llm-bench spec

This repo is both the CLI (`src/bench/`) and the GitHub Pages site (`docs/`, served from `main:/docs`).
The site is static and has no build step. The CLI writes JSON and files into `docs/data/` and `docs/engines/`,
and the viewer pages fetch that JSON in the browser.

Guiding rule: **simple and lean.** The CLI is standard-library Python only (argparse, json, hashlib,
tomllib, http.server, subprocess). The site is vanilla JS ES modules, with one optional CDN dependency
(`marked` for markdown). No frameworks and no bundler.

## Vocabulary

- **Page**: one prompt or task, such as `voxel-horse`.
- **Run**: one model × effort level attempt at a page's task. One `bench import` of an effort-run folder
  adds one run per effort level (usually low, medium, high).
- **Kind**: what a page's runs produce. `godot` = a Godot project, published as a playable web build;
  `media` = image and/or video files. Every run of a page has the page's kind.

## Site layout (the data contract between the CLI and the viewer)

```
docs/
  .nojekyll
  index.html                      # home: list of pages            (reads data/pages.json)
  page.html?p=<slug>              # one page: runs table + gallery (reads data/<slug>/results.json)
  run.html?p=<slug>&r=<run_id>    # one run: tabs Game | Transcript | Source | Metrics
  compare.html?p=<slug>[&r=<id>,<id>]   # side by side: all runs of the page, or just the listed ones
  assets/                         # shared JS/CSS
  engines/<sha12>/godot.wasm      # deduplicated Godot engine files, one dir per unique engine
  engines/<sha12>/godot.js
  engines/<sha12>/godot.audio.worklet.js
  engines/<sha12>/godot.audio.position.worklet.js
  data/
    pages.json                    # [PageSummary]
    <slug>/page.json              # Page
    <slug>/results.json           # [Run], every run.json of the page concatenated, sorted by started_at then effort order
    <slug>/runs/<run_id>/
      run.json                    # Run
      thumb.png                   # optional (godot)
      game/index.html, index.pck, index.png, index.icon.png, index.apple-touch-icon.png   # godot
      media/<file>, media/<name>.poster.jpg                                              # media
      session/conversation.json   # cleaned (see Cleaning)
      session/events.jsonl        # cleaned
      session/status.json         # cleaned
      session/output.md
      source/...                  # project files the model wrote
```

All paths inside JSON are **relative to the run directory** (for Run) or to `docs/` (for PageSummary.thumb).

### PageSummary (element of `data/pages.json`)
```json
{ "slug": "voxel-horse", "title": "Voxel horse", "kind": "godot", "n_runs": 3,
  "models": ["openai-codex/gpt-6-sol"], "updated": "2026-09-26T07:15:57Z",
  "thumb": "data/voxel-horse/runs/gpt-6-sol-high-20260926-001158/thumb.png" }
```
`thumb` is taken from the most recent run that has one (its run's `thumb` path), or `null`.

### Page (`data/<slug>/page.json`)
```json
{ "slug": "voxel-horse", "title": "Voxel horse", "kind": "godot",
  "prompt": "<contents of prompt.md, the originating prompt; refreshed on every import>",
  "final_prompt": "<the full brief each run received: first user message of the cleaned session, ./<level>/ -> ./<effort>/; null if none>",
  "created": "2026-09-26T07:12:42Z", "updated": "2026-09-26T07:15:57Z" }
```

### Run (`run.json`, and each element of `results.json`)
```json
{
  "id": "gpt-6-sol-high-20260926-001158",
  "page": "voxel-horse",
  "model": "openai-codex/gpt-6-sol",
  "effort": "high",
  "kind": "godot",
  "started_at": "2026-09-26T07:12:42Z",
  "source_dir": "2026-09-26-001158-gpt6sol-voxel-horse",
  "verified": true,
  "harness": { "name": "pi", "version": "0.87.1" },
  "state": "complete",
  "error": null,
  "metrics": {
    "duration_ms": 196192, "cost_usd": 0.146, "tool_calls": 16, "turns": 17,
    "tokens_total": 32732, "tokens_input": 25280, "tokens_output": 7452,
    "tokens_reasoning": 3073, "tokens_cache_read": 105984
  },
  "thumb": "thumb.png",
  "game": { "kind": "godot", "entry": "game/index.html", "engine": "41560f8755ed",
            "godot": "4.7.2.stable.official.ed1daf0bf", "threads": false },
  "media": null,
  "session": { "conversation": "session/conversation.json", "events": "session/events.jsonl",
               "status": "session/status.json", "output": "session/output.md" },
  "source": { "root": "source/", "files": ["README.md", "project.godot", "scenes/main.tscn", "scripts/main.gd"] }
}
```
- `game`, `media`, `session`, `source`, and `thumb` can each be `null` when the input doesn't have them.
- `kind` = the model dir's `data.json` → `kind`, default `godot` (runs imported before kinds existed have no
  `kind`; the viewer treats that as `godot`). Importing into a page of another kind is an error.
- `media` (kind `media`) = the items of `media/<level>/manifest.json` (see "bench run" step 6), each
  `{type: "image"|"video", path: "media/<file>", width, height, bytes}` plus, for a video,
  `duration_s, poster: "media/<name>.poster.jpg", transcoded` and `trimmed: true` when it was cut to 10 s.
  Width/height can be `null` for an SVG without a size. `thumb` = the first image's path or the first
  video's poster. `verified` = the manifest's `ok`. SVGs are model-written text, so they are cleaned and
  secret-scanned like source files. The run's `source` holds only text files of at most 512 KB, and never
  `output/`.
- `id` = `<model name after the last "/", lowercased>-<effort>-<YYYYMMDD-HHMMSS from the folder name>`.
- `verified` = `wasm/<level>/verification/verify-report.json` → `.ok`, or `null` if that file is missing.
- `harness` = `data.json` → `harness`; for an old `fe-model-effort-fanout/1` folder without it, `{"name": "pi", "version": null}`.
- `state` = `runs.<level>.state` (`complete` | `failed` | `timeout`), default `complete`.
- `error` = `runs.<level>.error` (a one-line reason: harness exit, timeout, or "Godot export failed: …"), default `null`.
  A run with `state` ≠ `complete` is still imported (it usually has no game).

## Input: an effort-run folder (`fe-model-effort-fanout/1`)

A real example (READ ONLY, never modify): `~/dev/effort-runs/2026-09-26-001158-gpt6sol-voxel-horse/`

```
prompt.md                     # the originating prompt, shown on the page (the subagent brief lives in <level>/conversation.json)
data.json                     # {"schema": "fe-model-effort-fanout/1", "runs": {"low": {...}, "medium": {...}, "high": {...}}, "totals": {...}}
                              #   runs.<level>: model, thinkingLevel, startedAt (epoch ms), durationMs, costUsd, toolCalls, turns,
                              #                 tokens: {input, output, total, reasoning, cacheRead, cacheWrite, ...}
conversation.json, workflow-*.json   # orchestrator-level files: ignored
<level>/                      # the Godot project the model wrote + its session
  conversation.json           # the session: JSON array of entries (session.jsonl is an identical copy, skip it)
  session.jsonl  events.jsonl  status.json  output.md  data.json
  project.godot  README.md  scenes/  scripts/  export_presets.cfg
  .godot/                     # editor cache: skip
wasm/<level>/                 # Godot web export
  index.html index.js index.wasm index.pck index.audio.worklet.js index.audio.position.worklet.js index.png index.icon.png index.apple-touch-icon.png
  export-manifest.json        # {"godot": "...", "threads": false, "template": "..."}
  verification/frame-1.png, frame-2.png, verify-report.json   # {"ok": true, ...}
wasm/index.html               # ignored
```

Page slug: from the folder name, strip the leading `YYYY-MM-DD-HHMMSS-` and then the next `-`-separated token
(the model tag): `2026-09-26-001158-gpt6sol-voxel-horse` → `voxel-horse`. `--page <slug>` overrides this.
Title = the slug with dashes turned into spaces and the first letter capitalized.

## Godot engine dedupe (proven in `../spike/build.py`)

1. The engine files are `index.wasm`, `index.js`, `index.audio.worklet.js`, `index.audio.position.worklet.js`.
   sha12 = the first 12 hex characters of sha256 over the four files' bytes, concatenated in that order.
2. If `docs/engines/<sha12>/` doesn't exist, copy them there as `godot.wasm`, `godot.js`, `godot.audio.worklet.js`, `godot.audio.position.worklet.js`.
3. Copy the other export files (except `export-manifest.json`, `verification/`, and the engine files) into `runs/<id>/game/`.
4. Rewrite `game/index.html`. `rel` = the relative path from the game dir to `docs/engines/<sha12>/godot`:
   - `<script src="index.js"></script>` → `<script src="{rel}.js"></script>`
   - in `const GODOT_CONFIG = {...};`: `executable` = rel, **`mainPack` = "index.pck"** (required), and rename the
     `fileSizes` key `index.wasm` → `{rel}.wasm`.
5. Refuse an export with `threads: true` (from export-manifest.json, or `const GODOT_THREADS_ENABLED = true` in the html)
   with a clear error, unless `--allow-threads` is given. With the flag, store `"threads": true`.
6. `verification/frame-1.png` → `runs/<id>/thumb.png`.

## Cleaning (always runs on session files before they are written to docs/)

1. Remove every `thinkingSignature` key and every `encrypted_content` key, at any depth (a `thinkingSignature`
   value may be a JSON string that contains `encrypted_content`; dropping the whole key is enough).
2. Rewrite path prefixes in all strings: the user's home dir → `~`, plus extra rewrites from `bench.toml`:
   ```toml
   [clean]
   rewrite = { "/Volumes/M2SSD" = "<vol>" }
   ```
3. Drop these keys at any depth: `pid`, `completionOwnerId`, `sessionId`, `sessionFile`, `sessionRoot`, `launchContractDigest`.
4. Secret scan over the cleaned text of every published file (session files, output.md, and source files).
   Patterns: `sk-[A-Za-z0-9_-]{20,}`, `ghp_[A-Za-z0-9]{30,}`, `github_pat_[A-Za-z0-9_]{30,}`, `gho_[A-Za-z0-9]{30,}`,
   `AKIA[0-9A-Z]{16}`, `xox[baprs]-[A-Za-z0-9-]{10,}`, `-----BEGIN [A-Z ]*PRIVATE KEY-----`,
   `(?i)(api[_-]?key|secret|token|password)["'\s:=]+[A-Za-z0-9_\-/+]{24,}`.
   Any hit aborts the import **before anything is written**. The error prints file:line and the match masked
   (first 4 characters + `…`). With `--redact`, each match is replaced with `[REDACTED]` and the import continues.
5. JSONL files are cleaned line by line. `output.md` and source files get steps 2 and 4 only.

## CLI (`bench`, run from the repo root, or pass `--root`)

```
bench import <effort-run-dir> [--page SLUG] [--redact] [--allow-threads] [--dry-run]
bench list                      # pages and their runs
bench rm <slug> [<run_id>]      # remove a run (or a whole page), then rebuild
bench rebuild                   # regenerate results.json + pages.json from runs/*/run.json; delete engines no run references
bench serve [--port 8000]       # serve docs/ like GitHub Pages: Access-Control-Allow-Origin: *, .wasm as application/wasm, NO COOP/COEP headers
bench publish [-m MSG]          # git add docs && git commit && git push
bench run ...                   # run agents locally, then import (see "Running benchmarks")
bench models [SEARCH]           # models the harness can run; with SEARCH also their effort levels
```
- `import` is idempotent. Re-importing the same folder replaces runs with the same id.
- `import` prints a short summary per run: id, engine stored or reused, bytes written, paths rewritten, secret hits.
- `--dry-run` does all the work, including the secret scan, in a temp dir and writes nothing to docs/.
- Errors go to stderr with a non-zero exit code, and there are no tracebacks for expected errors.

## Running benchmarks (`bench run`)

Runs one prompt through one or more models × effort levels on this machine with a **harness** (the agent program;
only `pi` for now), exports + verifies each Godot project, then imports everything into one page.

```
bench run PROMPT | --prompt-file FILE
    --kind godot|media  what the agents produce (default godot); must match an existing page's kind
    -m MODEL[:LEVELS]   repeatable. LEVELS: "low,high" | "low..max" (range in LEVEL_ORDER, keeping only supported levels)
                        | "all" (every supported level except off) | explicit "off". No suffix = "all".
    -e LEVELS           default LEVELS for every -m without a suffix
    --page SLUG         add to this page (default: slug of the prompt's first 6 words, max 40 chars)
    --title TEXT        page title (default: from slug, as for import)
    --brief FILE        use this brief template instead of the built-in one ({prompt} is substituted)
    -j N                max agents at once (default [run].parallel or 8)
    --timeout DUR       per agent, "30m" / "90s" / "1h" (default [run].timeout or 30m)
    --yes               don't ask for confirmation     --dry-run   print the plan and exit
    --publish           run `bench publish` after importing
bench run --resume DIR  finish an interrupted batch (see Resume)
```
`LEVEL_ORDER = off, minimal, low, medium, high, xhigh, max`. Every requested level is checked against the harness's
list for that model **before anything starts**; an unknown model or unsupported level is an error that names the
supported levels (pi silently clamps unsupported levels, so this check is what keeps labels honest).

`bench.toml`:
```toml
[run]
dir = "~/dev/bench-runs"   # where batch folders go (never inside ~/dev/effort-runs)
parallel = 8
timeout = "30m"
tools = ["python3 (standard library only)", "node (no npm packages)", "ffmpeg", "ffprobe"]   # listed in the brief
```

### Flow
1. **Plan**: resolve models + levels, print the harness (name + version), page (new/existing), prompt, the numbered
   model × effort list and the batch dir. Ask `Start? [y/N]` (stdin not a tty and no `--yes` → error). `--dry-run` stops after printing.
2. **Batch dir**: `<run.dir>/<YYYY-MM-DD-HHMMSS>-<page slug>/` containing `batch.json`, `prompt.md`, and one
   **model dir** per model named `<YYYY-MM-DD-HHMMSS>-<modeltag>-<page slug>` (modeltag = model id after the last "/",
   lowercased, non-alphanumerics removed: `gpt6sol`). Each model dir has exactly the effort-run-folder layout that
   `bench import` reads (its own copy of `prompt.md`, `data.json`, `<level>/`, `wasm/<level>/`), so import needs no special case.
3. **Brief**: `src/bench/briefs/<kind>.md` with `{prompt}` replaced by the prompt verbatim and `{tools}` by the
   installed tools from `[run].tools` (each `"name note"`, e.g. `"python3 (standard library only)"`, listed as
   `name version note`; tools not on PATH are left out with a note). The same text for every run.
   Saved as `.harness/<level>/brief.md`, never in the agent's working dir.
4. **Agents** (threads + subprocess, at most `-j` at once). Working dir = `<model dir>/<level>/` (empty at start).
   Harness scratch = `<model dir>/.harness/<level>/` (session dir, `events.jsonl`, `stderr.txt`), kept outside the
   level dir so the agent's project stays clean. Timeout → kill the process group, state `timeout`.
5. **Collect** (per run, when its agent exits): copy the session file to `<level>/session.jsonl`, write
   `<level>/conversation.json` (the session as a JSON array), `<level>/events.jsonl` (without the `message_update`
   streaming snapshots, which only repeat the partial message; the raw file stays in `.harness/`), `<level>/status.json`
   (`{state, error, exit_code, argv, harness, startedAt, endedAt, durationMs}`), `<level>/data.json` (the run entry
   below). The model dir's `data.json` = `{"schema": "bench-run/1", "harness": {...}, "runs": {"<level>": entry}}`,
   rewritten after every run finishes. Entry: `model, thinkingLevel, startedAt, endedAt, durationMs, costUsd,
   toolCalls, turns, tokens: {input, output, total, reasoning, cacheRead, cacheWrite}, state, error`.
6. **Media** (kind `media`, only when state is `complete`, when `media/<level>/manifest.json` is missing):
   check every file in `<level>/output/` (sorted, flattened as `a-b.png` for `a/b.png`, at most 8) into
   `media/<level>/`. Images (`.png .jpg .jpeg .webp .gif`) must be readable by ffprobe; one over 2 MB is
   re-encoded as JPEG (a GIF isn't). SVGs must parse as XML with an `<svg>` root (size from width/height or
   viewBox) and be ≤ 2 MB. Videos (`.mp4 .webm .mov`) must have a duration; one that isn't H.264/yuv420p mp4,
   is over 10 s or over 2 MB is re-encoded (`libx264`, `-t 10`, max 1280 wide, CRF 26 → 32 → 38 until it fits).
   Each video gets a `.poster.jpg` at 30% of its length. Unsupported types, unreadable files and name clashes
   are errors. `manifest.json` = `{ok, items, errors}` with `ok` = at least one item and no errors. Errors
   keep the state and set `error` (joined with `; `, the first 200 characters). ffmpeg and ffprobe must be
   on PATH before a media batch starts.

   **Export** (kind `godot`, only when state is `complete`; one export at a time, other agents keep running): write
   `export_presets.cfg` (preset "Web", nothreads, `exclude_filter` listing the session files), run
   `godot --headless --path <level> --export-release Web <abs wasm/<level>>/index.html`, then check `index.html`,
   `index.js`, `index.wasm`, `index.pck` exist and are non-empty (Godot can exit 0 after failing). Write
   `export-manifest.json` (`godot`, `threads: false`, `template`, `exportedAt`). Failure → keep state, set
   `error = "Godot export failed: <last log line>"`, no wasm dir.
7. **Verify** (optional dependency: Playwright, `pip install bench[verify]`; skipped with a note when missing):
   serve the export dir, open it in Chrome with the swiftshader flags, wait for Godot to remove `#status` (≤ 30s), take
   `verification/frame-1.png`, wait 1.2s, take `frame-2.png`; `verify-report.json` =
   `{ok, booted, framesDiffer, consoleErrors, pageErrors}` with `ok = booted and framesDiffer and no pageErrors`.
8. **Import**: `bench import` each model dir with `--page` (and `--title` for a new page), then print where to preview
   (`bench serve`) and publish, or run `bench publish` with `--publish`.

Progress: on a tty a table (model, effort, state, elapsed, turns, tokens, cost) redrawn every 2s, read from each
session file as it grows; otherwise one line per state change. States: queued, running, exporting, verifying,
processing (media), done, failed, timeout.

### Metrics (from the session log, the same numbers pi-subagents reported)
Over assistant messages: `turns` = count; `toolCalls` = number of `toolCall` content blocks; `tokens.input/output/
reasoning/cacheRead/cacheWrite` = sums of `usage.<field>`; `tokens.total = input + output`; `costUsd` = sum of
`usage.cost.total`. `durationMs` = wall clock of the harness process. `thinkingLevel` = the session's
`thinking_level_change` entry (what actually ran). `state = failed` when the process exits non-zero, there is no
session file, or the last assistant message has `stopReason: "error"`; `error` = its `errorMessage` or the last
non-empty stderr line (the first 200 characters).

### Harness interface (`src/bench/harness.py`)
```python
class Harness:           # one per agent program; Pi is the only one for now
    name: str
    def version(self) -> str | None
    def models(self) -> list[str]                       # "provider/id"
    def levels(self, model) -> list[str]                # supported effort levels, in LEVEL_ORDER
    def command(self, model, level, brief, session_dir) -> list[str]
    def session_file(self, session_dir) -> Path | None
```
Pi: `pi --version`; `pi --list-models` (parse the table); levels via `pi --mode rpc --no-session --model M -ne -ns -np -nc`
sending `{"type":"get_available_thinking_levels"}` and reading the matching response;
command = `pi -p --mode json --model M:LEVEL --session-dir DIR -ne -ns -np -nc BRIEF` (no user extensions, skills,
prompt templates or AGENTS.md, so runs are reproducible); session file = the one `*.jsonl` in DIR.
Future harnesses and a VM runner plug in here and at "start one agent" in `runner.py`.

### Ctrl-C
Kills every running agent's process group, marks those runs `queued` in batch.json, prints the `--resume` command, exits 130.

### Resume
`batch.json` = `{prompt, kind, page, title, harness, brief, created, runs: [{model, level, model_dir, state}]}`, updated on
every state change. `--resume DIR` reads it and, per run: `queued`/`running` → start the agent again (clear its level
dir first); a finished agent is never rerun. Then export where `wasm/<level>` is missing, verify where
`verify-report.json` is missing (media: process where `media/<level>/manifest.json` is missing), and import. Failed and timed-out runs stay as they are.

## Viewer (docs/)

- **index.html**: cards per page (thumb, title, n_runs, models, updated) → page.html.
- **page.html**: title, the Prompt (prompt.md) and a collapsed Final prompt, then a "Compare all" link → compare.html and
  a runs table (thumb, model, effort, harness, verified ✓/✗, duration, tokens total/output/reasoning, cost, tool calls, turns).
  Harness shows "pi 0.87.1" (name only when version is null, "–" when missing).
  A `media` page also has a **Gallery** above the table: one card per run (its thumb, model · effort, cost,
  duration, "N files" when more than one), linking to the run. Expanding a media row shows its outputs. A run whose `state` isn't `complete`
  shows a red `failed`/`timeout` badge in the Verified cell, and its expanded row shows `error`.
  The table is sortable, numeric columns show an inline CSS bar scaled to the column max, and every header has a help
  tooltip (shown after 0.5s). Clicking a row expands it and boots that run's game inline; clicking again removes it.
- **run.html**: a header with model, effort, harness, and key metrics (plus the failed/timeout badge and `error`), then tabs:
  - *Game*: click-to-play overlay (shows thumb). On click it inserts
    `<iframe sandbox="allow-scripts allow-pointer-lock" allow="fullscreen; autoplay; gamepad">` pointing at `game.entry`.
    There's also an "Open full screen ↗" link (plain link to the entry; it runs unsandboxed, so label it).
  - *Transcript*: renders `session.conversation`. System prompt collapsed. User text. For each assistant message:
    thinking (collapsed, toggle "show thinking"), text (markdown), and toolCall blocks paired with their toolResult by
    `toolCallId`. Tool display: `bash` → command + output, `write` → path + content, `edit` → path + old/new blocks,
    `read`/`ls` → args + output. Output is collapsed past 20 lines, and `isError` gets a ✗ badge. Show `+m:ss` since
    session start and per-message token usage. Durations come from `events.jsonl` `tool_execution_start`/`_end`
    (matched by `toolCallId`) when present. Filter buttons: all / tool calls / errors.
  - *Output* (instead of Game, for a `media` run): every item as a captioned figure (file name, size, duration,
    bytes, a `download` link). Images, **SVGs included**, are only ever shown with `<img>` (which never runs an
    SVG's scripts), never inlined or put in an object/embed/iframe, and never linked for viewing on this origin.
    Videos use `<video controls preload="none">` with the poster, and never autoplay.
  - *Source*: a file list, and clicking a file shows it in a `<pre>`.
  - *Metrics*: all metrics as a table (including Harness, State and Error), plus links to download the raw session files.
- **compare.html**: one card per run (all runs of the page by default), laid out as a grid of ~380px columns that wraps
  into rows (3 across at desktop width, 1 on phones, never sideways scrolling). Each card has the run title, one line with
  harness, duration, tokens and cost (plus the failed/timeout badge), and its game with click-to-play (each column boots independently, never automatically),
  or for a `media` run its outputs stacked (the Play all button is hidden when there are no games).
- Everything renders from the JSON. There are no per-page HTML files. It must work under a sub-path (`/llm-bench/`),
  so use only relative URLs. It supports dark mode via `prefers-color-scheme`, has readable defaults, and has no frameworks.

## Tests (`uv run pytest`)

- CLI: unit tests plus an end-to-end import of a small synthetic effort-run fixture. The fixture uses tiny fake engine
  files and a real Godot `index.html` template, and covers dedupe, the html rewrite, cleaning, the secret abort and
  redaction, idempotency, rm, and rebuild.
- Viewer: Playwright (Python, `channel="chrome"`, which uses the installed Google Chrome, so no browser download)
  against `bench serve` on a fixture site. It covers each page rendering without console errors, click-to-play inserting
  a sandboxed iframe, the transcript's tool calls and error badges, and compare with 3 runs. A `media` fixture page
  (`art`: an SVG with an embedded script, a PNG and a 1 s mp4) covers the gallery, the Output tab (the SVG's script
  never runs, videos don't autoplay), expanded rows and compare.
- `bench run`: a fake `pi` (a Python script put first on PATH by the test) that answers `--version`, `--list-models`,
  the RPC levels request, and `-p` runs by writing a canned session file and a tiny project; env vars make it fail,
  hang, or exit non-zero. Covers level parsing (`all`, ranges, explicit lists, off excluded by default, unsupported
  level → error before anything starts), the plan/confirmation, `-j`, timeout, failed runs being imported, metrics
  against the real voxel-horse `high/session.jsonl` numbers (when present), and `--resume` not rerunning finished
  agents. For a media brief the fake pi writes `./output/` (SVG, PNG and an ffmpeg-made mp4) plus a script and a
  leftover binary frame. `tests/test_media.py` checks the media step on ffmpeg-generated inputs (trim + re-encode,
  oversized image → JPEG, bad files, empty output, too many files, name clashes); media tests are skipped without
  ffmpeg. A slow test (skipped without `godot`) exports a tiny real project. No test calls a real model.
- Integration (skipped when `~/dev/effort-runs/2026-09-26-001158-gpt6sol-voxel-horse` is missing): import the real run
  into a temp site, serve it, and check that all 3 Godot games boot inside the sandboxed iframe in compare. Headless Chrome
  needs `--enable-unsafe-swiftshader --use-angle=swiftshader` for WebGL. Godot removes `#status` from its document
  once the game has started, which is the boot signal.
