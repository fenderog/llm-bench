# Voxel Runner Sandbox

A tiny voxel character running around in a small sandbox, built as a complete,
self-contained **Godot 4.7.2** project. No downloads, external assets, or plugins:
the character, trees, fences, crates, pond, clouds, shard pickups, UI, and even
the sound effects are all generated procedurally in code.

## Run it

1. Open this folder in **Godot 4.7.2** (`godot --path .` or Project Manager →
   Import).
2. Press **F5** (or the ▶ button). `scenes/main.tscn` is already set as the
   main scene.
3. Headless smoke test used during development:
   `godot --headless --path . --editor --quit`
   plus a short runtime check: `godot --headless --path . --quit-after 180`

## Controls

| Input | Action |
| --- | --- |
| WASD / arrows | Run (camera-relative), SHIFT = sprint |
| Mouse drag, or click to capture | Orbit camera, wheel = zoom (Q/E also rotate) |
| Space | Jump (coyote time + jump buffer) |
| R | Respawn |
| H | Toggle help panel |
| Gamepad | Left stick = move, A = jump, X = sprint |
| Touch | Left stick = move, RUN / JUMP buttons, drag right side = camera |

Goal: collect all **12 sky shards**. Some are hidden on the platform, the
steps, and the crates. Collecting them all triggers a little celebration and
respawns fresh shards.

## Web-export notes

- Renderer is `gl_compatibility` (including the `.web` override).
- Thread support is off (`threading/worker_pool/use_threads=false`) and the
  game code uses no `Thread` / `WorkerThreadPool` / GPU particles, so it runs
  in a single-threaded web export.
- UI stretch is `canvas_items` / `expand` so it scales to the browser window.

## Files

- `project.godot` — main scene, GL Compatibility, threads off.
- `scenes/main.tscn` — world shell: sun, sky, ground slab, player rig mount,
  follow camera, HUD layer.
- `scripts/player.gd` — third-person controller + procedural voxel character
  (run-cycle limb swing, lean, squash & stretch, dust puffs, blip SFX).
- `scripts/main.gd` — builds the sandbox (island, fence, trees, rocks, crates,
  platform, pond, flowers, clouds, shards), runtime input map, game state.
- `scripts/pickup.gd` — spinning sky-shard pickup with magnet + respawn.
- `scripts/hud.gd` — HUD, toasts, help, touch controls.
- `scripts/sfx.gd` — procedural 8-bit WAV sound effects.
- `icon.svg` — little voxel-face project icon.
