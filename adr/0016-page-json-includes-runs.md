# 0016. One page.json includes its ranked runs

- Status: Accepted
- Date: 2026-10-01
- Supersedes: the results.json aggregate clauses in 0003 and 0010.

## Context

Page views fetched two or three overlapping JSON files and repeated their loading/error handling (#24).

## Decision

Rebuild writes metadata plus ranked runs into page.json and deletes legacy results.json. Per-run
run.json stays the source of truth and never stores rank. Rankings remain in ranking.json and are
applied to page.json.runs. bench list reads that array. All four page views use the shared loadPage()
loader; run/play select their run from the array.

## Alternatives considered

- **Separate results.json:** duplicates fetching and loader logic without useful separation.
- **Fetching run.json on the run page:** the switcher already needs all runs, including their ranks.

## Consequences

The contract and viewer migrate together; old deployments must rebuild before using the new viewer.
