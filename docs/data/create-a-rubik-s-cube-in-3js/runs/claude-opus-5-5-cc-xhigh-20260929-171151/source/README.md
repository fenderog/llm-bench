# Rubik's Cube (three.js)

An interactive Rubik's cube in the browser, built with [three.js](https://threejs.org/).

## Run

```sh
npm install
npx vite        # or any dev server that resolves bare module imports like "three"
```

`index.html` loads `main.js` as an ES module and `style.css` via a `<link>` tag. Everything,
including the lighting environment, is generated in code, so the page needs no network access
or storage once bundled.

## Features

- 2×2, 3×3, 4×4 and 5×5 cubes with rounded cubies and glossy stickers
- **Drag a sticker** to turn its layer. The layer follows your pointer and snaps to the nearest
  quarter turn, and a quick flick finishes the turn.
- **Drag the background** to orbit, scroll or pinch to zoom
- Keyboard notation relative to the current view: `U D L R F B`, `M E S`, `X Y Z`,
  `Shift` for counter-clockwise, a number prefix (`2`–`5`) for inner layers, and `Ctrl/⌘+Z` to undo
- **Scramble** shows the scramble in standard notation (white on top, green in front). The timer
  starts on your first turn and stops when the cube is solved.
- **Undo**, **Reset**, and **Solve**, which animates the move history in reverse (it rewinds your
  moves rather than computing an optimal solution)

## Files

| File          | Purpose                                                           |
| ------------- | ----------------------------------------------------------------- |
| `main.js`     | Scene, lighting, camera, UI, keyboard input, timer and game state |
| `cube.js`     | Cube geometry, layer-turn animation queue, snapping, solved check |
| `drag.js`     | Pointer interaction for grabbing and turning layers               |
| `notation.js` | Move notation, scrambles, view-relative key mapping               |
| `confetti.js` | Celebration particles                                             |
