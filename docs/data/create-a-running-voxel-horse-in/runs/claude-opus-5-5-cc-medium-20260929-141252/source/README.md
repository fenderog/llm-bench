# Voxel Horse Run

A voxel horse gallops across an endless, procedurally generated meadow. The horse, trees, rocks, flowers, ground and lighting are all built in code. The project has no external assets.

## Run

- **Editor:** open Godot 4.7, import this folder (`project.godot`), then press **F5**.
- **Command line:** `godot --path .`

It uses the `gl_compatibility` renderer, so it can be exported to Web.

## Controls

| Key | Action |
|-----|--------|
| W / ↑, S / ↓ | Speed up / slow down through the gaits (stand, walk, trot, canter, gallop) |
| 1–5 | Choose a gait directly |
| A / ←, D / → | Steer |
| Shift | Sprint |
| Space | Jump |
| C / V | Switch camera (chase, side, front, orbit) |

## Files

- `main.gd`: horse rig and gait animation, movement, chunk streaming, camera and HUD
- `voxel.gd`: small voxel-to-mesh builder that culls hidden faces
- `main.tscn`: main scene
