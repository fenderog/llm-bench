# 0004. Untrusted model output is always sandboxed

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

Everything a model produces is untrusted:
- the HTML and JS of a game,
- SVG files,
- markdown answers,
- transcript text,
- file contents.

The site serves it from `fenderog.github.io`, an origin shared by all the owner's Pages sites. Script that
runs there could read storage of that origin, change the viewer, or trick visitors. The owner's local
`bench serve` also has a write API (0010) that such script must not reach.

## Decision

There is exactly one way to show each type of output:

| Output | How it's shown | Where |
|---|---|---|
| Godot games (HTML/JS/wasm) | `<iframe sandbox="allow-scripts allow-pointer-lock">`, **never `allow-same-origin`**, so the game gets an opaque origin | `sandboxedGame()` in `common.js`, the only place games are embedded |
| Web pages (kind `web`, one packaged `index.html`) | The same sandboxed iframe as games, via `sandboxedGame()`; verification boots them in that sandbox too (0013) | `sandboxedGame()` |
| Images, SVGs included | `<img>` only, which never runs an SVG's scripts. Never inlined, never in object/embed/iframe, never linked for viewing on the site's origin (downloads use the `download` attribute) | `mediaElement()` in `common.js` |
| Images inside a transcript (screenshots the agent read) | `<img>` with a `data:` URL, only for jpeg/png/gif/webp with plain base64 data, never SVG. Claude Code runs store a ≤320px JPEG thumbnail re-encoded by ffmpeg, not the original | `renderImage()` in `transcript.js` |
| Videos | `<video controls preload="none">`, never autoplay | `mediaElement()` |
| Text (transcripts, source, metrics) | `textContent` | everywhere |
| Markdown | `renderMarkdown()`: raw HTML is escaped, and `href`/`src` must be http(s) or relative. Without `marked` it falls back to `textContent` | `common.js` |

- Never use `innerHTML` with run data. The exception is `renderMarkdown()`, whose output is sanitized as
  described above.
- "Open full screen" runs a game outside the sandbox, so the link says "(unsandboxed)".
- Games boot only on click, never automatically. The exception is `play.html` (the compare cards' ↗ pop-out
  window), which boots at once because opening the window was the click. It shows output only through
  `sandboxedGame()` / `mediaGallery()`, so it is not a new unsandboxed entry point.
- Tests check that the fixture SVG's embedded script never runs and that games are embedded in a sandboxed iframe.

## Alternatives considered

- **`allow-same-origin` for easier game APIs** (IndexedDB, PWA hooks): the spike showed games boot and save
  fine without it, and the only cost is a harmless console warning.
- **Inline SVG**, which would allow styling and theming: that runs the model's script on our origin.
- **A sanitizer library (DOMPurify)**: this breaks 0002. Escaping raw HTML plus an allowlist for URLs is
  enough for markdown.
- **A separate origin for untrusted output**: stronger, but needs a second domain or Pages site. Revisit if
  anything ever needs `allow-same-origin`.

## Consequences

- Each sandboxed iframe has its own opaque origin, so the compare view downloads the engine once per
  column. That's why games are click-to-play.
- A new type of output needs its own row in this table before it ships.
