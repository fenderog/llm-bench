# Voxel Runabout

A cute voxel character running around a small fenced sandbox in **Godot 4.7.2**.
Sprint, jump on crates, and collect all 8 floating gems as fast as you can.

Everything is procedural — no downloads, assets, or plugins. Just open and run.

## Run

- Open this folder in Godot 4.7.2 (`Main` scene is set as the main scene) and press **F5**,
  or from a terminal:
  ```
  godot --path . 
  ```
- Headless sanity check:
  ```
  godot --headless --path . --editor --quit
  ```

## Controls

| Input | Action |
|---|---|
| WASD / Arrow keys | Run around (camera-relative) |
| Space | Jump |
| Shift | Sprint |
| Mouse (click first to capture) | Orbit camera, wheel = zoom |
| Q / E | Keyboard camera orbit |
| R | Reset run |
| Esc | Release mouse |

## Notes

- Renderer: `gl_compatibility`, worker-pool threads off — ready for Web export.
- Crates are solid (jump on them!); trees, fence, and walls keep you in the sandbox.
- Dust puffs kick up when you sprint; the gem timer tracks your best run.
