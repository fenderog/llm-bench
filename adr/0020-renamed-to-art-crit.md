# 0020. Renamed from llm-bench to art-crit

- Status: Accepted
- Date: 2026-10-10

## Context

The site and the tool were called llm-bench, and the CLI was `bench`. But it isn't a benchmark in the usual sense:
there's no score and no leaderboard. The prompts ask for visual and spatial work (games, images, 3D scenes, web
pages), and the point is to put the results side by side and judge them by eye. That's what an art-school crit is.

## Decision

Everything is called art-crit: the GitHub repo (`fenderog/art-crit`, so the site lives at
`fenderog.github.io/art-crit/`), the CLI (`art-crit`), the package (`src/art_crit/`), the config file
(`art-crit.toml`), the default batch directory (`~/dev/art-crit-runs`), the env vars (`ART_CRIT_*`) and the
viewer's localStorage keys (`art-crit.*`). Published run data is left as it was: transcripts that mention the old
paths are a record of what happened.

## Alternatives considered

- **Keep the llm-bench repo and URL, rename only the text**: no broken links, but the address wouldn't match the
  name.
- **A shorter command (`crit`)**: easier to type, but the user preferred the command to match the name.
- **Rewrite old paths in published transcripts**: changes the record of what the agents saw, for no real gain.

## Consequences

- Old `fenderog.github.io/llm-bench/` links stop working: GitHub redirects the repo and git remotes after a rename,
  but not Pages sites.
- The editable uv tool has to be reinstalled under the new name, and the remembered grid/table view and run
  selections in the browser reset once.
- Older records were updated to the new command and file names (a renamed file is a small factual update).
  DESIGN.md stays historical, with a note pointing here.
