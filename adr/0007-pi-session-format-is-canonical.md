# 0007. pi's session format is canonical; harnesses convert into it

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

The first runs came from pi (via `fe-model-effort-fanout/1`), and the viewer, the metrics and the tests were built
on pi's session format. Then Claude Code was added as a second harness, and Codex and others may follow.
Each harness logs differently, and some report metrics that are wrong in misleading ways.

## Decision

- **The published transcript is always in pi's format**: `conversation.json` with `message` entries and `thinking`,
  `toolCall`, `text` and `toolResult` blocks.
- **Each harness implements `Harness` in `harness.py`, including a converter into pi's format.**
  - `convert_claude_stream` is the model to follow. Tool names and argument shapes map onto pi's
    `bash`/`write`/`edit`/`read`.
  - Unknown tools keep their names.
  - The viewer has no per-harness code.
- **Metrics have one definition**, whatever the harness:
  - `tokens.total = input + output`, not pi's `totalTokens`, which includes cache reads.
  - `costUsd` is the sum of per-message cost. For Claude Code, it's `result.total_cost_usd`, an estimate at API prices.
  - Claude Code's tokens come from the final `result` event, because its per-message usage is a snapshot taken
    before the output is written.
- **Labels must be honest.** Every requested model and effort level is checked against the harness before a batch
  starts, because pi silently clamps unsupported levels.
  - `thinkingLevel` records what actually ran.
- **Runs are reproducible**: no user extensions, skills, CLAUDE.md, memory, MCP servers or hooks, and only the core
  file and shell tools, with no sub-agents or web access.
- Each run records its harness (name and version). A model run under two harnesses gets distinct ids.

## Alternatives considered

- **A neutral format designed for this project**: cleaner in theory, but it means migrating every published run
  and rewriting the transcript viewer, with no gain today.
- **Publish each harness's native log with a viewer per harness**: the viewer code grows with every harness, and
  raw logs carry account details (0005).
- **Trust each harness's own totals**: they aren't comparable (cache reads, snapshot usage).

## Consequences

- Adding a harness is: a `Harness` class, a converter, `HARNESSES`, and a fake binary in `tests/fixtures/fake_pi/`.
- Anything pi's format can't express is lost in conversion. For example, Claude Code's thinking text is empty in
  print mode.
- Claude Code has no model-listing command, so `ClaudeCode.MODELS` has to be updated by hand.
