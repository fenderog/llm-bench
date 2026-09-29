# Voxel Horse

A small Godot 4.7 project: a chestnut horse made of voxel blocks gallops across an endless
blocky meadow. Everything (horse, trees, clouds, hurdles, ground shader) is generated in code,
so there are no external assets or plugins.

## Run

1. Open this folder in Godot 4.7.x (Project Manager -> Import -> `project.godot`) and press **F5**,
   or run `godot --path .` from this directory.
2. It uses the `gl_compatibility` renderer and no threads, so it exports cleanly to the Web.

## Controls

| Input | Action |
| --- | --- |
| `W` / `Up`, `S` / `Down` | Speed up / slow down (the horse changes gait: walk, trot, gallop) |
| `Space`, `Enter` or click | Jump |
| `A` / `D`, arrows left / right, or drag with the mouse | Orbit the camera |
| Mouse wheel | Zoom |

Red-and-white hurdles appear on the trail. Jump over them; if you hit one you knock it over,
stumble and lose speed. The HUD shows gait, speed, distance and your hurdle count.

## Files

- `main.gd` / `main.tscn` - main scene: environment, camera, HUD, input
- `horse.gd` - builds the voxel horse and animates the gaits and jump
- `world.gd` - scrolling ground, scenery, clouds and hurdles
- `voxel_builder.gd` - turns a voxel dictionary into a face-culled coloured mesh
- `ground.gdshader` - scrolling tiled ground with a dirt trail
