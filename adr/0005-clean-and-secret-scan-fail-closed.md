# 0005. Clean and secret-scan before publishing, fail closed

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

The site publishes full agent sessions, source files and model-written SVGs to a public repo (0001, 0003).
These files contain:
- the owner's home directory and volume paths,
- pids and session ids,
- opaque encrypted reasoning blobs (~150 KB per run),
- possibly a secret an agent printed.

Anything pushed to the repo stays in git history, so a leaked secret can't be taken back by deleting the file.

## Decision

- **Cleaning always runs on import.** It can't be turned off, only tuned in `art-crit.toml [clean]`. It:
  - strips `thinkingSignature`/`encrypted_content`,
  - rewrites paths (home → `~`, plus configured rewrites),
  - drops keys that are machine noise.
- **The secret scan covers every published text file**: transcripts, source files, the packaged page and SVGs.
  - It matches known token formats (`sk-`, `ghp_`, `AKIA`, `xox*-`, private keys...) and generic `key|secret|token|password = <long value>` patterns.
- **A hit aborts before anything is written** (fail closed). The error prints file:line and a masked match.
  `--redact` replaces matches with `[REDACTED]`, and the owner must choose it for that import.
- Raw harness output that carries account details isn't published at all: Claude Code's stream-json stays in
  the run's `harness/`, and only the converted session is published (0007).
- **Image data is exempt.** The base64 data of image blocks in session JSON is set aside before path rewrites and the scan,
  then put back. It's binary: rewrites could corrupt it, and the scan found random `AKIA…` matches in thumbnails.
  Only data that is plain base64 is exempt. A secret visible *in* a screenshot isn't caught, but a scan of base64 text
  couldn't catch it either.
- `--dry-run` runs the whole pipeline, scan included, in a temp dir.
- Test fixtures are synthetic. No real sessions or personal paths are committed.

## Alternatives considered

- **Redact by default**: that silently changes transcripts and could hide the fact that an agent leaked a
  credential, which the owner should know about.
- **Warn and continue**: publishing is irreversible, so a warning is too weak.
- **An external scanner (gitleaks, trufflehog)**: better coverage, but it's a dependency (0002) and runs
  after the fact, unless it's wired in as a pre-import step.

## Consequences

- A false positive blocks an import until the owner looks at it, which is the intended cost.
- The patterns are a heuristic. A new token format needs a new pattern and a test.
- Rewritten paths mean a transcript isn't byte-identical to what the agent saw. The viewer and the metrics
  don't depend on those paths.
