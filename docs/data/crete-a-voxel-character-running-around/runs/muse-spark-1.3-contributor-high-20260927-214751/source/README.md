# Voxel Runner Sandbox

A tiny 3D sandbox for Godot 4.7.2: a procedurally built voxel character runs,
jumps and collects coins in a small fenced arena with trees, rocks, crates,
grass, flowers and drifting clouds.

Everything is generated in code — no downloads, external assets or plugins.

## Run

- Open this folder in Godot 4.7.2 and press **F5** (or run `godot --path .`).
- Headless sanity check: `godot --headless --path . --editor --quit` (should print no errors).

## Controls

| Input | Action |
| --- | --- |
| WASD / Arrow keys | Run |
| SHIFT | Sprint |
| SPACE | Jump (with coyote time + jump buffering) |
| Mouse drag (or Q / E, touch drag) | Orbit camera |
| Mouse wheel | Zoom |
| R | Reset the sandbox |

## Web-export notes

- Renderer is `gl_compatibility` (`project.godot`: `rendering/renderer/rendering_method`).
- No threads, no GDExtension, no plugins — plain nodes, one MultiMesh for
  repeated voxels, and `CPUParticles3D` for dust, so it runs in the default
  (non-threaded) Godot web export.

## Files

- `main.tscn` — main scene (sun, sky, player, camera rig, HUD).
- `scripts/voxel_character.gd` — builds + animates the voxel runner.
- `scripts/player.gd` — third-person runner controller.
- `scripts/camera_rig.gd` — follow camera with collision-aware SpringArm.
- `scripts/world_builder.gd` — procedural sandbox (tiles, fence, trees, crates, coins…).
- `scripts/coin.gd` — spinning pickup coin.
- `scripts/hud.gd`, `scripts/main.gd` — HUD, coin counting, reset, pickup sound.
