# Voxel Runner

A small, self-contained Godot 4.7 project featuring a blocky (voxel) character
running around a sandbox arena. Everything — the character, the ground, the
scattered blocks and the environment — is generated procedurally in GDScript,
so there are no external assets, downloads or plugins.

## Requirements

- [Godot 4.7.x](https://godotengine.org/download) (standard build)
- Uses the **GL Compatibility** renderer and does **not** require thread support,
  so it is safe to target a web export.

## Run it

From the project directory:

```bash
# Open the project in the editor
godot --path .

# Or run the game directly
godot --path . 
```

You can also open `project.godot` from the Godot project manager and press
**F5**.

## Controls

| Action | Keys |
| ------ | ---- |
| Move   | `W` `A` `S` `D` or Arrow Keys |
| Jump   | `Space` |

The camera follows the character automatically.

## Project layout

| File           | Purpose |
| -------------- | ------- |
| `project.godot`| Project configuration (main scene, renderer, window). |
| `main.tscn`    | Main scene; just a `Node3D` with `main.gd` attached. |
| `main.gd`      | Builds the environment, ground, props, camera and HUD, and spawns the player. |
| `player.gd`    | Voxel character model, movement physics and the procedural run/idle animation. |
| `icon.svg`     | Simple project icon drawn inline. |

## Notes on web export

The project intentionally leaves multi-threading disabled. Export with the
standard **Web** preset; no extra thread-support flags are needed.
