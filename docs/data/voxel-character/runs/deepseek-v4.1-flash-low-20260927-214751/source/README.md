# Voxel Sandbox Runner

A small, self-contained Godot 4.7 project featuring a blocky voxel character
running around a fenced sandbox. All geometry, materials and the environment are
generated procedurally at runtime — there are no external assets, downloads or
plugins.

## Requirements

- [Godot 4.7](https://godotengine.org/) (stable)
- Uses the **GL Compatibility** renderer with **threading disabled**, so it is
  ready for a web (HTML5) export.

## Run instructions

From this directory:

```bash
godot --path .
```

Or open the project in the Godot editor (`godot --editor --path .`) and press
**F5**.

### Controls

| Action | Keys |
| ------ | ---- |
| Run    | `W` `A` `S` `D` or Arrow keys |
| Jump   | `Space` |

The camera follows the character from a fixed third-person angle; movement is
camera-relative.

## What's inside

- `project.godot` — project settings (GL Compatibility renderer, no threads,
  main scene, window/stretch setup).
- `main.tscn` — tiny scene whose root node runs `scripts/main.gd`.
- `scripts/main.gd` — builds the sandbox: voxel ground, walls, pyramid, ramp,
  platform, trees, crates, flowers, lighting, sky, follow camera and HUD.
- `scripts/voxel_character.gd` — the playable character: built from boxes,
  with gravity, jumping and a procedural run/idle/jump animation.

## Web export note

The project intentionally leaves thread support off. When exporting to the web,
do **not** enable the threaded export option; the default single-threaded
settings work as-is.
