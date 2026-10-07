# Voxel Horse

A running voxel horse built in Godot 4.7. The horse, field, trees, rocks and
fence are all generated from code, so there are no external assets or plugins.

## Run

Requires Godot 4.7 (the project uses the Compatibility renderer).

- **Editor:** open Godot, choose *Import*, select `project.godot`, then press **F5**.
- **Terminal:** `godot --path .`

## Controls

| Key | Action |
| --- | --- |
| W / Up | Run forward |
| S / Down | Slow down and back up |
| A / D or Left / Right | Steer |
| Shift (with W / Up) | Gallop |
| R | Reset the horse to the start |

Turning is slower at low speed, and the horse turns back on its own at the
edge of the field. Trees and rocks block the horse.

## Web export

The project has no thread settings and uses the Compatibility renderer, so it
can be exported to the web without enabling thread support.
