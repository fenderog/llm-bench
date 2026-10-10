# 0018. One Kind interface; `state` is the agent's, `output` is the kind step's

- Status: Accepted
- Date: 2026-10-02
- Amends: [0006](0006-one-kind-per-page.md) (how a kind is built), [0013](0013-web-kind-packaged-with-esbuild.md).

## Context

Kind-specific behaviour was spread over layers: a three-way branch in the runner, directory sniffing in the importer,
a `web=True` flag inside the verifier, mutually exclusive `game` / `media` fields in `run.json`, and the same
`if (r.media) … else if (r.game)` block in four viewer pages. Three vocabularies described one run's state
(`batch.json`, the progress table, `run.json`) and a run whose export failed was "complete" with an `error`.
A fourth kind would have touched about ten places in Python and twenty in JS.

## Decision

- **A kind is one class** in `src/art_crit/kinds/` (`Godot`, `Media`, `Web`), registered in `KINDS` like `HARNESSES`:
  `tools`, `brief()`, `finalize(work, out)`, `verify(out)`, `stage(out, run_dir, ctx)`, `keep_source(rel, path)`.
  The runner and the importer call these and never branch on the kind's name. The headless-Chrome check is one shared
  helper (`browser.verify_page`) that the Godot and web kinds call with their own readiness test and verdict.
- **`run.json` has one `output` field**, `{kind, <kind fields>, ok, verified, error}`, or `null` when the agent never
  finished. Games and pages carry `entry`, media carries `items`.
- **Three questions, three places**: `state` (+ `error`) says what the agent did (queued | running | complete | failed |
  timeout); `output.ok` / `output.error` say what the kind step made of the work (export, packaging, normalization);
  `output.verified` says whether the boot, offline or file check passed. The progress table's other labels are
  transient and never written.
- **The viewer has one `renderOutput(run, base, opts)`** (and one `KIND_UI` table for names, tab labels and
  messages) that every page uses; a kind step that failed gets its own badge ("export failed", "packaging failed")
  and its error is shown with the output, not as the agent's error.

## Alternatives considered

- **Kind modules as free functions plus a dispatch table**: the same, with the surface implied rather than stated.
- **A `status` per stage in `batch.json`** (exporting, verifying…): couples resume logic to progress cosmetics.
- **Keep `game` / `media` and add flags**: leaves the viewer's four-way duplication.

## Consequences

- A new kind is one class (plus its brief) in Python; the viewer shows any output with an `entry` in the sandbox, and a
  new `KIND_UI` row only changes names. A test defines a toy kind and runs it end to end.
- A run that exported nothing still counts in the page's highlights, because the agent completed.
- Resume re-runs a kind step whose `output` is missing or not ok, and never re-runs a finished agent.
