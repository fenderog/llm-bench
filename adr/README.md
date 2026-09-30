# Architecture decision records

Why llm-bench is built the way it is. Each record covers one decision, the alternatives that were turned
down, and what the decision costs.

This folder sits at the repo root and not under `docs/`, because everything in `docs/` is published to
GitHub Pages.

## How these docs fit together

- **SPEC.md**: the contract. It says *what* the system does.
- **adr/**: *why* it does it that way.
- **AGENTS.md**: how to work in the repo, plus the gotchas.

Gotchas (Playwright sleep, `append(null)`, Safari Range requests...) aren't decisions, so they stay in AGENTS.md.

## Writing one

Copy `template.md` to `NNNN-short-title.md` using the next number, and add it to the index below.

- A record's status is Proposed, Accepted, Superseded by NNNN, or Deprecated.
- Don't rewrite an accepted record when the decision changes. Write a new one and mark the old one superseded.
  Small factual updates, such as a renamed file, are fine.
- If a record backs a rule in AGENTS.md, point to it from that rule, like "(ADR-0004)".

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-static-site-on-github-pages.md) | Static site on GitHub Pages, no backend | Accepted |
| [0002](0002-lean-stack.md) | Lean stack: stdlib-only CLI, vanilla JS, no build step | Accepted |
| [0003](0003-repo-is-the-database.md) | The repo is the database; `docs/data` is generated | Accepted |
| [0004](0004-sandbox-untrusted-output.md) | Untrusted model output is always sandboxed | Accepted |
| [0005](0005-clean-and-secret-scan-fail-closed.md) | Clean and secret-scan before publishing, fail closed | Accepted |
| [0006](0006-one-kind-per-page.md) | A page is one prompt with one kind | Accepted |
| [0007](0007-pi-session-format-is-canonical.md) | pi's session format is canonical; harnesses convert into it | Accepted |
| [0008](0008-godot-nothreads-and-engine-dedupe.md) | Godot: no-threads web export, engine deduped by hash | Accepted |
| [0009](0009-agents-run-as-local-processes.md) | Agents run as local processes, not in a VM | Accepted |
| [0010](0010-rankings-are-local-only.md) | Rankings are written only locally; the site is read-only | Accepted |
| [0011](0011-publish-pushes-to-main.md) | `bench publish` pushes to `main`, no PR flow | Accepted |
| [0012](0012-asset-cache-busting.md) | Asset cache-busting | Proposed |
| [0013](0013-web-kind-packaged-with-esbuild.md) | Web pages are packaged into one file with esbuild | Accepted |
| [0014](0014-openrouter-upstream-routing.md) | Pin the OpenRouter upstream provider per run (`MODEL@upstream`) | Accepted |
