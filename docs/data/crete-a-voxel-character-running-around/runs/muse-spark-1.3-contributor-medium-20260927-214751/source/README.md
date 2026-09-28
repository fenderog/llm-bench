# Voxel Runner Sandbox

A tiny voxel character running around in a small sandbox, built with Godot 4.7.2.

## Run

1. Open this folder in Godot 4.7.2 (or run `godot --path .`).
2. Press **F5** (the main scene is already set to `scenes/main.tscn`).
3. For web: export with the **GL Compatibility** renderer preset and **thread support off**.

## Controls

- **WASD / Arrow keys** — run around (camera-relative)
- **Mouse** — click the game to capture, move to orbit, wheel to zoom (`Q`/`E` also orbit)
- **Space / Enter** — jump
- **Shift** — sprint (with dust puffs!)
- **R** — reset to spawn
- **Esc** — release the mouse

## What's in the sandbox

- Procedurally animated voxel runner (swinging limbs, jump pose, scarf, idle breathing)
- Fenced grass arena with voxel tiles, crates, climbable platform + flag, trees, lamps, flowers
- 12 collectible spinning coins with HUD counter
- 2 bounce pads that launch you in the air
- Drifting voxel clouds, third-person follow camera with collision (SpringArm3D)

## Project details

- Renderer: `gl_compatibility` (set for base, mobile, and web)
- No threads, no plugins, no external assets — everything is generated in code from `BoxMesh` + `StandardMaterial3D`
- Main scene: `scenes/main.tscn`
- Scripts: `scripts/main.gd` (game/camera), `scripts/player.gd` (controller + voxel rig), `scripts/sandbox.gd` (world builder), `scripts/coin.gd`, `scripts/bounce_pad.gd`, `scripts/hud.gd`
