# Rubik's Cube (three.js)

An interactive 3×3 Rubik's Cube rendered with three.js.

## Controls

- **Drag a face** of the cube to turn that layer. The layer follows your pointer and snaps to the nearest quarter turn when you let go. A quick flick commits the turn.
- **Drag the background** to orbit the camera. Scroll or pinch to zoom.
- **Keyboard:** `U D L R F B` turn the faces, `M E S` turn the slices, `X Y Z` rotate the whole cube. Hold `Shift` to turn counter-clockwise (′).
  `Backspace` undoes the last move and `Space` scrambles.
- **Buttons:** face turns, Scramble, Solve (plays the move history back in reverse), Undo, Reset, Reset view, and a speed slider.

After a scramble, the timer starts on your first move and stops when the cube is solved.

## Running

```sh
npm install
npx esbuild main.js --bundle --format=esm --outfile=bundle.js   # or serve with any ES-module-aware dev server
```

The entry point is `index.html`, which loads `main.js` as an ES module. Everything is generated in code (geometry, stickers, the environment map and the shadow texture), so the page makes no network requests and uses no storage.
