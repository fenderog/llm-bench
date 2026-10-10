# Wildstride — Voxel Trail

A self-contained Godot 4.7.2 endless horse runner. Procedural voxel horse with animated gallop, prairie scenery, fences, and spinning carrot collectibles. Speed gradually increases; three fence collisions end the run.

## Run
Open `project.godot` in Godot 4.7.2 and press F6/F5, or run `godot --path .`.

- **A/D or Left/Right:** switch between three lanes
- **Space:** jump over fences
- **P/Escape:** pause
- **R / Restart button:** start a new run

Collect carrots and travel as far as possible. All art is generated in code; no external dependencies. Uses GL Compatibility, with no thread support enabled, suitable for web export.

Validated with `godot --headless --path . --editor --quit` and a headless runtime smoke test.
