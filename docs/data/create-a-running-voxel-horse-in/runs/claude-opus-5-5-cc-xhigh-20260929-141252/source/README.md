# Voxel Horse

A voxel horse galloping across an endless, procedurally generated blocky meadow.
Built for Godot 4.7 with the **GL Compatibility** renderer, so it can be exported to
the web without thread support. Everything is generated in code (meshes, terrain,
sky and sounds), so there are no external assets or plugins.

## Run

- **Editor:** open Godot 4.7, choose *Import*, select this folder's `project.godot`,
  then press **F5**.
- **Command line:** `godot --path .`

## Controls

| Key | Action |
| --- | --- |
| W / Up, S / Down | Change gait: stand, walk, trot, canter, gallop |
| A / D, Left / Right | Steer |
| Shift | Sprint (full gallop) |
| Space | Jump |
| C | Cycle camera: chase, side, front, orbit |
| H | Change coat: bay, chestnut, palomino, black, grey, pinto |
| M | Mute |
| F | Fullscreen |
| Tab | Show or hide help |
| Mouse drag / wheel | Orbit / zoom the camera |

Gamepads work too: left stick or D-pad to steer and change gait, A to jump,
RB to sprint, Y for camera and X for coat.

Optional start-up arguments, handy for screenshots:
`godot --path . -- --camera=1 --coat=5 --gait=2 --zoom=0.8`

## How it works

- `scripts/voxel_model.gd` holds a sparse voxel grid and bakes it into one
  vertex-coloured mesh, emitting only the faces that touch empty space.
- `scripts/horse_model.gd` designs the horse from voxel shapes, split into
  13 parts: body, neck, head, two tail segments, and upper and lower legs.
- `scripts/horse.gd` drives a procedural gait cycle. Speed blends between
  walk, trot, canter and gallop footfall patterns. Leg swing is derived from
  speed so planted hooves don't slide. The script also handles body bob,
  rocking, neck and tail motion, jumping, grazing when idle, dust and
  footfall sounds.
- `scripts/terrain.gd` streams 16 m chunks of terraced voxel terrain around
  the horse, with lakes, trees, rocks, flowers and grass baked into each
  chunk's mesh. Each chunk is one draw call.
- `scripts/sfx.gd` synthesises hoof clops and a wind loop into `AudioStreamWAV`s.
