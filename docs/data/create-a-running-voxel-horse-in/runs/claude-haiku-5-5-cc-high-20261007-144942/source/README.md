# Voxel Gallop

An endless gallop with a blocky voxel horse, built in Godot 4.7.2. The horse runs
on its own and speeds up over time. Switch lanes, jump the hurdles, and dodge the
rock walls. Every model is generated in code, so there are no
external assets.

## Run it

1. Install [Godot 4.7.2](https://godotengine.org/download).
2. From this folder, run `godot --path .`, or open `project.godot` in the Godot
   editor and press **F5**.

To check that the project loads without errors:

```sh
godot --headless --path . --editor --quit
```

## Controls

| Action        | Keys                       |
| ------------- | -------------------------- |
| Change lane   | `A` / `D` or Left / Right  |
| Jump          | `Space`, `W` or Up         |
| Restart       | `R` (or `Space` after a fall) |

## Project layout

- `scenes/main.tscn`: the main scene, which holds only the game script.
- `scripts/game.gd`: track, lanes, jumping, obstacles, camera, HUD.
- `scripts/horse.gd`: the voxel horse and its procedural gallop animation.
- `scripts/props.gd`: hurdles, rock walls, trees, bushes and boulders.
- `scripts/voxel_builder.gd`: turns voxel data into an optimized mesh.

## Web export

The project uses the `gl_compatibility` renderer and has no threading. The
included `export_presets.cfg` has a **Web** preset with thread support turned off,
so the export runs without cross-origin isolation headers.
