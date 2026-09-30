# COPPER · Wild Run

A self-contained Godot 4.7.2 voxel horse runner, set on an endless golden-hour trail. The horse, landscape, interface, collectibles, and hoof sounds are generated in code. No external assets or plugins.

## Run

Open `project.godot` in Godot 4.7.2 and press **F5**, or run:

```sh
godot --path .
```

- **A / D** or **← / →** — change lanes
- **Space**, **W**, or **↑** — jump fences and rocks
- **Shift** — sprint (uses energy; release to recover)
- **P / Esc** — pause
- **R** — restart
- **M** — toggle sound

Collect golden sunshards and travel as far as you can. Three collisions end the ride. The HUD's steer, jump, pause, and audio buttons can also be clicked.

Uses the **GL Compatibility** renderer. No thread support, downloads, or external dependencies are required for web export.
