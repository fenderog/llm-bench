# 0013. Web pages are packaged into one file with esbuild

- Status: Accepted
- Amendment: Raw fullscreen exception superseded by [0015](0015-viewer-csp-and-local-markdown.md).
- Date: 2026-09-29

## Context

We wanted a kind for interactive pages written in HTML/JS, typically three.js. Models build these as a folder:
`index.html`, ES modules, and npm packages, or CDN imports if nobody stops them. A published run must keep working
long after it's made, in the site's sandboxed iframe (0004), where each page has an opaque origin: storage APIs
throw, and loading modules would depend on CORS headers. CDN imports can disappear, and they make a run depend on
a third party.

## Decision

- The agent writes a normal page (`index.html` + `<script type="module">` + `npm install`), and **bench packages
  it** into one self-contained `index.html` afterwards: esbuild bundles every local module script with everything
  it imports, stylesheets are inlined, and imported assets become data: URLs (`src/bench/kinds/web.py`).
- **Verification decides whether the page is self-contained**: it boots the packaged file offline, in an iframe
  sandboxed exactly like the site's, and fails on any network request or page error. The brief states the rules
  (import everything, no CDNs, no storage), but the check is what enforces them.
- The published run is that one file, shown through `sandboxedGame()` like a game. `node_modules/` is never published.
- esbuild is an external tool the pipeline needs, like `godot` and `ffmpeg`. The CLI stays stdlib-only (0002).

## Alternatives considered

- **The model writes the single file itself** (e.g. three.js inlined through a data: URL import map): no packaging
  step, but packaging then becomes part of what's being scored, and runs fail for reasons unrelated to the task.
- **Publish the folder as-is**: works on Pages, but module loading inside an opaque-origin iframe depends on CORS
  headers, and CDN imports would still be dependencies.
- **Vite + vite-plugin-singlefile**: one step from folder to single file, but it needs a full Node toolchain and
  a per-run `npm install` of the bundler. esbuild is one binary.
- **monolith / SingleFile**: page inliners that don't follow ES module imports.
- **Zip + a loader page / service worker**: service workers can't register in the sandbox, and it's fragile.

## Consequences

- Each run carries its own copy of its libraries (three.js adds ~500 KB). That's fine at this scale; if it grows,
  dedupe like the Godot engine (0008).
- Assets loaded by URL string (`TextureLoader.load("wood.png")`) aren't bundled and fail the offline check. The
  brief tells models to `import` assets or generate them.
- Packaging is in-house HTML handling with regexes: module scripts, classic scripts (kept verbatim as data: URLs,
  since bundling would break their globals) and stylesheets. Anything else remote or local is left for verification
  to catch.
- "Open full screen (unsandboxed)" runs the page on the site's origin, as it already does for Godot games (0004).
