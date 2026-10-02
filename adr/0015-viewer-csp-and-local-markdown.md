# 0015. Viewer uses local Markdown tokens and a same-origin CSP

- Status: Accepted
- Date: 2026-10-01
- Supersedes: the CDN/fallback clauses in 0002 and the Markdown/fullscreen exceptions in 0004 and 0013.

## Context

The shared viewer imported Marked from a CDN on every page. Markdown used sanitized innerHTML,
and run/table fullscreen links bypassed the existing sandboxed play viewer (issues #21 and #23).

## Decision

Vendor Marked 15.0.12 with its MIT license. Load it only through the transcript module and render
lexer tokens as DOM nodes. Raw HTML stays text, links allow HTTP(S), and remote Markdown images
stay alt text. Never assign innerHTML with run data.

All five viewer documents enforce a same-origin meta CSP, with data images permitted and objects
and base URLs forbidden. Dynamic styles use CSSOM property setters. Model documents have their own
policy and remain inside opaque-origin sandboxed iframes. All fullscreen links open play.html.

## Alternatives considered

- **DOMPurify:** another dependency; token rendering removes the HTML insertion altogether.
- **CDN plus timeout:** adds outside requests and silently loses Markdown when the CDN is slow.
- **Raw fullscreen entry:** permits model code on the viewer origin; the sandbox supports the needed APIs.

## Consequences

The viewer works without external requests. Parser upgrades require replacing the pinned module
and license and running the Markdown/CSP regressions. Supported Markdown tokens are maintained in markdown.js.
