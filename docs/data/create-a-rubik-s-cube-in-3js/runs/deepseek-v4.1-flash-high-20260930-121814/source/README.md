# Rubik's Cube — Three.js

An interactive 3D Rubik's Cube rendered with [Three.js](https://threejs.org/).
Everything runs locally in the browser; there are no external assets or network
requests.

## Features

- 27 rounded cubies with rounded sticker tiles, soft lighting and shadows.
- **Drag a face** to turn the slice you grabbed. The drag direction is projected
  into screen space to decide the rotation axis and direction.
- **Drag the background** to orbit the camera, scroll/pinch to zoom (powered by
  `OrbitControls`).
- **Scramble / Reset / Undo** buttons.
- **Keyboard moves**: `U`, `D`, `L`, `R`, `F`, `B` (and `M`, `E`, `S` for the
  middle slices). Hold `Shift` for the counter-clockwise / inverse turn.
- Live status showing whether the cube is `Solved` or `Scrambled`.

## Files

| File         | Purpose                                        |
| ------------ | ---------------------------------------------- |
| `index.html` | Page shell, HUD and control buttons.           |
| `styles.css` | Dark UI styling.                               |
| `main.js`    | Three.js scene, cube model and move engine.    |

## Running

```bash
npm install
npx esbuild main.js --bundle --format=esm --outfile=bundle.js
```

Then serve the directory (or open a packaged build). During development you can
also use any static server, e.g. `npx serve .`.

## How it works

`main.js` builds each cubie as a `THREE.Group` containing a dark body box plus
one rounded `ShapeGeometry` sticker per outward-facing side. A layer turn is
animated by re-parenting the affected cubies to a temporary pivot group, rotating
the pivot by 90°, then re-attaching the cubies and snapping their transforms to
the exact lattice so floating-point drift never accumulates.

Drag-to-turn picks the sticker under the pointer with a `Raycaster`, derives the
face normal and the screen-space tangent for a positive rotation, and queues a
quarter turn whose layer matches the picked cubie.
