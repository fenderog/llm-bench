# Voxel Horse

A running horse built entirely from procedurally generated voxels, galloping through an
endless voxel meadow. Made for Godot 4.7.2 with the `gl_compatibility` renderer; no
external assets, plugins or threads, so it works as a web export.

## Run

- Editor: open this folder in Godot 4.7.2 and press **F5** (the main scene is `main.tscn`).
- Command line: `godot --path .`

## Controls

| Input | Action |
| --- | --- |
| `W` / `S` (or Up / Down) | Speed up / slow down (stand, walk, trot, canter, gallop) |
| `A` / `D` (or Left / Right) | Steer |
| `Space` | Jump |
| `1` `2` `3` `4` | Jump straight to walk / trot / canter / gallop |
| `C` | Cycle coat (chestnut, bay, palomino, black, grey, pinto) |
| Mouse drag, wheel | Orbit and zoom the camera |
| `R` / `H` | Reset the camera / hide the help text |

## How it works

- `scripts/voxel_builder.gd` turns a sparse voxel grid into a mesh with hidden faces removed
  and baked ambient occlusion.
- `scripts/voxel_horse.gd` builds the horse from articulated voxel parts and animates it. The
  gait blends smoothly with speed, and the body height is derived from the feet so hooves
  stay planted.
- `scripts/voxel_world.gd` builds the sky, fog, trees, rocks, flowers, clouds and mountains.
  Props are MultiMeshes that wrap around the horse, so the meadow never ends.
- `shaders/ground.gdshader` draws the ground as one quad of per-voxel coloured cells.
- `scripts/main.gd` handles input, steering, jumping, the chase camera and the HUD.

## Web export

Use the included `Web` export preset (thread support is off) or export with
*Variant > Thread Support* disabled.
