# Voxel Runner

A tiny Godot 4.7 sandbox with a box-built voxel character ("Vex") who runs
around on his own. After a few seconds of AI wandering you can take over and
run him yourself.

Everything is generated in code — no external assets, plugins or downloads.
Built for the **GL Compatibility** renderer with thread support disabled
(`run/max_threads = 1`), so it is ready to be exported for the web.

## Run it

Desktop (needs a display):

```sh
godot --path . 
```

Or open the folder in the Godot editor (Project Manager → Import) and press F5.
Headless smoke test:

```sh
godot --headless --path . --editor --quit
```

## Controls

| Input | Action |
| --- | --- |
| W A S D / Arrow keys | Run (takes over from the AI) |
| Shift | Sprint |
| Space | Jump |
| I | Take over from the AI early |
| R | Teleport back to the spawn |
| Hold left mouse near screen edge | Pan the follow camera |
