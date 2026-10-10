# Voxel Horse

A voxel horse gallops round a circular track. Everything is built in code at
runtime, so the project has no external assets or plugins.

## Requirements

- Godot 4.7.2 (standard build, not .NET)

## Run

From this directory:

```sh
godot --path .
```

Or open `project.godot` in the Godot editor and press F5.

To check that the project loads without errors:

```sh
godot --headless --path . --editor --quit
```

## Controls

| Key              | Action             |
| ---------------- | ------------------ |
| W / Up           | Gallop faster      |
| S / Down         | Slow down          |
| A / Left         | Steer outwards     |
| D / Right        | Steer inwards      |
| Space            | Jump               |
| R                | Restart            |

Jump over the red-and-white hurdles while you are in their lane. Hitting one
knocks you down to a slow canter.

## Layout

- `project.godot` - project settings, main scene and the gl_compatibility renderer
- `main.tscn` / `main.gd` - the game: track, hurdles, scenery, camera, HUD and controls
- `voxel_horse.gd` - the horse model and its procedural gallop animation
- `voxel_builder.gd` - helper that turns boxes into vertex-coloured meshes
