# Voxel Runner

A small, self-contained Godot 4.7.2 project: a voxel-built character runs
around a walled voxel sandbox with trees, rocks, crates and flowers.

## Run it

**In the Godot editor:** open the project (`project.godot`) and press **F5**
(or the Play button).

**From the command line:**

```sh
godot --path . 
```

**As a web export:** the project is configured for the `gl_compatibility`
renderer with the rendering device thread model disabled, so it is suitable
for a WebGL2 web export. Export it with the standard Godot web export
presets afterwards (this repo intentionally does not ship export presets).

## Controls

| Input            | Action                          |
|------------------|---------------------------------|
| WASD / Arrows    | Run (relative to camera)        |
| Right-drag mouse | Orbit the camera (desktop)      |
| Mouse wheel      | Zoom the camera in/out          |
| ESC              | Quit (desktop)                  |

The character automatically faces its movement direction and plays a simple
procedural run cycle (arm/leg swing + body bob) while moving.

## Layout

- `main.tscn` — main scene (world, sun, environment, player, camera rig)
- `character.tscn` — the voxel character (built from BoxMesh parts)
- `scripts/world.gd` — builds the sandbox procedurally at startup
- `scripts/player.gd` — movement, facing and run animation
- `scripts/camera_rig.gd` — third-person follow/orbit camera
- `resources/environment.tres` — procedural sky, ambient light, tonemap

No external assets, plugins or downloads are required.
