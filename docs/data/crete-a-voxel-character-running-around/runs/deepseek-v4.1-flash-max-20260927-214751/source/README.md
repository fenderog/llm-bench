# Voxel Runner

A small, fully procedural voxel sandbox made with **Godot 4.7.2**. A blocky
voxel character runs, sprints and jumps around a tiny island, collecting
spinning coins.

Everything is generated at runtime from code — there are no downloaded
assets, external files or plugins. The project uses the **GL Compatibility**
renderer and does not use threads, so it can be exported to the web.

## Run it

From this directory:

```bash
godot --path .
```

Or open the folder in the Godot project manager and press **F5**.
The main scene (`main.tscn`) is already configured in `project.godot`.

## Controls

| Input | Action |
| --- | --- |
| `W` `A` `S` `D` | Run (camera relative) |
| `Shift` | Sprint |
| `Space` | Jump |
| Mouse (left-click to grab, `Esc` to release) | Look around |
| `Q` / `E` | Rotate the camera with the keyboard |

Collect all 12 coins and they respawn in new spots.

## Web export

A Web export preset is included (thread support **disabled**). To export:

```bash
godot --headless --path . --export-release "Web" build/index.html
```

## Project layout

- `main.tscn` — minimal main scene (a single `Node3D` with the game script).
- `scripts/game.gd` — builds the world: terrain, props, clouds, camera, HUD, coins.
- `scripts/player.gd` — the voxel character: movement and run-cycle animation.
- `scripts/coin.gd` — spinning collectible coin.
- `icon.svg` — project icon drawn as a tiny voxel character.

## Features

- Procedurally generated blocky terrain (noise heightmap, dirt/stone cliffs,
  grass, rocky rim, a small pond with translucent water and sandy floor).
- Solid one-block ledges that the character can climb, plus real jumping.
- Trees, rocks, flowers, drifting clouds, sun shadows and distance fog.
- Third-person spring-arm camera with mouse/keyboard look.
- Coin hunt with particle bursts and a simple HUD.
