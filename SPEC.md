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
      thumb.png                   # optional
      game/index.html, index.pck, index.png, index.icon.png, index.apple-touch-icon.png
      session/conversation.json   # cleaned (see Cleaning)
      session/events.jsonl        # cleaned
      session/status.json         # cleaned
      session/output.md
      source/...                  # project files the model wrote
```

All paths inside JSON are **relative to the run directory** (for Run) or to `docs/` (for PageSummary.thumb).

### PageSummary (element of `data/pages.json`)
```json
{ "slug": "voxel-horse", "title": "Voxel horse", "n_runs": 3,
  "models": ["openai-codex/gpt-6-sol"], "updated": "2026-09-26T07:15:57Z",
  "thumb": "data/voxel-horse/runs/gpt-6-sol-high-20260926-001158/thumb.png" }
```
`thumb` is taken from the most recent run that has one, or `null`.

### Page (`data/<slug>/page.json`)
```json
{ "slug": "voxel-horse", "title": "Voxel horse",
  "prompt": "<contents of prompt.md, the originating prompt; refreshed on every import>",
  "final_prompt": "<brief the main agent sent each run: first user message of the cleaned session, ./<level>/ -> ./<effort>/; null if none>",
  "created": "2026-09-26T07:12:42Z", "updated": "2026-09-26T07:15:57Z" }
```

### Run (`run.json`, and each element of `results.json`)
```json
{
  "id": "gpt-6-sol-high-20260926-001158",
  "page": "voxel-horse",
  "model": "openai-codex/gpt-6-sol",
  "effort": "high",
  "started_at": "2026-09-26T07:12:42Z",
  "source_dir": "2026-09-26-001158-gpt6sol-voxel-horse",
  "verified": true,
  "metrics": {
    "duration_ms": 196192, "cost_usd": 0.146, "tool_calls": 16, "turns": 17,
    "tokens_total": 32732, "tokens_input": 25280, "tokens_output": 7452,
    "tokens_reasoning": 3073, "tokens_cache_read": 105984
  },
  "thumb": "thumb.png",
  "game": { "kind": "godot", "entry": "game/index.html", "engine": "41560f8755ed",
            "godot": "4.7.2.stable.official.ed1daf0bf", "threads": false },
  "session": { "conversation": "session/conversation.json", "events": "session/events.jsonl",
               "status": "session/status.json", "output": "session/output.md" },
  "source": { "root": "source/", "files": ["README.md", "project.godot", "scenes/main.tscn", "scripts/main.gd"] }
}
```
- `game`, `session`, `source`, and `thumb` can each be `null` when the input doesn't have them.
- `id` = `<model name after the last "/", lowercased>-<effort>-<YYYYMMDD-HHMMSS from the folder name>`.
- `verified` = `wasm/<level>/verification/verify-report.json` → `.ok`, or `null` if that file is missing.

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
```
- `import` is idempotent. Re-importing the same folder replaces runs with the same id.
- `import` prints a short summary per run: id, engine stored or reused, bytes written, paths rewritten, secret hits.
- `--dry-run` does all the work, including the secret scan, in a temp dir and writes nothing to docs/.
- Errors go to stderr with a non-zero exit code, and there are no tracebacks for expected errors.

## Viewer (docs/)

- **index.html**: cards per page (thumb, title, n_runs, models, updated) → page.html.
- **page.html**: title, the Prompt (prompt.md) and a collapsed Final prompt, then a "Compare all" link → compare.html and
  a runs table (thumb, model, effort, verified ✓/✗, duration, tokens total/output/reasoning, cost, tool calls, turns).
  The table is sortable, numeric columns show an inline CSS bar scaled to the column max, and every header has a help
  tooltip (shown after 0.5s). Clicking a row expands it and boots that run's game inline; clicking again removes it.
- **run.html**: a header with model, effort, and key metrics, then tabs:
  - *Game*: click-to-play overlay (shows thumb). On click it inserts
    `<iframe sandbox="allow-scripts allow-pointer-lock" allow="fullscreen; autoplay; gamepad">` pointing at `game.entry`.
    There's also an "Open full screen ↗" link (plain link to the entry; it runs unsandboxed, so label it).
  - *Transcript*: renders `session.conversation`. System prompt collapsed. User text. For each assistant message:
    thinking (collapsed, toggle "show thinking"), text (markdown), and toolCall blocks paired with their toolResult by
    `toolCallId`. Tool display: `bash` → command + output, `write` → path + content, `edit` → path + old/new blocks,
    `read`/`ls` → args + output. Output is collapsed past 20 lines, and `isError` gets a ✗ badge. Show `+m:ss` since
    session start and per-message token usage. Durations come from `events.jsonl` `tool_execution_start`/`_end`
    (matched by `toolCallId`) when present. Filter buttons: all / tool calls / errors.
  - *Source*: a file list, and clicking a file shows it in a `<pre>`.
  - *Metrics*: all metrics as a table, plus links to download the raw session files.
- **compare.html**: one column per run (all runs of the page by default). Each column has the run title, one line with
  duration, tokens and cost, and its game with click-to-play (each column boots independently, never automatically).
- Everything renders from the JSON. There are no per-page HTML files. It must work under a sub-path (`/llm-bench/`),
  so use only relative URLs. It supports dark mode via `prefers-color-scheme`, has readable defaults, and has no frameworks.

## Tests (`uv run pytest`)

- CLI: unit tests plus an end-to-end import of a small synthetic effort-run fixture. The fixture uses tiny fake engine
  files and a real Godot `index.html` template, and covers dedupe, the html rewrite, cleaning, the secret abort and
  redaction, idempotency, rm, and rebuild.
- Viewer: Playwright (Python, `channel="chrome"`, which uses the installed Google Chrome, so no browser download)
  against `bench serve` on a fixture site. It covers each page rendering without console errors, click-to-play inserting
  a sandboxed iframe, the transcript's tool calls and error badges, and compare with 3 runs.
- Integration (skipped when `~/dev/effort-runs/2026-09-26-001158-gpt6sol-voxel-horse` is missing): import the real run
  into a temp site, serve it, and check that all 3 Godot games boot inside the sandboxed iframe in compare. Headless Chrome
  needs `--enable-unsafe-swiftshader --use-angle=swiftshader` for WebGL. Godot removes `#status` from its document
  once the game has started, which is the boot signal.
