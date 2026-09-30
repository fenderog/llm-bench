# Rubik's Cube — three.js

An interactive 3×3×3 Rubik's Cube rendered with [three.js](https://threejs.org/).
Everything (geometry, colors, materials) is generated in code, so the page works
completely offline.

## Run

```bash
npm install
npx serve .        # or any static file server
```

Then open `index.html`. The page must be served over HTTP so the ES modules load.

## Controls

- **Drag a face** of the cube to turn that layer in the direction you drag.
- **Drag the background** to orbit the camera.
- **Scroll / pinch** to zoom.
- **Keys** `R` `L` `U` `D` `F` `B` perform face turns; hold `Shift` for the
  counter-clockwise (`'`) variant.
- **Buttons** at the bottom perform every face turn, plus **Scramble** and
  **Reset**.

## Implementation notes

- Each of the 26 visible cubies is a rounded box with extruded rounded-rectangle
  stickers, so no textures or external assets are needed.
- Moves are queued and animated on a temporary pivot group. Once a turn finishes
  the affected cubies are re-parented to the cube and their logical integer
  positions / orientations are baked in, which keeps the state consistent.
- Drag-to-turn raycasts against the cubie bodies, snaps the hit normal to a world
  axis, then projects the two in-face axes to screen space to decide which layer
  to rotate and in which direction.

## Build check

```bash
esbuild main.js --bundle --format=esm --outfile=/dev/null
```
