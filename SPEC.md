# llm-bench spec

This repo is both the CLI (`src/bench/`) and the GitHub Pages site (`docs/`, served from `main:/docs`).
The site is static and has no build step. The CLI writes JSON and files into `docs/data/` and `docs/engines/`,
and the viewer pages fetch that JSON in the browser.

Guiding rule: **simple and lean.** The CLI is standard-library Python only (argparse, json, hashlib,
tomllib, http.server, subprocess). The site is vanilla JS ES modules, with one pinned, vendored dependency
(`marked` for Markdown tokenization). No frameworks and no bundler.

## Vocabulary

- **Page**: one prompt or task, such as `voxel-horse`.
- **Run**: one model × effort level attempt at a page's task, kept in one directory (`<batch>/<run id>/`, see
  "Run directory"). `bench import` publishes it to the site.
- **Kind**: what a page's runs produce. `godot` = a Godot project, published as a playable web build;
  `media` = image and/or video files; `web` = a web page (HTML + ES modules + npm packages), published as one
  self-contained `index.html` packaged with esbuild. Every run of a page has the page's kind.

## Site layout (the data contract between the CLI and the viewer)

```
docs/
  .nojekyll
  index.html                      # home: list of pages            (reads data/pages.json)
  page.html?p=<slug>              # one page: runs table + gallery (reads data/<slug>/page.json)
  run.html?p=<slug>&r=<run_id>    # one run: tabs Game | Transcript | Source | Metrics
  compare.html?p=<slug>[&r=<id>,<id>]   # side by side: all runs of the page, or just the listed ones
  play.html?p=<slug>&r=<run_id>   # one run's output alone, full window (the compare cards' pop-out target)
  assets/                         # shared JS/CSS
  engines/<sha12>/godot.wasm      # deduplicated Godot engine files, one dir per unique engine
  engines/<sha12>/godot.js
  engines/<sha12>/godot.audio.worklet.js
  engines/<sha12>/godot.audio.position.worklet.js
  data/
    pages.json                    # [PageSummary]
    <slug>/page.json              # Page
    <slug>/ranking.json           # optional: {"ranks": {"<run id>": 1, ...}, "updated": "<iso>"}, the owner's ranking (see Ranking)
    <slug>/runs/<run_id>/
      run.json                    # Run
      thumb.png                   # optional (godot)
      game/index.html, index.pck, index.png, index.icon.png, index.apple-touch-icon.png   # godot
      media/<file>, media/<name>.poster.jpg                                              # media
      game/index.html             # web: the packaged page, one file (cleaned and secret-scanned like source)
      session/conversation.json   # cleaned (see Cleaning)
      session/stderr.txt          # optional, cleaned
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
  "final_prompt": "<the full brief each run received: first user message of the cleaned transcript; null if none>",
  "created": "2026-09-26T07:12:42Z", "updated": "2026-09-26T07:15:57Z",
  "runs": ["<Run with rank; see below>"] }
```

### Run (`run.json`, and each element of `page.json.runs`)
```json
{
  "id": "gpt-6-sol-high-20260926-001158",
  "page": "voxel-horse",
  "model": "openai-codex/gpt-6-sol",
  "effort": "high",
  "kind": "godot",
  "started_at": "2026-09-26T07:12:42Z",
  "batch": "2026-09-26-001158-voxel-horse",
  "harness": { "name": "pi", "version": "0.87.1" },
  "state": "complete",
  "error": null,
  "route": null,
  "metrics": {
    "duration_ms": 196192, "cost_usd": 0.146, "tool_calls": 16, "turns": 17,
    "tokens_total": 32732, "tokens_input": 25280, "tokens_output": 7452,
    "tokens_reasoning": 3073, "tokens_cache_read": 105984
  },
  "thumb": "thumb.png",
  "output": { "kind": "godot", "entry": "game/index.html", "engine": "41560f8755ed",
             "godot": "4.7.2.stable.official.ed1daf0bf", "threads": false,
             "ok": true, "verified": true, "error": null },
  "session": { "conversation": "session/conversation.json", "stderr": "session/stderr.txt" },
  "source": { "root": "source/", "files": ["README.md", "project.godot", "scenes/main.tscn", "scripts/main.gd"] }
}
```
- `output`, `session`, `source` and `thumb` can each be `null`.
- `rank` exists only in `page.json.runs` (never in `run.json`): the run's rank from `ranking.json`, or `null`.
- `kind` is the page's kind (runs imported before kinds existed have none; the viewer treats that as `godot`). Importing
  into a page of another kind is an error. `batch` = the batch directory's name (runs published before run
  directories hold the old model directory's name).
- **`state`, `output.ok`, `output.verified`: three questions, three places.** `state` is only what the agent did:
  `queued | running | complete | failed | timeout`; `error` is the agent's error (harness exit, timeout, an assistant
  `stopReason: error`, or a note that a pinned OpenRouter run was served outside its upstreams). `output.ok` /
  `output.error` are what the kind step made of the work (Godot export, packaging, media normalization): a run
  whose export failed is `state: complete` with `output: {kind, ok: false, error: "Godot export failed: …",
  verified: null}`. `output.verified` is whether the check passed (booted, loaded offline, files readable), `null`
  when it wasn't run. `output` is `null` only when the agent didn't complete (there was nothing to export).
- `output` carries its own `kind` and the kind's fields (see Kinds): `godot` = `entry`, `engine`, `godot`, `threads`;
  `web` = `entry`, `bytes`, `esbuild`; `media` = `items`, each `{type: "image"|"video", path: "media/<file>", width,
  height, bytes}` plus, for a video, `duration_s, poster: "media/<name>.poster.jpg", transcoded` and `trimmed: true`
  when it was cut to 10 s (width/height can be `null` for an SVG without a size). Paths are relative to the run
  directory. `thumb` = `thumb.png` (the verify step's first screenshot) for godot and web, the first image's path or
  the first video's poster for media. Model-written text (SVGs, the packaged page) is cleaned and secret-scanned like
  source. The run's `source` never includes `node_modules/`; for media it holds only text files of at most 512 KB,
  and `output/` only for the files there that aren't media (a generator script kept in `./output/`).
- `id` = `<model name after the last "/", lowercased>-<effort>-<YYYYMMDD-HHMMSS of the batch>`, with `-cc` after the
  model for Claude Code runs; URL/filesystem-safe: a pinned OpenRouter route (`@…`, which can contain `/` itself) is split
  off first and appended as `-via-<route>`, e.g. `…flash@deepinfra/fp8` → `deepseek-v4.1-flash-via-deepinfra-fp8-low-20261001-101500`;
  anything else outside `[a-z0-9.-]` becomes `-`. It is also the run directory's name; two runs of a batch with one id
  are refused before anything starts.
- `harness` = the agent program and its version; `metrics` as in "Metrics".
- `route` = what the harness reports about routing, for a pi `openrouter/` run, else `null`:
  `{"requested": {"only": [...], "allow_fallbacks": false}, "served": [...], "cost_usd": 0.00085, "pi_cost_usd": 0.00038}`.
  `requested` is `null` for an unpinned run (OpenRouter chose the upstream); the rest is recorded either way.
  `served` = the upstreams that served the run, in order, as OpenRouter names them ("DeepInfra", "AtlasCloud").
  They're matched to the requested slugs by `upstream_key()` (lowercase alphanumerics of the name, and of the slug
  before its `/variant`: `atlas-cloud/fp8` and "AtlasCloud" → `atlascloud`); one outside `requested.only` is appended
  to `error`. `cost_usd` = what OpenRouter charged (the sum of each response's `usage.cost`), `null` when no response
  reported one; `pi_cost_usd` = pi's own estimate. For an OpenRouter run `metrics.cost_usd` is `cost_usd` when present:
  pi prices every OpenRouter call at one catalog rate whatever upstream served it (≈ 2–7× too low on real runs).

## Run directory (what `bench run` writes and `bench import` publishes)

```
<run.dir>/<YYYY-MM-DD-HHMMSS>-<page slug>/      # a batch
  batch.json  prompt.md                         # the batch's record (see Resume) and the originating prompt
  <run id>/                                     # one run
    run.json                                    # the run's record: the Run above, minus rank, thumb, session and source;
                                                #   output = {kind, ok, error, verified} (null until the kind step ran)
    work/                                       # the agent's working dir, empty at start; nothing else is ever written here
    harness/                                    # session file(s), stdout (events.jsonl), stderr.txt, brief.md, route.jsonl,
                                                #   conversation.json (the session in pi's format): never published except the
                                                #   transcript and a non-empty stderr
    output/                                     # what the kind made: Godot export (+ verification/), the packaged page
                                                #   (+ verification/), or normalized media + manifest.json
```
`bench import` takes one run directory or a batch directory and publishes each run: cleans and secret-scans, copies
`run.json` (adding `thumb`, `output`'s kind fields, `session` and `source`), `harness/conversation.json` as
`session/conversation.json`, `work/` as `source/` and the kind's `output/`, then rebuilds. The page slug is the run's
`page` (`--page` overrides it); the title = the slug with dashes turned into spaces and the first letter capitalized.
The page's prompt is the batch directory's `prompt.md`. Effort-run folders (`fe-model-effort-fanout/1`) are no longer read.

## Godot engine dedupe (proven in `../spike/build.py`)

1. The engine files are `index.wasm`, `index.js`, `index.audio.worklet.js`, `index.audio.position.worklet.js`.
   sha12 = the first 12 hex characters of sha256 over the four files' bytes, concatenated in that order.
2. If `docs/engines/<sha12>/` doesn't exist, copy them there as `godot.wasm`, `godot.js`, `godot.audio.worklet.js`, `godot.audio.position.worklet.js`.
3. Copy the other export files (except `export-manifest.json`, `verification/`, and the engine files) from `output/` into `runs/<id>/game/`.
4. Rewrite `game/index.html`. `rel` = the relative path from the game dir to `docs/engines/<sha12>/godot`:
   - `<script src="index.js"></script>` → `<script src="{rel}.js"></script>`
   - in `const GODOT_CONFIG = {...};`: `executable` = rel, **`mainPack` = "index.pck"** (required), and rename the
     `fileSizes` key `index.wasm` → `{rel}.wasm`.
5. Refuse an export with `threads: true` (from export-manifest.json, or `const GODOT_THREADS_ENABLED = true` in the html)
   with a clear error, unless `--allow-threads` is given. With the flag, store `"threads": true`.
6. `verification/frame-1.png` → `runs/<id>/thumb.png`.

## Cleaning (always runs on text files before they are written to docs/)

1. Remove every `thinkingSignature` key and every `encrypted_content` key, at any depth (a `thinkingSignature`
   value may be a JSON string that contains `encrypted_content`; dropping the whole key is enough).
2. Rewrite path prefixes in all strings: the user's home dir → `~`, plus extra rewrites from `bench.toml`:
   ```toml
   [clean]
   rewrite = { "/Volumes/M2SSD" = "<vol>" }
   ```
3. Drop these keys at any depth: `pid`, `completionOwnerId`, `sessionId`, `sessionFile`, `sessionRoot`, `launchContractDigest`.
4. Secret scan over the cleaned text of every published file (the transcript, stderr, source files, SVGs and the packaged page).
   Patterns: `sk-[A-Za-z0-9_-]{20,}`, `ghp_[A-Za-z0-9]{30,}`, `github_pat_[A-Za-z0-9_]{30,}`, `gho_[A-Za-z0-9]{30,}`,
   `AKIA[0-9A-Z]{16}`, `xox[baprs]-[A-Za-z0-9-]{10,}`, `-----BEGIN [A-Z ]*PRIVATE KEY-----`,
   `(?i)(api[_-]?key|secret|token|password)["'\s:=]+[A-Za-z0-9_\-/+]{24,}`.
   Any hit aborts the import **before anything is written**. The error prints file:line and the match masked
   (first 4 characters + `…`). With `--redact`, each match is replaced with `[REDACTED]` and the import continues.
5. Image data (the base64 `data` of `{type: "image"}` blocks in session JSON) is set aside before steps 2 and 4 and
   put back after: it's binary, so rewrites could corrupt it and the scan finds random matches (`AKIA…`) in it.
   Data that isn't plain base64 stays in place and is scanned.
6. JSONL files are cleaned line by line. Source files, stderr, SVGs and the packaged page get steps 2 and 4 only.

## CLI (`bench`, run from the repo root, or pass `-C/--root`)

```
bench import <run-dir | batch-dir> [-p/--page SLUG] [-t/--title TEXT] [-r/--redact] [-a/--allow-threads] [-n/--dry-run]
bench list                      # pages and their runs
bench rm <slug> [<run_id>]      # remove a run (or a whole page), then rebuild
bench rebuild                   # regenerate page.json + pages.json from runs/*/run.json; delete engines no run references
bench serve [-p/--port 8000]    # serve docs/ like GitHub Pages: Access-Control-Allow-Origin: *, .wasm as application/wasm, NO COOP/COEP headers
                                #   plus the local-only ranking API (see Ranking)
bench publish [-m MSG]          # git add docs && git commit && git push
bench run ...                   # run agents locally, then import (see "Running benchmarks")
bench models [SEARCH] [-H/--harness pi|claude-code]   # models the harness can run; with SEARCH also their effort levels
```
Every long option has a single-dash short form (shown as `-p/--page`); the short forms are listed with each command.
- `import` is idempotent. Re-importing the same directory replaces runs with the same id.
- `import` prints a short summary per run: id, engine stored or reused, bytes written, paths rewritten, secret hits.
- `--dry-run` does all the work, including the secret scan, in a temp dir and writes nothing to docs/.
- Errors go to stderr with a non-zero exit code, and there are no tracebacks for expected errors.

## Running benchmarks (`bench run`)

Runs one prompt through one or more models × effort levels on this machine with a **harness** (the agent program;
pi or Claude Code), turns each run's work into its kind's output and verifies it, then imports everything into one page.

```
bench run PROMPT | -f/--prompt-file FILE
    -k, --kind godot|media|web what the agents produce (default: the existing page's kind, else godot); must match it
    -m, --model MODEL[@UPSTREAMS][:LEVELS]  repeatable. UPSTREAMS: comma-separated OpenRouter provider slugs, as
                        OpenRouter lists a model's endpoints, variants included (`deepinfra/fp8`, `fireworks/us`)
                        (pi `openrouter/` models only, e.g. `openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8:low`);
                        pinned with fallbacks off, recorded as part of the model name. LEVELS: "low,high" | "low..max" (range in LEVEL_ORDER, keeping only supported levels)
                        | "all" (every supported level except off) | explicit "off". No suffix = "all".
    -s, --set SET       repeatable: a model set, either a NAME from bench.toml [sets] or a FILE with one
                        MODEL[@UPSTREAMS][:LEVELS] per line (# comments, blank lines ignored). Its entries are added before
                        the -m specs, exactly as if given with -m. An unknown name that isn't a file is an error
                        listing the defined sets.
    -e, --effort LEVELS default LEVELS for every model without a suffix (-m or set entry)
    -p, --page SLUG     add to this page (default: slug of the prompt's first 6 words, max 40 chars). For an existing
                        page, PROMPT can be left out: its prompt (page.json) and kind are reused.
    -c, --change-prompt allow a PROMPT that differs from the existing page's (after path cleaning); without it that's
                        an error, since every import replaces the page's prompt for all its runs
    -t, --title TEXT    page title (default: from slug, as for import)
    -b, --brief FILE    use this brief template instead of the built-in one ({prompt} is substituted)
    -j N                max agents at once (default [run].parallel or 8)
    -T, --timeout DUR   per agent, "30m" / "90s" / "1h" (default [run].timeout or 30m)
    -y, --yes           don't ask for confirmation
    -n, --dry-run       print the plan and exit
    -P, --publish       import and `bench publish` each run as it finishes
bench run -r/--resume DIR  finish an interrupted batch (see Resume)
```
`LEVEL_ORDER = off, minimal, low, medium, high, xhigh, max`. Every requested level is checked against the harness's
list for that model **before anything starts**; an unknown model or unsupported level is an error that names the
supported levels (pi silently clamps unsupported levels, so this check is what keeps labels honest).

`bench.toml`:
```toml
[run]
dir = "~/dev/bench-runs"   # where batch directories go (never inside ~/dev/effort-runs)
parallel = 8
timeout = "30m"
tools = ["python3 (standard library only)", "node (no npm packages)", "ffmpeg", "ffprobe"]   # listed in the brief

[sets]   # each a list of "MODEL[@UPSTREAMS][:LEVELS]" strings (anything else is an error)
cheap = ["openai-codex/gpt-6-luna:minimal,low", "openrouter/deepseek/deepseek-v4.1-flash:low..high"]
```

`bench.toml` is parsed in one place: `bench.config.Config.load(root)` in `cli.main` exposes `.rewrites` (`[clean]`),
`.run` (dir, parallel, timeout, tools) and `.sets`, and is passed to the importer and runner. One run's inputs
are a `bench.config.RunRequest` (prompt, kind, page, title, model specs/sets, effort, brief, parallel, timeout,
publish, change_prompt); it round-trips through JSON and is stored in `batch.json`, so a `--resume` (or, later, a
website-started run) replays the same fields. It is validated when built (kind, parallel >= 1, a parseable timeout),
so bad input fails before a batch dir exists; `from_dict` ignores unknown keys. A malformed `bench.toml` is a
plain error for every command.

### Flow
1. **Plan**: resolve models + levels, print the harness (name + version), page (new/existing), prompt, the numbered
   model × effort list and the batch dir. Ask `Start? [y/N]` (stdin not a tty and no `--yes` → error). `--dry-run` stops after printing.
2. **Batch dir**: `<run.dir>/<YYYY-MM-DD-HHMMSS>-<page slug>/` with `batch.json`, `prompt.md` and one run directory per
   model × effort (see "Run directory"). Run ids are assigned here from the batch's start time; each run's `state` in
   `batch.json` starts `queued`.
3. **Brief**: the kind's `src/bench/kinds/<kind>.md` with `{prompt}` replaced by the prompt verbatim and `{tools}` by the
   installed tools from `[run].tools` (each `"name note"`, e.g. `"python3 (standard library only)"`, listed as
   `name version note`; tools not on PATH are left out with a note). The same text for every run.
   Saved as `harness/brief.md`, never in the agent's working dir.
4. **Agents** (threads + subprocess, at most `-j` at once). Working dir = `<run>/work/` (empty at start); the harness's
   scratch is `<run>/harness/`, kept outside the working dir so the agent's project stays clean. Timeout → kill the
   process group, state `timeout`.
5. **Collect** (per run, when its agent exits): write `harness/conversation.json` (the session as a JSON array; each
   `toolResult` message carries `durationMs`, the tool's duration: from the assistant entry that called it to the
   result entry for pi, from the `tool_use` event to the `tool_result` event for Claude Code) and `run.json` (the
   run's record with `output: null`; see Run). `batch.json`'s state for the run becomes the record's `state`.
6. **Output** (per run, only when `state` is `complete`, and when `output` is missing or not `ok`): the kind's
   `finalize(work, output/)` makes the publishable output, `verify(output/)` checks it (when `finalize` succeeded), and
   `run.json`'s `output` becomes `{kind, ok, error, verified}`. A step that fails leaves `state` alone. See Kinds.
7. **Import**: `bench import` the batch directory with `--page` (and `--title` for a new page), then print where to
   preview (`bench serve`) and publish, or run `bench publish` with `--publish`. With `--publish` each run is
   imported and pushed on its own, right after its step 6 (`Publisher`, one run at a time: an import rewrites
   page.json, and a push must never see a half-written run directory), so the live site fills up while the batch
   still runs; the batch's own import at the end is then skipped. Only runs that couldn't be published (a secret
   hit, a failed push — reported as a `note:`) fall back to it: it retries them and exits non-zero.

Progress: on a tty a table (model, effort, state, elapsed, turns, tokens, cost) redrawn every 2s, read from each
session file as it grows; otherwise one line per state change. The states are the agent's (queued, running, complete,
failed, timeout) plus transient labels of the output step (exporting, packaging, processing, verifying, then done, or
"no output" when it failed); the labels are never written to `batch.json`.

### Kinds (`src/bench/kinds/`)

A kind is one class registered in `KINDS` (like `HARNESSES`); the runner and the importer never branch on a kind's name.
```python
class Kind:
    name: str; tools: tuple; tools_hint: str; activity: str; serial: bool   # tools must be on PATH before a batch starts;
                                                                            # serial: finalize runs one at a time
    def brief(self) -> str                              # the template text (kinds/<name>.md)
    def finalize(self, work_dir, out_dir) -> (bool, str | None)    # export / package / normalize -> (ok, error)
    def verify(self, out_dir) -> dict | None            # {ok, ...} or None when it can't be checked here
    def stage(self, out_dir, run_dir, ctx) -> Staged    # the output into the run's published dir; Staged(fields, thumb, engine)
    def keep_source(self, rel, path) -> bool            # whether a work file is published as source
```
- **godot** (`Godot`): `finalize` = **Export**: write `export_presets.cfg` into the project (preset "Web", nothreads), run
  `godot --headless --path <work> --export-release Web <abs output>/index.html`, then check `index.html`, `index.js`,
  `index.wasm`, `index.pck` exist and are non-empty (Godot can exit 0 after failing), and write `export-manifest.json`
  (`godot`, `threads: false`, `template`, `exportedAt`). Failure → `ok: false`, `error = "Godot export failed: <last log line>"`.
  `verify` = serve the export, open it in Chrome with the swiftshader flags, wait for Godot to remove `#status` (≤ 30s), take
  `verification/frame-1.png`, wait 1.2s, take `frame-2.png`; `verify-report.json` = `{ok, booted, framesDiffer,
  consoleErrors, pageErrors}` with `ok = booted and framesDiffer and no pageErrors`. `stage` = the engine dedupe below.
- **web** (`Web`; `esbuild` and `npm` on PATH): `finalize` = **Package**: read `work/index.html` and inline what it references
  (`bundle_html()`): each local `<script type="module">` (with `src` or inline) is bundled by `esbuild --bundle
  --format=esm --minify` with everything it imports, npm packages from `node_modules/` included, and imported assets
  (images, models, audio, fonts) become data: URLs; each local `<link rel="stylesheet">` is bundled into a `<style>`; a
  classic `<script src>` is kept verbatim as a `data:text/javascript` URL (bundling would turn its globals into
  locals). `</script`/`</style` inside inlined code is escaped. Remote URLs, import maps and other script types are
  left alone for verify to catch. A `src`/`href` must name a file inside the work dir. Write `output/index.html` (≤ 20 MB)
  and `package-manifest.json` (`esbuild` version, `bytes`, `packagedAt`). Failure → `ok: false`, `error = "packaging
  failed: <reason>"` (e.g. `esbuild: Could not resolve "./x.js"`). `verify` = serve `output/`, load `index.html` inside
  `verification/frame.html`, an iframe sandboxed exactly like the site's (`allow-scripts allow-pointer-lock`, so storage
  APIs throw), with every request except those two pages aborted and recorded; wait for `document.readyState ==
  "complete"` (≤ 30s) and 1.2s more, then take the two frames. The report adds `blockedRequests`, and `ok = booted and no
  pageErrors and no blockedRequests` (a static page is fine, so frames needn't differ). `stage` copies the page to
  `game/index.html` (cleaned like source). Both Chrome checks are one helper (`browser.verify_page`); Playwright is an
  optional dependency (`pip install bench[verify]`), and verification is skipped with a note when it's missing.
- **media** (`Media`; `ffmpeg` and `ffprobe` on PATH): `finalize` checks every media file in `work/output/` (sorted, flattened as
  `a-b.png` for `a/b.png`, at most 8) into `output/`. Images (`.png .jpg .jpeg .webp .gif`) must be readable by ffprobe;
  one over 2 MB is re-encoded as JPEG (a GIF isn't). SVGs must parse as XML with an `<svg>` root (size from width/height
  or viewBox) and be ≤ 2 MB. Videos (`.mp4 .webm .mov`) must have a duration; one that isn't H.264/yuv420p mp4, is over
  10 s or over 2 MB is re-encoded (`libx264`, `-t 10`, max 1280 wide, CRF 26 → 32 → 38 until it fits). Each video gets a
  `.poster.jpg` at 30% of its length. A file that is none of those types isn't output at all: it's skipped without an
  error (a model that keeps its generator script in `./output/` shouldn't fail the step), and `output/` holding no media
  file at all is the error `no image or video files in ./output/`. Unreadable files and name clashes are errors. `manifest.json` =
  `{ok, items, errors}` with `ok` = at least one item and no errors. `ok` of the step = at least one item was kept;
  `error` = the manifest's errors (joined with `; `, the first 200 characters, the kept files are still published);
  `verify` = the manifest's `ok`. `keep_source`: text files of at most 512 KB; `output/` only for the files there that
  aren't media (the script that made them), never the images or videos themselves.

### Metrics (from the session log, the same numbers pi-subagents reported)
Over assistant messages: `turns` = count; `tool_calls` = number of `toolCall` content blocks; `tokens_input/output/
reasoning/cache_read` = sums of `usage.<field>`; `tokens_total = input + output`; `cost_usd` = sum of
`usage.cost.total`. `duration_ms` = wall clock of the harness process. `state = failed` when the process exits non-zero, there is no
session file, or the last assistant message has `stopReason: "error"`; `error` = its `errorMessage` or the last
non-empty stderr line (the first 200 characters).

### Harness interface (`src/bench/harness.py`)
Harnesses: `pi` (the default) and `claude-code`. A `-m` spec picks one with a prefix: `claude-code:MODEL[:LEVELS]`
(no prefix, or `pi:`, = pi), in `-m`, `--set` entries and set files alike, so one batch can mix harnesses. Each run
records its harness; batch.json has `harnesses: {name: version}`. The run ids of non-pi harnesses put the harness tag after
the model (`claude-opus-5-5-cc-high-20260928-154152`), so one model under two harnesses never collides.
```python
class Harness:           # one per agent program
    name: str; tag: str                                 # tag: "" for pi, "cc" for claude-code
    def version(self) -> str | None
    def models(self) -> list[str]
    def resolve(self, model) -> str                     # alias -> id (identity by default)
    def levels(self, model) -> list[str]                # supported effort levels, in LEVEL_ORDER
    def display_model(self, model) -> str               # the model name recorded for the run
    def split_spec(self, rest) -> (str, list | None)    # "MODEL@UPSTREAMS:LEVELS" -> ("MODEL:LEVELS", upstreams)
    def pinned(self, model, upstreams) -> str           # the model argument ("model@a,b"); only pi accepts upstreams
    def command(self, model, level, brief, session_dir) -> list[str]
    def env(self, model=None, harness_dir=None) -> dict | None  # the agent's environment (None = inherit)
    def session_file(self, session_dir) -> Path | None  # the raw session in harness/ (never published)
    def session_entries(self, session_dir, brief, level) -> list  # the session in pi's format -> conversation.json
    def metrics(self, session_dir, level) -> dict | None          # parse_session()'s shape; tolerates a growing file
    def finish(self, harness_dir, model, metrics) -> dict         # final touches from the scratch dir (pi: the OpenRouter route
                                                                  # and cost); `notes` join the run's error, `extra` fields join the run
```
Pi: `pi --version`; `pi --list-models` (parse the table); levels via `pi --mode rpc --no-session --model M -ne -ns -np -nc`
sending `{"type":"get_available_thinking_levels"}` and reading the matching response;
command = `pi -p --mode json --model M:LEVEL --session-dir DIR -ne -ns -np -nc BRIEF` (no user extensions, skills,
prompt templates or AGENTS.md, so runs are reproducible); session file = the `*.jsonl` in DIR that isn't pi's stdout (`events.jsonl`).
Every `openrouter/` run adds `-e src/bench/pi_ext/openrouter_routing.ts` (explicit `-e` paths still load under
`-ne`) and sets `BENCH_ROUTE_LOG=<harness dir>/route.jsonl` in that run's environment. A pinned run (`MODEL@slug`)
passes the base id to `--model` and also sets `BENCH_OPENROUTER_ROUTING={"only": [...], "allow_fallbacks": false}`
(never inherited from bench's own environment), which the extension merges into the request's
`provider` field. The extension logs, per response (generation id), `{id, provider}` from its first stream chunk and
`{id, cost}` from the final chunk's `usage.cost`; the run records `route` from that log (see Run). The upstream is part of the recorded model name
(`openrouter/…/flash@deepinfra`), so two upstreams are separate rows; run ids use `-via-`.

Claude Code (`claude`): version = first word of `claude --version`. Models come from a table in the harness (there's no
listing command), mirroring the CLI's own alias table: `claude-fable-5-1`, `claude-opus-5-5`, `claude-opus-5`,
`claude-opus-4-8`, `claude-opus-4-7`, `claude-opus-4-6`, `claude-sonnet-5-5`, `claude-sonnet-5`, `claude-sonnet-4-6`,
`claude-haiku-5-5`, plus the aliases fable/opus/sonnet/haiku (each the newest of its family, `sonnet` = `claude-sonnet-5-5`);
runs are recorded as `anthropic/<id>`. Levels are low, medium, high, xhigh, max (no minimal/off), but only the ones the
model actually takes: the CLI silently clamps a level it doesn't accept (measured: `--effort xhigh` on the two `*-4-6`
models sends `effort=high`), so those are listed without xhigh, and a model that ignores effort entirely (e.g.
`claude-haiku-4-5`) isn't listed at all. Command = `claude -p --model ID --effort LEVEL --output-format stream-json --verbose --safe-mode
--permission-mode bypassPermissions --no-session-persistence --tools=Bash,Read,Write,Edit,Glob,Grep
--disallowed-tools=Agent,Task --disable-slash-commands -- BRIEF`: one direct agent with only the core file and shell
tools (like pi: no sub-agents, web, scheduling, messaging or skills), none of the user's CLAUDE.md, memory, plugins,
hooks or MCP servers (login still works), and nothing saved to the user's session history. `CLAUDECODE` and
`CLAUDE_CODE_*` are removed from its environment (bench may itself run inside Claude Code). The stdout stream-json is
the session; its raw events carry account/session details, so they're not published (for any harness). Conversion to pi's format:
assistant events are merged by message id (the stream emits one per content block, each repeating the usage) and
become assistant messages (text; thinking only when non-empty, print mode usually omits it; `tool_use` → `toolCall`
with Bash/Write/Edit/MultiEdit/Read mapped to pi's bash/write/edit/read names and argument shapes, file paths made
relative to the run dir; other tools keep their name and input); `tool_result` blocks become `toolResult` messages (text blocks joined into one text block; each image block becomes
`{type: "image", mimeType: "image/jpeg", data: <≤320px JPEG thumbnail made with ffmpeg>, sourceMimeType, bytes}`,
without `data` when ffmpeg is missing or fails, never the original ~500 KB image);
messages keep the stream event's `timestamp` (a merged message its first event's; the session entry and the brief the
first one in the stream); the brief is the first user message; an error result adds a final assistant message with `stopReason: "error"`.
Sub-agent events (`parent_tool_use_id` set) are skipped. Metrics: turns = top-level assistant API messages, tool
calls = their `tool_use` blocks; tokens from the final `result.usage` (the stream's per-message usage is a snapshot
taken before output is written and undercounts it; it's only summed while the run is still going), reasoning =
`result.usage.output_tokens_details.thinking_tokens`; cost = `result.total_cost_usd` (Claude Code's estimate at API
prices, also on a subscription); failed = `result.is_error` (error = `result.result`).
Future harnesses and a VM runner plug in here and at "start one agent" in `runner.py`; a container executor mounts one run directory.

### Ctrl-C
Kills every running agent's process group, marks those runs `queued` in batch.json, prints the `--resume` command, exits 130.

### Resume
`batch.json` = `{prompt, kind, page, title, title_is_explicit, harnesses, brief, request, created, runs: [{id, harness, model,
model_arg, level, state}]}`, updated on every state change (`model` = what the site shows, `model_arg` = the harness's id).
`--resume DIR` reads it and, per run: `queued`/`running` → start the agent again (its run directory is emptied first); a
finished agent is never rerun. Then the output step for a `complete` run whose `output` is missing or not `ok` (so a failed
export is retried), and import. Failed and timed-out runs stay as they are. A batch written by a bench that grouped runs by
model (no `id` in its runs) can't be resumed.

## Ranking

The page owner ranks runs in the browser; there is no CLI command for it. Only `bench serve` can save a ranking
(GitHub Pages is static), so the published site shows rankings read-only.

- `bench serve` answers `GET api/local` → `{"rank": true}` and `PUT api/rank?p=<slug>` with body
  `{"ranks": {"<run id>": <int>|null, ...}}`. It validates the slug (`[a-z0-9][a-z0-9-]*`, page must exist), that every
  id is a run of the page, and that each rank is a whole number from 1 to the number of runs (ties allowed; `null`
  = unranked), writes `data/<slug>/ranking.json`, then rebuilds. Errors are `400 {"error": ...}`.
- Cross-site writes are refused: the request must be `Content-Type: application/json` (so another site can't send it
  without a CORS preflight, which the server doesn't answer) → else 415, and an `Origin` header, when present, must
  match the `Host` → else 403.
- `rebuild` copies each run's rank into `page.json.runs` (`rank`, `null` when unranked) and drops `ranking.json` entries
  for runs that no longer exist (e.g. after `bench rm`).
- The viewer only asks `api/local` when served from localhost; when it answers, the page shows a rank picker per row.

## Viewer (docs/)

All four page views use `loadPage(slug)` in dom.js: one fetch of `page.json`, which includes
`runs` sorted by started_at then effort order with ranks applied. `run.json` stays the rebuild source of truth;
`bench list` reads `page.json.runs`. Rebuild removes legacy `results.json`. The loader owns missing-page
parameters and fetch-error messages; run/play find their run by id in `page.runs`.

All five viewer documents enforce a meta CSP: `default-src 'self'; script-src 'self'; style-src 'self';
img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-src 'self'; object-src 'none';
base-uri 'none'`. Dynamic styles use CSSOM properties. The transcript lazily loads local Marked 15.0.12
and renders lexer tokens to DOM nodes with textContent, never innerHTML. Raw HTML stays visible text;
links permit only HTTP(S), and remote Markdown images stay alt text to avoid outside requests.

Shared conventions: runs are ordered by model, then effort from minimal to max (`EFFORTS` in runs.js), not
alphabetically. Effort is shown as a pill whose text is just the level, with a 6-step meter. Model ids show the model
name in bold and the provider prefix quietly (`modelLabel()`). Runs are grouped by vendor with a faint tint and a thin
stripe in the vendor's hue on table rows (page.html) and compare cards (`vendorOf()`/`vendorAttrs()`: the first segment of the
model id up to `-`, or the second after `openrouter/`; sets `data-vendor` and `--vh`). It is color only, so it works under any
sort; runs of one vendor sit together in the default model order. "Best" means the lowest cost, duration or total tokens
among **completed** runs (a failed run never wins), only when at least two runs compete (`rankBy()`); it's marked in green
with ★. Styling is one token set on `:root` (light) redefined under `prefers-color-scheme: dark`, system fonts only.

Your ranking (`run.rank`) is shown as 🥇🥈🥉 then `#4`, `#5`… (`rankLabel()`/`rankChip()`): in the runs table's Rank
column, on gallery cards, compare cards, the run title and the run switcher. When any run of a page is ranked, the table
sorts by rank by default, and the gallery and compare order ranked runs first (`byRankThenModel()`). Under `bench serve`
(`canEditRanks()`), the Rank column holds a `<select>` (– or 1…N) per row, and each change saves the whole page's ranking
(`saveRanks()`), with a status line next to the run count; a failed save reverts the select and shows the error. Data
JSON is fetched with `cache: "no-cache"` so a saved ranking or a new publish is never hidden by the browser cache.

All output rendering goes through one function, `renderOutput(run, base, opts)` in output.js (the click-to-play frame, the
immediate sandboxed frame, the media gallery, or the "no output" message, with the kind step's own error above it) and
one `KIND_UI` table (chip label, tab label, no-output text and failure badge per kind); page, run, compare and play all call
them. Any output with an `entry` is shown in the sandbox, so a new kind needs no viewer code.

- **index.html**: cards per page (thumb, a Game/Media chip, title, model names, n_runs, updated date) → page.html.
- **page.html**: title, a meta line (kind, n runs, n models, last run), the Prompt (prompt.md) and a collapsed Final prompt,
  then **highlights**: the cheapest, fastest and fewest-tokens completed run (each links to it) plus verified count, failed
  count and total spend. Then a "Compare all" link → compare.html and a runs table (thumb, rank, model, effort, harness,
  verified ✓/✗ (`output.verified`), run at (the run's `started_at`, local time, year on hover; in the phone cards a line under the metrics), duration, tokens total/reasoning, cost, tool calls). Harness shows "pi 0.87.1" (name only
  when version is null, "–" when missing).
  A `media` page also has a **Gallery** above the table: one card per run (its thumb, effort, model, cost, duration,
  "N files" when more than one), linking to the run. Expanding a media row shows its outputs. A run whose `state` isn't `complete`
  shows a red `failed`/`timeout` badge in the Verified cell (and a red edge on its row), and its expanded row shows `error`. A completed run
  whose output step failed shows a red "export failed" / "packaging failed" / "output failed" badge there instead of a check mark, still counts
  as completed in the highlights, and its expanded row shows `output.error` above "No playable build recorded for this run.".
  The table is sortable (default: model, then effort), numeric columns are right-aligned with a thin bar under the value
  scaled to the column max, the best completed value in duration / tokens / cost is starred, and every header has a help
  tooltip (shown after 0.5s). Clicking a row expands it and boots that run's game inline; clicking again removes it.
  The Harness cell shows the name with the version small underneath. At ≤720px the table turns into a list of cards
  (headers become sort chips; harness and reasoning tokens are hidden). Above that it never scrolls horizontally: the full
  table fits the 1240px page, and below it columns hide by priority: Reasoning at ≤1199px, Harness and Tool calls at ≤959px, the thumbnail at ≤799px. Model, Effort, Run at, Verified, Duration and Cost (plus
  the rank, caret and Tokens) always stay; hidden metrics are on the run page's Metrics tab and in compare.
  (`.table-wrap` keeps `overflow-x: auto` as a safety net only.) Model names with a pinned upstream wrap inside their cell.
- **run.html**: a header with model (provider above) and effort, a switcher with every run of the same page (grouped by
  model, current one marked), stat tiles (cost, duration, tokens, output tokens, tool calls, turns) each with the run's
  rank among the page's completed runs ("cheapest of 6", "3rd of 6"), a line with verified (`output.verified`), harness,
  started (plus the failed/timeout badge for the agent and an "export failed" / "packaging failed" / "output failed"
  badge when the output step failed), and the agent's `error`. Then tabs (the open tab is kept in the URL hash, e.g. `#transcript`; Transcript and
  Source show a count):
  - *Game*: click-to-play overlay (shows thumb). On click it inserts
    `<iframe sandbox="allow-scripts allow-pointer-lock" allow="fullscreen; autoplay; gamepad">` pointing at `output.entry`.
    There's also an "Open full screen ↗" link (link to `play.html`, which boots it in the sandbox).
  - *Transcript*: renders `session.conversation`. System prompt collapsed. User text. For each assistant message:
    thinking (collapsed, toggle "show thinking"), text (markdown), and toolCall blocks paired with their toolResult by
    `toolCallId`. Tool display: `bash` → command + output, `write` → path + content, `edit` → path + old/new blocks,
    `read`/`ls` → args + output. Any block past 20 lines or 4000 characters starts collapsed behind a toggle: output ("Output (N lines)"),
    a written file ("File (N lines)"), an edit's diff, other tools' arguments, and a bash command (its first line shown).
    An image in a tool result is shown as an `<img>` thumbnail (a data: URL, only for
    jpeg/png/gif/webp with plain base64 data, never SVG) captioned `[image: <type>, N KB]`, never as text.
    `isError` gets a ✗ badge. Show `+m:ss` since session start (the clock time on hover) and per-message token usage. A tool's duration is the `durationMs` on its `toolResult` message (when present). Filter buttons: all / tool calls / errors.
  - *Output* (instead of Game, for a `media` run): every `output.items` entry as a captioned figure (file name, size, duration,
    bytes, a `download` link). Images, **SVGs included**, are only ever shown with `<img>` (which never runs an
    SVG's scripts), never inlined or put in an object/embed/iframe, and never linked for viewing on this origin.
    Videos use `<video controls preload="none">` with the poster, and never autoplay.
  - *Page* (instead of Game, for a `web` run): the packaged page with click-to-play, in the same sandboxed iframe as games.
  - *Source*: a file list, and clicking a file shows it in a `<pre>`. The first code file opens right away.
  - *Metrics*: all metrics as a table of raw values (with a readable form beside durations, costs and big counts,
    including Harness, State, Error and the output's ok / verified / error), plus links to download the raw session files.
- **compare.html**: one card per run (all runs of the page by default), laid out as a grid of ~380px columns that wraps
  into rows (3 across at desktop width, 1 on phones, never sideways scrolling), ordered by model then effort. Each card has
  the model, its effort pill (plus the failed/timeout badge), one line with harness, duration, tokens and cost (the best
  among the shown runs starred), and its game with click-to-play (each column boots independently, never automatically),
  or for a `media` run its outputs stacked (the Play all button is hidden when there are no games).
  Cards are subgrids spanning three grid rows (heading, metrics, output), so those line up across a row even when a metrics line wraps.
  Cards are grouped by vendor (`groupByVendor()`, `vendorOf()`): a section per vendor with a quiet header (name from
  `VENDOR_NAMES`/`vendorName()`, run count, thin rule in the vendor's hue), always shown, even with a single vendor. Within a
  group the order is `byRankThenModel()`; groups go by their best rank, then unranked groups by name. Each group is its own
  grid, so the subgrid rows line up per group. The ★ best values are still computed across all shown runs, and `&r=` only
  limits which runs (and so which groups) appear. `#columns` holds the groups, not the cards.
  A card with output also has a small ↗ button (`a.popout`, next to the effort pill) that opens `play.html` for that run in a
  separate popup window (`window.open(..., "popup,noopener,width=1280,height=800")`); middle/cmd-click falls back to the
  `href` and opens a tab. It never carries `data-play`, so Play all ignores it.
- **play.html**: one run's output alone. A 36px bar (model, effort pill, state badge, "Run page →" link to run.html) above
  the output, which fills the rest of the window: for `godot`/`web` runs one `sandboxedGame()` iframe that boots immediately
  (opening the window was the click), for `media` runs `mediaGallery()` (videos still don't autoplay). A run's `error` is
  shown above the output; a missing/unknown `p`/`r` or a run without output shows a message. Never links or embeds the raw entry URL.
- Everything renders from the JSON. There are no per-page HTML files. It must work under a sub-path (`/llm-bench/`),
  so use only relative URLs. It supports dark mode via `prefers-color-scheme`, has readable defaults, and has no frameworks.

## Tests (`uv run pytest`)

- CLI: unit tests plus an end-to-end import of a small synthetic batch directory (run directories with `run.json`,
  `work/`, `harness/`, `output/`). The fixture uses tiny fake engine
  files and a real Godot `index.html` template, and covers dedupe, the html rewrite, cleaning, the secret abort and
  redaction, idempotency, rm, and rebuild.
- Viewer: Playwright (Python, `channel="chrome"`, which uses the installed Google Chrome, so no browser download)
  against `bench serve` on a fixture site. It covers each page rendering without console errors, click-to-play inserting
  a sandboxed iframe, the transcript's tool calls and error badges, and compare with 3 runs. A `media` fixture page
  (`art`: an SVG with an embedded script, a PNG and a 1 s mp4) covers the gallery, the Output tab (the SVG's script
  never runs, videos don't autoplay), expanded rows and compare.
  Also covered: effort-order sorting, the highlights (a failed run never wins "cheapest"), best-value stars, the run
  page switcher and ranks, the linkable tab hash and the Source tab opening its first file.
- `bench run`: a fake `pi` (a Python script put first on PATH by the test) that answers `--version`, `--list-models`,
  the RPC levels request, and `-p` runs by writing a canned session file and a tiny project; env vars make it fail,
  hang, or exit non-zero. Covers level parsing (`all`, ranges, explicit lists, off excluded by default, unsupported
  level → error before anything starts), the plan/confirmation, `-j`, timeout, failed runs being imported, metrics
  against the real voxel-horse `high/session.jsonl` numbers (when present), and `--resume` not rerunning finished
  agents (and retrying a failed output step), a toy kind defined in a test running end to end, and the run directory layout. For a media brief the fake pi writes `./output/` (SVG, PNG and an ffmpeg-made mp4) plus a script and a
  leftover binary frame; with `FAKE_PI_BAD_OUTPUT` it adds an unreadable PNG (the step's error) and a text file in
  `./output/` (published as source, not an error). `tests/test_media.py` checks the media step on ffmpeg-generated inputs (trim + re-encode,
  oversized image → JPEG, bad files, empty output, too many files, name clashes, non-media files being skipped); media tests are skipped without
  ffmpeg. A slow test (skipped without `godot`) exports a tiny real project. No test calls a real model.
  For a web brief the fake pi writes `index.html`, `main.js`, `style.css` and a fake npm package in `node_modules/`.
  `tests/test_web_kind.py` (skipped without esbuild) packages pages with the real esbuild (module + inline module +
  classic scripts, stylesheets, imported assets, `</script>` escaping, remote/importmap left alone, missing imports and
  paths outside the project), verifies offline in the sandbox (a remote fetch and localStorage both fail it), and runs
  a web batch end to end into the viewer (kind chip, Page tab, the bundled package running in the sandboxed iframe).
- Integration: serve the published voxel-horse page (real Godot builds) from a temp site, and check that all 3 games boot
  inside the sandboxed iframe in compare. Headless Chrome
  needs `--enable-unsafe-swiftshader --use-angle=swiftshader` for WebGL. Godot removes `#status` from its document
  once the game has started, which is the boot signal.
