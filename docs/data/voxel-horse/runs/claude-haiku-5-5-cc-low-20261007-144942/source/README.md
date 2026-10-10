# Voxel Horse

A small, self-contained Godot 4.7 game. A voxel-built horse gallops across a
green field, collecting carrots while you steer it around the trees.

Everything (the horse model, scenery, and animation) is generated in code.
There are no external assets or plugins.

## Running

1. Install Godot 4.7.2 (or a compatible 4.7 build).
2. Open the project: `godot --path .` or use **Import** in the Project Manager
   and select `project.godot`.
3. Press **F5** (Run Project). The main scene is `main.tscn`.

To check that the project loads without errors from the command line:

```
godot --headless --path . --editor --quit
```

## Controls

| Key                    | Action            |
| ---------------------- | ----------------- |
| W / Up                 | Gallop (accelerate) |
| S / Down               | Brake             |
| A / Left, D / Right    | Steer             |
| Space                  | Jump              |

Steering only works well while moving. Collect carrots to raise your score.

## Notes

- Renderer: `gl_compatibility`, so the project can be exported to the web.
- Thread support is not enabled.
