# bench — a CLI for publishing LLM benchmark results to GitHub Pages

Status: historical. This is the paper design written before anything was built, and much of it changed
(typer → argparse, generic artifacts → one kind per page, `bench push` → `import`/`run`). The current contract is
SPEC.md, and the decisions and their reasons are in `adr/`.

## The idea in one paragraph

The repo holds a static site plus folders of data and artifacts. GitHub Pages
serves all of it. The site has no build step: each page is a thin HTML shell
that `fetch()`es its JSON when it loads and renders tables, charts, and artifact
viewers in the browser. The CLI never touches HTML after scaffolding. It only
copies files, writes and validates JSON, then commits and pushes. "Dynamic" here
means the data changes and the site picks it up without anything being
regenerated.

```
  benchmark run ──► metrics + artifact(s) ──► bench push ──► git commit + push
   (image / video / wasm / html site)                             │
                                                                  ▼
  browser ◄── GitHub Pages serves docs/ ◄── docs/<page>/runs/<run_id>/...
     └─ page shell fetches results.json, then renders the table, chart, and
        artifacts (img / video / sandboxed iframe)
```

## Core concepts

- **Page** is one benchmark, such as "MMLU sweep" or "Make a Snake game".
- **Run** is one `bench push`: a single execution of the benchmark, usually one model with one config.
  It contains **records** (rows of metrics) and **artifacts** (the files it produced).
- **Artifact** is one file or directory a run produced. It has one of these kinds:

| kind | what it is | how the site shows it |
|---|---|---|
| `image` | png, jpg, gif, webp, svg | `<img>` with a lightbox |
| `video` | mp4, webm | `<video controls>` with a poster frame if one exists |
| `site` | a directory with an entry html (can include js, css, wasm, assets) | sandboxed `<iframe>`, with an "open full screen" link |
| `godot` | a Godot web export (a `site` the CLI recognizes, see [Godot web exports](#godot-web-exports)) | same as `site`, with the engine files deduped and a click-to-play overlay |
| `wasm` | a bare `.wasm` file | loaded into the page's **harness** (a site shared by the page) through `?wasm=<url>` |
| `session` | an agent transcript: `conversation.json`, `events.jsonl`, `status.json`, `output.md` (cleaned, see [Session transcripts](#session-transcripts)) | Transcript tab: a timeline of messages, thinking, and tool calls |
| `source` | the project files the model wrote | Source tab: a file tree with syntax highlighting and a diff in compare |
| `file` | anything else (json, txt, logs) | link, plus an inline preview for text |

The CLI infers the kind from the extension, or from the fact that a path is a
directory, and `--kind` overrides it. A directory counts as a `site` when it
contains `index.html`. Otherwise the entry file has to be named.

## Repo layout

GitHub Pages is set to deploy from `main` → `/docs`, so no Actions are needed.

```
my-bench-site/
├── bench.toml                       # CLI config: site title, repo, size limits
└── docs/                            # ← GitHub Pages root
    ├── .nojekyll                    # REQUIRED: otherwise _next/, _app/ and other _dirs aren't served
    ├── index.html                   # home: lists every page (reads data/pages.json)
    ├── run/index.html               # shared run-detail view: /run/?page=<slug>&id=<run_id>
    ├── compare/index.html           # side-by-side view: /compare/?page=<slug>&a=<id>&b=<id>
    ├── assets/app.js, style.css     # shared renderer
    ├── data/pages.json              # manifest of all pages
    ├── engines/                     # shared Godot engine builds, stored once per build
    │   └── 41560f8755ed/            #   sha256 prefix of the wasm+js pair
    │       ├── godot.wasm           #   38 MB (Godot 4.7.2 nothreads)
    │       ├── godot.js
    │       └── godot.audio.worklet.js ...
    └── snake-game/
        ├── index.html               # 5-line shell
        ├── page.json                # page config
        ├── harness/                 # optional: a shared loader for bare-wasm artifacts
        │   └── index.html
        ├── results.json             # compiled from runs/*/run.json (the CLI regenerates it)
        └── runs/
            └── 2026-09-26T15-40-03_claude-y/
                ├── run.json         # records + artifact manifest (source of truth)
                └── artifacts/
                    ├── screenshot.png
                    ├── gameplay.mp4
                    ├── gameplay.poster.jpg   # generated when ffmpeg is on PATH
                    ├── session/              # a "session" artifact (cleaned)
                    │   ├── conversation.json
                    │   ├── events.jsonl
                    │   ├── status.json
                    │   └── output.md
                    ├── source/               # a "source" artifact: project.godot, scenes/, scripts/, README.md
                    └── game/                 # a "godot" artifact
                        ├── index.html        #   GODOT_CONFIG rewritten to point at /engines/41560f…/
                        ├── index.pck         #   game data, usually a few MB
                        └── index.png, icons…
```

## Data model

**`<slug>/page.json`**
```json
{
  "title": "Make a Snake game",
  "description": "One-shot: 'write a playable snake game in the browser'",
  "primary_metric": "score",
  "metrics": { "score": { "higher_is_better": true },
               "tokens": { "higher_is_better": false } },
  "group_by": "model",
  "charts": [ { "type": "bar", "x": "model", "y": "score" } ],
  "primary_artifact": "game",
  "harness": null
}
```
`primary_artifact` names the artifact that becomes the thumbnail or tile in the
gallery. `harness` is the relative path to a loader page, and is only needed
when runs produce bare `.wasm`.

**`runs/<run_id>/run.json`**
```json
{
  "run_id": "2026-09-26T15-40-03_claude-y",
  "timestamp": "2026-09-26T15:40:03Z",
  "model": "claude-y",
  "params": { "temperature": 0 },
  "notes": "new system prompt",
  "git_sha": "abc1234",
  "records": [ { "metrics": { "score": 8, "tokens": 5120 } } ],
  "artifacts": [
    { "name": "game",       "kind": "site",  "path": "artifacts/game/", "entry": "index.html", "bytes": 1843200 },
    { "name": "screenshot", "kind": "image", "path": "artifacts/screenshot.png", "bytes": 210000 },
    { "name": "gameplay",   "kind": "video", "path": "artifacts/gameplay.mp4",
      "poster": "artifacts/gameplay.poster.jpg", "bytes": 8400000 }
  ]
}
```
`results.json` is the list of every `run.json` for the page, concatenated, so
the page makes one fetch. Artifact paths are relative to the run folder, and the
renderer resolves them.

Records can also carry their own `artifacts` field when one run produces
several items, for example one image per prompt. The input file can then give
each row a local path, which the CLI copies in and rewrites.

## CLI surface

```
bench init                                   # scaffold docs/ (with .nojekyll), bench.toml, print Pages setup steps
bench serve                                  # local preview (serves .wasm with the right MIME type)

bench page new <slug> --title "..." [--desc "..."]
      [--metric score:max --metric tokens:min]
      [--harness ./my-wasm-loader/]          # copies into <slug>/harness/
bench page list | show <slug> | rm <slug>

bench push <slug> [results-file]             # metrics are optional, artifact-only runs are fine
      [-a, --artifact PATH[:name]] ...       #   file or directory; repeatable
      [--kind site|image|video|wasm|file]    #   applies to the preceding --artifact
      [--entry play.html]                    #   entry file for a site dir without index.html
      [--model NAME] [--note "..."] [--param k=v ...]
      [--metric k=v ...]                     #   quick inline metrics without a results file
      [--dry-run] [--no-git]

bench runs list <slug>
bench runs rm <slug> <run_id>
bench rebuild [<slug>]
bench du                                     # repo and site size by page and by run, measured against the limits
```

What `bench push` does, step by step:
1. Load `page.json` and fail if the page doesn't exist.
2. Parse metrics from the file and/or `--metric` flags.
3. Check the artifacts:
   - resolve the kind, and check that the entry exists for `site`
   - enforce size limits (see below)
   - check sites for absolute paths (`src="/..."`), which break under `/<repo>/`, and warn
   - for `wasm`, require the page to have a harness
4. Copy everything into `runs/<run_id>/artifacts/`. Generate the video poster when ffmpeg exists.
5. Write `run.json`, rebuild `results.json`, and update `data/pages.json`.
6. `git add` → `commit -m "bench: snake-game ← claude-y (3 artifacts, 10.4 MB)"` → `push`.
7. Print the run URL: `https://you.github.io/repo/run/?page=snake-game&id=…`

## Example session

```
$ bench page new snake-game --title "Make a Snake game" --metric score:max
✓ created docs/snake-game/

$ bench push snake-game \
    -a out/claude-y/game/ -a out/claude-y/screenshot.png -a out/claude-y/gameplay.mp4 \
    --model claude-y --metric score=8 --metric tokens=5120
  game        godot  4.x export, threads: off ✓
                     engine 38 MB → engines/41560f8755ed/ (already published, 0 B added)
                     index.pck 7.5 KB, html rewritten
  screenshot  image  210 KB
  gameplay    video  8.4 MB → transcoded 720p, 2.1 MB, poster generated
✓ wrote runs/2026-09-26T15-40-03_claude-y/
✓ pushed a1b2c3d → main
  https://you.github.io/my-bench-site/run/?page=snake-game&id=2026-09-26T15-40-03_claude-y
```

## Website mockups

Page (`/snake-game/`) has two tabs, a table and a gallery:
```
┌───────────────────────────────────────────────────────────────┐
│ ← All pages      Make a Snake game                            │
│ [ Table ]  [ Gallery ]                          compare: ☐ ☐  │
│                                                               │
│ Gallery (primary artifact per run, sorted by score)           │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │  [thumb /    │ │  [thumb /    │ │  [thumb /    │            │
│ │   poster]    │ │   poster]    │ │   poster]    │            │
│ │ claude-y   8 │ │ gpt-x      7 │ │ llama-z    3 │            │
│ │ ▶ play  ☐cmp │ │ ▶ play  ☐cmp │ │ ▶ play  ☐cmp │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
└───────────────────────────────────────────────────────────────┘
```

Run detail (`/run/?page=snake-game&id=…`):
```
┌───────────────────────────────────────────────────────────────┐
│ ← Make a Snake game   claude-y · 2026-09-26 15:40 · score 8   │
│ params: temperature=0   notes: new system prompt              │
│                                                               │
│ [ game ] [ screenshot ] [ gameplay ] [ files ]   ← artifact tabs│
│ ┌───────────────────────────────────────────────────────────┐ │
│ │                                                           │ │
│ │     <iframe sandbox="allow-scripts" src=".../game/">      │ │
│ │                                                           │ │
│ └───────────────────────────────────────────────────────────┘ │
│  ⤢ open full screen   ⟳ reload   ⬇ download                   │
└───────────────────────────────────────────────────────────────┘
```

Compare (`/compare/?page=…&a=…&b=…`) shows the same artifact from two runs side
by side, with their metrics above each. This is the most useful view when the
outputs are generated sites or games.

## Godot web exports

The main artifact is a Godot game exported for the web, with one per run most
of the time. This is a real export, from
`effort-runs/2026-09-26-001158-gpt6sol-voxel-horse/wasm/high`, made with Godot
4.7.2 and the `web_nothreads_release` template:

```
index.html                         5 KB   loader page, contains GODOT_CONFIG and GODOT_THREADS_ENABLED
index.js                         273 KB ┐
index.wasm                        38 MB │ engine: byte-identical across the low/medium/high exports
index.audio.worklet.js             7 KB │ (same sha256 for all three)
index.audio.position.worklet.js    3 KB ┘
index.pck                        7.5 KB   the actual game
index.png, index.icon.png, index.apple-touch-icon.png   ~40 KB
export-manifest.json                      {"godot": "4.7.2…", "threads": false, "template": …}
verification/frame-1.png, frame-2.png, verify-report.json   free thumbnails and a boot check
```

`push` recognizes a Godot export from `export-manifest.json`, or falls back to
detecting `GODOT_CONFIG` in the html plus a `.pck`.

### 1. Deduplicate the engine ✅ verified

The engine is **38 MB of the 38.3 MB** export, and the game itself is 7.5 KB.
Without deduplication, the 1 GB Pages limit would allow about 25 runs. With
it, a run costs about **100 KB** (pck, html, icons, thumbnail), and the engine
costs 38 MB once per Godot version and template.

How it works, as prototyped in `spike/build.py`:
1. Hash the four engine files and copy them once to `engines/<sha12>/godot.{wasm,js,audio.worklet.js,audio.position.worklet.js}`.
   Godot's `locateFile` maps every `godot.*` request to `<executable>.*`, which is why the files use this naming.
2. Rewrite the run's `index.html`:
   - `<script src="index.js">` → `<script src="../../../../../engines/<sha12>/godot.js">`
   - `GODOT_CONFIG.executable` → `"../../../../../engines/<sha12>/godot"`
   - `GODOT_CONFIG.mainPack` → `"index.pck"`. **This is required**, because otherwise the pck path defaults to `<executable>.pck`, which is in the engine folder.
   - the `fileSizes` key for the wasm → the new path. This only affects the progress bar.
3. Copy everything else as-is, and drop `export-manifest.json` and `verification/` into `run.json` metadata or the thumbnail.

### 2. Threads ✅ handled

`export-manifest.json` has `"threads": false`, and the html has
`const GODOT_THREADS_ENABLED = false;`. `push` reads either one. It refuses
threaded builds by default and accepts them with `--allow-threads`, which marks
the run `needs_coi` so it's playable in full screen only. The current pipeline
(`fe-godot-web-export`) already uses the no-threads template, so in practice
this is just a safety check.

### 3. Playing in the sandboxed iframe ✅ verified

Test setup: headless Chrome with a local server that mimics Pages
(`Access-Control-Allow-Origin: *`, `application/wasm`, **no** COOP/COEP), and
`<iframe sandbox="allow-scripts allow-pointer-lock">` with no `allow-same-origin`.

| Scenario | Result |
|---|---|
| Rewritten game loaded directly | boots, animates, no errors |
| Same game in the sandboxed iframe | boots, animates. The engine and pck load cross-origin without problems. |
| Compare page: low, medium, and high in three sandboxed iframes side by side | all three boot and animate |
| IndexedDB (`user://`) in an opaque origin | no failure, the game starts normally |
| Console noise | `Failed to assign PWA callback SecurityError: … sandboxed and lacks 'allow-same-origin'` appears once per game. It's harmless, and the viewer can ignore it. |

Findings that affect the viewer:
- **The compare view downloads the engine once per iframe** (3 × 38 MB in parallel). Each sandboxed iframe has its own opaque origin, and the requests start together, so they can't share one download. Fix: use click-to-play per iframe, or boot them one after another so the later ones can hit the HTTP cache (untested).
- **The gallery must never boot the engine.** Tiles use `verification/frame-1.png` as the thumbnail, and only the run and compare views load games.
- Click-to-play is still worth having for keyboard focus and audio unlock. Neither has been tested yet.

### Not yet verified
- A real GitHub Pages deployment. The spike used a local server with the same headers.
- Safari and Firefox, and real GPUs. The spike ran headless Chrome with SwiftShader.
- Audio and keyboard input inside the sandboxed iframe.
- Whether Pages gzips `.wasm`. That decides whether a cold play costs about 38 MB or about 9 MB of bandwidth.

## Importing from `effort-runs/` directly

Your runs already have a fixed layout (`fe-model-effort-fanout/1`), so the
main command reads a whole run folder instead of taking `--artifact` and
`--metric` flags:

```
bench import ~/dev/effort-runs/2026-09-26-001158-gpt6sol-voxel-horse [--page voxel-horse]
```

**A page is one prompt.** Its runs are every model × effort level ever run
against that prompt. One import adds three runs (low, medium, high). A later
import of the same prompt with a different model adds more runs to the same
page.

| Source | Becomes |
|---|---|
| `prompt.md` | page description. `import` creates the page on first sight (slug from the folder name minus the timestamp and model), and later imports match the prompt by hash. |
| `data.json → runs.<level>` | one bench run per effort level: model, thinkingLevel, tokens.*, costUsd, durationMs, toolCalls, turns |
| `wasm/<level>/` | the run's `godot` artifact (deduplicated engine) |
| `wasm/<level>/verification/frame-1.png` | thumbnail. `verify-report.json.ok` becomes a `verified` field. |
| `<level>/conversation.json`, `events.jsonl`, `status.json`, `output.md` | the `session` artifact (see below) |
| `<level>/**` minus `.godot/`, session files, and `.DS_Store` | the `source` artifact: the project files the model wrote |

## Session transcripts

**Decision: publish the whole session**, meaning messages, thinking summaries,
every tool call with its arguments and output, timings, and usage. These are
real files from the `high` run:

| File | Size | Contents | Published as |
|---|---|---|---|
| `conversation.json` | 107 KB | 39 entries: `session`, `model_change`, `thinking_level_change`, and `message` with role `system`, `user`, `assistant`, or `toolResult`. Assistant blocks are `thinking`, `toolCall`, or `text`. Each assistant message carries `usage` and `cost`. | cleaned → `session/conversation.json` (the viewer's main source) |
| `session.jsonl` | 93 KB | identical to `conversation.json` | skipped |
| `events.jsonl` | 363 KB | `tool_execution_start/update/end`, `turn_start/end`, and so on, with timestamps | cleaned → `session/events.jsonl` (the viewer takes per-tool durations from it) |
| `status.json` | 13 KB | run lifecycle, pid, deadlines, extension digests | cleaned → `session/status.json` (download only) |
| `output.md` | 9 KB | final task + answer | `session/output.md`, shown as the run summary |

### Cleaning (`import` and `push` both run it; it can't be turned off, only tuned)

Your pages will be public, so the pipeline runs **before** anything is
written into `docs/`:
1. **Strip encrypted reasoning blobs** (`thinkingSignature` / `encrypted_content`). They're opaque and useless to readers, and they make up about 150 KB of the `high` run.
2. **Rewrite paths:** `/Users/<you>` → `~` and `/Volumes/M2SSD` → `<vol>`. The `high` run has 20 such paths. The rewrite list is configurable in `bench.toml`.
3. **Drop machine noise:** `pid`, `completionOwnerId`, session file paths, and `launchContractDigest`.
4. **Scan for secrets.** Patterns include `sk-…`, `ghp_…`, `github_pat_…`, `AKIA…`, `xox[bp]-…`, `-----BEGIN … PRIVATE KEY`, and high-entropy `*_KEY=` / `*_TOKEN=` values. **Any hit aborts** the import and prints the file, line, and a masked match. `--redact` masks the matches and continues. The first real run scanned clean.
5. `--dry-run` prints the summary: bytes before and after, paths rewritten, and secret hits.

Cleaned session size: about 300–350 KB per run, so about 1 MB per import.
That's fine in the repo.

### Transcript viewer (run page → Transcript tab)

```
┌────────────────────────────────────────────────────────────────────┐
│ gpt-6-sol · high · 3m16s · 32.7k tok · $0.146 · 16 tool calls      │
│ [ Game ] [ Transcript ] [ Source ] [ Metrics ] [ Raw files ⬇ ]     │
├────────────────────────────────────────────────────────────────────┤
│ ▸ System prompt (13 KB)                                  collapsed │
│ ● User   Task: Goal: Generate a complete, playable Godot 4.7.2 …   │
│                                                                    │
│ ◆ +0:04  thinking  "Inspecting the current workspace"      2.8k tok│
│   └ ls  path="."                                    0.0s  ✓       │
│       ▸ high/ low/ medium/ prompt.md                               │
│ ◆ +0:41  thinking  "Writing the horse script"             ...      │
│   └ write  scripts/main.gd (5.7 KB)                       ✓       │
│       ▸ view file (syntax highlighted)                             │
│ ◆ +1:12  bash  godot --headless --path "$PWD/high" --quit-after 5  │
│       ▾ Godot Engine v4.7.2 …                            4.1s  ✗   │
│         ERROR: Node not inside tree. Use look_at_from_position()…  │
│ ◆ +1:20  edit  scripts/main.gd  (diff view)               ✓       │
│   …                                                                │
│ ● Assistant (final)  rendered markdown                             │
│                                                                    │
│ filter: [all] [tool calls] [errors only]   ☐ show thinking         │
└────────────────────────────────────────────────────────────────────┘
```

- Tool calls are paired with their `toolResult` by `toolCallId`. Durations come from `events.jsonl` `tool_execution_start/end`.
- `write` shows the file, `edit` shows a diff, `bash` shows the command and output, and a result with `isError` or a non-zero exit gets an ✗ badge.
- Results are collapsed past about 20 lines. The whole transcript renders client-side from one JSON fetch.
- **Compare view:** transcripts side by side, low | medium | high, aligned by turn number. Seeing how effort changes the path is probably the most interesting view on the site.

### Source tab

It shows a file tree of what the model wrote (`project.godot`, `scenes/`,
`scripts/main.gd`, `README.md`), with syntax highlighting and download as
zip. The compare view can diff `scripts/main.gd` between effort levels.

## Short videos

These are fine to keep in the repo. `push` transcodes with ffmpeg when it's
available: H.264 MP4, max 720p, `-crf 28`, `+faststart`, no audio unless
`--keep-audio`. A 30-second clip ends up around 1–4 MB. `push` also extracts a
poster frame for the gallery tile.

## Serving artifacts on GitHub Pages: constraints and decisions

| Concern | Reality on Pages | Decision |
|---|---|---|
| `.wasm` MIME type | Served as `application/wasm`, so `instantiateStreaming` works | nothing needed |
| `_`-prefixed dirs | Jekyll drops them | always write `docs/.nojekyll` |
| Absolute paths in generated sites | The site lives under `/<repo>/<slug>/runs/…`, so `/game.js` returns 404 | `push` scans html, css, and js for root-absolute URLs and warns. Optionally `--fix-paths` or `--base` injection. |
| Untrusted LLM-written html/js | It would run on **`you.github.io`, an origin shared by all your Pages repos** | iframe `sandbox="allow-scripts"` **without** `allow-same-origin`, which gives it an opaque origin with no access to your cookies or storage. Pages sends `Access-Control-Allow-Origin: *`, so fetches and ES modules inside still work. "Open full screen" loses the sandbox, so the link is labeled. |
| Threaded wasm (`SharedArrayBuffer`) | Needs COOP/COEP headers, which Pages **can't set** | Export Godot single-threaded (see [Godot web exports](#godot-web-exports)). For anything that must use threads: a service-worker workaround, full screen only, flagged with `"needs_coi": true`. |
| Git file limits | Pushes over 50 MB warn, and **over 100 MB are rejected** | default limits: warn at 25 MB per file, refuse at 95 MB |
| Git LFS | Pages serves the LFS *pointer*, not the file | don't use LFS |
| Site size | Published site limit is **1 GB**, with a soft 100 GB/month bandwidth limit | Godot engine dedupe (the big win), plus video transcoding. `bench du` tracks usage. Each Godot play costs ~40 MB of bandwidth on first load, so ~100 GB/month allows ~2,500 cold plays. |
| Repo growth | Every video stays in history forever | Phase 2 option: move `docs/` to a `gh-pages` branch the CLI owns and can squash, and/or add an external store (R2 or S3) for large files, with `path` becoming a full URL |

## Tech choices (proposed)

| Piece | Choice | Why |
|---|---|---|
| CLI | Python, `typer`, installed with `uv tool install` | benchmark code is usually Python |
| Site | vanilla JS plus one chart lib from a CDN (Chart.js or Observable Plot) | no build step |
| Hosting | Pages from `main:/docs` | no Actions workflow to maintain |
| Git | CLI shells out to `git` | uses your existing auth |
| Optional | `ffmpeg` for posters and transcoding, Playwright for site thumbnails later | degrades gracefully when missing |

## Decisions so far

- **The site is its own repo**, with Pages serving `main:/docs`.
- **The CLI is Python** (`typer`, installed with `uv tool install`).
- **A page is one prompt.** Its runs are model × effort level, added over time by `bench import`.
- Wasm artifacts are **Godot 4.7.2 web exports, single-threaded**, made by `fe-godot-web-export`. The engine is deduplicated into `engines/<hash>/` (verified).
- **Full sessions are published** (transcript, tool calls, timings, usage) along with the generated source. They always go through the cleaning pipeline, and a secret-scan hit aborts the import.
- Videos are **short clips**. They're stored in the repo and transcoded to 720p.
- There's **one primary artifact per run**. Record-level artifacts are deferred.
- Metrics come from `data.json` (`fe-model-effort-fanout/1`).

## Build order

1. `bench init` for the repo scaffold, and `bench import` for voxel-horse end to end: Godot dedupe, cleaning, and `run.json`/`results.json`. Check it with `bench serve`.
2. Viewer: home page, prompt page (table and gallery), and the run page with the Game, Transcript, Source, and Metrics tabs.
3. Compare view (games with click-to-play, transcripts, source diff).
4. Git commit and push, then the first real Pages deploy. Verify the items in "Not yet verified".
5. `bench push` (the generic path for non-effort-runs artifacts, and videos), plus `bench du`, `runs rm`, and `rebuild`.

## Open questions

- Repo name and GitHub account for the site. This decides the URL, `you.github.io/<repo>/`.
