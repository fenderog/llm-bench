# Voxel Horse Run

A voxel horse galloping through an endless meadow, built in Godot 4.7 (Compatibility renderer, web-friendly).
Everything (the horse, trees, rocks, logs, carrots, ground) is generated from code. There are no external assets.

## Run

- **Editor:** open Godot 4.7, choose *Import*, pick this folder's `project.godot`, then press **F5**.
- **Command line:** `godot --path .` from this directory.

## Controls

| Key | Action |
| --- | --- |
| W / Up, S / Down | Change gait: stand, walk, trot, canter, gallop |
| A / Left, D / Right | Steer |
| Space | Jump (logs and rocks). When standing, the horse rears up |
| C | Cycle camera: chase, side, front, orbit |
| Mouse wheel | Zoom |

A gamepad also works: D-pad or left stick to steer, shoulder buttons to change gait, A to jump and Y to switch camera.

Collect carrots and jump the fallen logs. If you run into a tree or a log, the horse stumbles.
If you leave the horse standing for a few seconds, it lowers its head and grazes.

## How it works

- `scripts/voxel.gd` builds meshes from colored voxel grids and skips hidden faces.
- `scripts/horse.gd` builds the horse out of voxel parts: body, neck, head, a two-part tail and two-segment legs.
  Each gait has its own footfall timing, and two-bone IK keeps the hooves planted on the ground.
  The body bobs and pitches, the head nods and the tail streams out behind.
- `scripts/world.gd` streams 32 m chunks of meadow around the horse. Each chunk has paths, trees, rocks, logs,
  flowers and carrots, and uses MultiMesh instancing to keep draw calls low.
- `scripts/main.gd` sets up the sky, sun, fog, camera, input map and HUD.
