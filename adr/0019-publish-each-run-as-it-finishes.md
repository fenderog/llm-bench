# 0019. `art-crit run --publish` publishes each run as it finishes

- Status: Accepted
- Date: 2026-10-10
- Amends: [0011](0011-publish-pushes-to-main.md) (what `art-crit run --publish` does, not where it pushes).

## Context

`art-crit run --publish` imported the whole batch and pushed once, after every agent had finished. A batch of 20 runs,
8 at a time, takes one to two hours: nothing was visible on the live site until the end, and a problem in the batch's
import (a secret hit in any one run) meant nothing at all was published. Following a long batch meant publishing by
hand from the batch directory while it ran (`art-crit import <batch>/<run id>` plus `art-crit publish`).

## Decision

- With `-P/--publish`, a run is imported and pushed on its own, right after its output step (step 6 of `art-crit run`) —
  the same import the batch would do, just per run, with the message `art-crit run: <page> (<run id>)`.
- One run at a time (`Publisher` in runner.py, one lock): an import rewrites `page.json`/`pages.json` and may write
  `docs/engines/`, git needs the index to itself, and a push must never see a half-written run directory.
- The batch's own import at the end is skipped when every run was published. A run that couldn't be published — a
  secret hit, a failed push — is reported as a `note:` instead of killing the running batch, and is left to that final
  import, which retries it and exits non-zero.

## Alternatives considered

- **Publish the whole batch once at the end** (what it did): a long batch stays invisible for hours, and one bad run
  blocks every other run's publication.
- **A background publisher thread collecting finished runs into fewer commits**: fewer commits and pushes, but a second
  concurrency model, and a run's finish time stops mapping to a commit. Not worth it at 8 parallel agents; easy to add
  behind `Publisher` later.
- **Import as runs finish, push once at the end**: keeps the local preview current but not the deployed site, which is
  the point.
- **A `art-crit publish --watch` reading the batch directory**: a second process to babysit, and it has to work out which
  runs are finished on its own.

## Consequences

- The live site fills up run by run; a batch can be followed at its page URL, and Ctrl-C leaves what is already
  published live.
- Git history has one commit per run instead of one per batch, and each commit triggers its own Pages deploy (about a
  minute; Pages coalesces when runs finish together).
- A secret hit in one run no longer blocks the others (that run simply isn't published), and the batch still exits
  non-zero so the hit can't go unnoticed.
- `art-crit run --resume <batch> --publish` re-imports and re-pushes runs that were already published: a "nothing to
  commit" plus a no-op push, which is idempotent and cheap.
