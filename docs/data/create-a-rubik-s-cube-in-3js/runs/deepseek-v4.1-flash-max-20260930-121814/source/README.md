# Rubik's Cube — three.js

An interactive 3D Rubik's cube built with [three.js](https://threejs.org). No external
assets: the cube, its stickers and all lighting are generated in code, so the page runs
fully offline.

## Run it

Serve the folder with any static server and open `index.html`, e.g.

```sh
npx serve .
# or
python3 -m http.server
```

## Controls

| Action | Input |
| --- | --- |
| Turn a layer | Drag a sticker/face with the mouse or a finger |
| Orbit the camera | Drag the background |
| Zoom | Mouse wheel / pinch |
| Face turns | `U` `D` `L` `R` `F` `B` (hold `Shift` for the inverse) |
| Slice turns | `M` `E` `S` |
| Whole-cube rotations | `X` `Y` `Z` |
| Scramble / reset | Buttons in the top-right corner |

Press **Scramble** and the timer starts on your first move; when all six faces show a
single color the page tells you the time and move count.

## Files

- `index.html` — page shell, HUD and styles, loads `main.js` as an ES module.
- `main.js` — renderer, camera/controls, procedural lighting, pointer & keyboard
  input, drag-to-turn logic, and the timer/move-counter HUD.
- `cube.js` — the cube model: 26 rounded cubies with sticker meshes, queued and
  animated 90° turns, move notation parsing, scramble generation, solved detection.

## Notes

- Turns are animated on a temporary pivot group and snapped back to the exact 90°
  lattice afterwards, so the cube never accumulates floating-point drift.
- Lighting uses `RoomEnvironment` (procedurally generated) through `PMREMGenerator`,
  plus directional lights and a shadow catcher.
- Bundling: `esbuild main.js --bundle --format=esm --outfile=/dev/null`.
