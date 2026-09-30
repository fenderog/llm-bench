# Wildstride

A cozy, endless voxel horse runner through Sunset Valley. The horse, articulated gallop, landscape, obstacles, carrots, dust, UI, and sound effects are all generated inside Godot. No assets, plugins, or downloads are required.

## Run

Open `project.godot` in **Godot 4.7.2**, then press **F5**, or run:

```sh
godot --path .
```

Click **Hit the Trail** or press **Enter**. Collect carrots, jump fences and logs, and weave around hay bales. You have three spirit hearts; the trail gradually gets faster. Your best distance is remembered for the current session.

- **A / D** or **← / →**: change lanes
- **Space / W / ↑**: jump
- **Esc / P**: pause or resume
- **R**: restart
- **M**: toggle sound
- On-screen buttons also work with a mouse or touch.

Uses **GL Compatibility**, with no threads, external resources, or export plugins. Ready for a single-threaded web export; no export is included.

Load check:

```sh
godot --headless --path . --editor --quit
```
