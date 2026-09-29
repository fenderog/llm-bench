# 0012. Asset cache-busting

- Status: Proposed
- Date: 2026-09-28

## Context

- **The problem**: GitHub Pages serves everything with a 10-minute cache. After a deploy, a browser can pair new
  HTML with old `assets/*.js` (or the reverse). The old code then hits elements that no longer exist and throws
  null errors until a hard refresh.
- **Data is already handled**: data JSON is fetched with `cache: "no-cache"` (`getJSON()`).
- **Scripts and styles aren't**: they're loaded by plain `<script type="module">`/`<link>` tags and ES module
  imports between files, which can't carry that option.
- A fix was drafted in a git stash, but the stash was lost when the repo was moved on 2026-09-28.

## Options

1. **A version query string on every asset URL** (`app.js?v=<sha>`), stamped by `bench publish`.
   - Simple.
   - `bench publish` would then rewrite HTML/JS. So far it only commits, and the CLI never touches viewer
     files (0003).
   - Every relative `import` between modules needs the same version string.
2. **Content-hashed filenames** (`common.3f2a.js`).
   - The strongest option, but it takes a build step or a rename-and-rewrite pass, which 0002 rules out.
3. **A runtime version check**: fetch a small `version.json` with `no-cache`, and reload once when it doesn't
   match the version the page loaded with.
   - No rewriting.
   - It costs one extra request, and the stale page appears briefly before the reload.
4. **Do nothing**: tell people to hard-refresh after a deploy.
   - Only the owner hits this today, usually right after publishing.

## Decision

Not decided yet. Choose one of the options above and set this ADR to Accepted.
Whatever is chosen must not add a build step (0002).

## Consequences

To be filled in when the decision is made.
