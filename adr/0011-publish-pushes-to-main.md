# 0011. `bench publish` pushes to `main`, no PR flow

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

Publishing is `git add docs && git commit && git push`, and Pages deploys `main:/docs` in about a minute.
The owner is the only publisher. A pull-request flow came up for future contributors without write access, and
as a review step for the owner.

## Decision

- `bench publish [-m MSG]` commits `docs/` and pushes straight to `main`, using the owner's existing git auth.
- `bench run --publish` does the same after importing.
- There is no pull-request mode and no CI check for now.

## Alternatives considered

- **`bench publish --pr`**: opens a PR, and a GitHub Action checks that the PR only touches `docs/data/` and
  `docs/engines/`. This would let other people contribute runs, and give the owner a review step.
  Discussed and deliberately deferred: there's one publisher, and the safety checks (0005) already run
  before anything is written.
- **Deploy through Actions**: see 0001.

## Consequences

- Publishing takes one step and is instant. The review is `bench serve` before publishing.
- A bad import goes live straight away. The fix is `bench rm`/re-import plus another publish, and history
  keeps the bad version (which matters for secrets, hence 0005).
- Outside contributions would mean superseding this ADR with the PR flow above.
