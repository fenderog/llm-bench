# Voxel Runner

A small Godot 4.7 sandbox: a blocky voxel character runs around a 24×24
voxel world with platforms, trees, crates and flowers. The character
auto-patrols a loop, climbing the platforms as it goes, and has a
full run-cycle animation (swinging arms/legs, body bob, head tilt).

- Renderer: **gl_compatibility** (web export ready), no thread support
- 100% procedural: no external assets, textures, plugins or downloads

## Controls

- **WASD / Arrow keys** — steer the character yourself (camera-relative)
- Release the keys and the character resumes its automatic patrol

## Run it

Open the project in Godot 4.7.x (the main scene is set automatically),
then press **F5** to run.

Command line:

```
godot --path .
```

Headless smoke test:

```
godot --headless --path . --editor --quit
```

## Web export

Because the project uses the GL Compatibility renderer and no threaded
features, the standard **Web** export preset works as-is.

## Files

- `project.godot` — project settings (main scene, gl_compatibility)
- `scenes/main.tscn` — main scene: sun, camera, environment
- `scripts/main.gd` — builds the world and drives the character
