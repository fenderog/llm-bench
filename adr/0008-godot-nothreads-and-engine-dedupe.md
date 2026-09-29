# 0008. Godot: no-threads web export, engine deduped by hash

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

A Godot 4 web export is about 38.3 MB, and 38 MB of that is the engine (`index.wasm` + JS), which is
byte-identical across exports from the same Godot version and template. The game itself (`index.pck`) is a few KB
to a few MB. Pages has a 1 GB site limit. It also can't send the COOP/COEP headers that threaded
(`SharedArrayBuffer`) builds need (0001). Both were checked in a spike before building (`spike/build.py`).

## Decision

- **Export single-threaded only** (`web_nothreads_release`). `bench run` writes its own `export_presets.cfg`.
  Import refuses threaded exports unless `--allow-threads` is given, which marks the run `threads: true`.
- **Store each engine once**:
  - `engines/<sha12>/godot.{wasm,js,audio.worklet.js,audio.position.worklet.js}`, where sha12 is taken from
    the four engine files.
  - The run's `index.html` is rewritten to load the engine from there, with `mainPack = "index.pck"` set
    explicitly. Without that, the pck path would resolve into the engine folder.
- **Delete unreferenced engines** on `bench rebuild`.
- **Verify builds** headlessly: the output files must exist (Godot can exit 0 after failing), and a Playwright boot
  check waits for `#status` to be removed and for two frames that differ.

## Alternatives considered

- **Copy the engine into every run**: about 25 runs would fill the 1 GB limit.
- **Threaded builds with a service-worker COOP/COEP shim**: fragile, and works only full screen, outside the
  sandboxed iframe.
- **Load the engine from a CDN**: an outside dependency with version drift. Pages serves it fine.

## Consequences

- A run costs about 100 KB instead of about 38 MB. Each new Godot version or template adds 38 MB once.
- Games that need threads can't be published.
- A cold play costs about 38 MB of bandwidth, and the compare view pays that once per iframe (0004).
- Godot's HTML template is load-bearing. A Godot upgrade needs the rewrite checked against the new `index.html`
  (tests use a real template).
