# Rubik's Cube (three.js)

An interactive 3×3×3 Rubik's Cube.

- **Drag a sticker** to turn that layer; **drag the background** to orbit; scroll/pinch to zoom.
- **Keys:** `U D L R F B` turn a face clockwise, hold `Shift` for counter-clockwise.
- **Buttons:** move pad, Scramble, Solve (replays your move history in reverse), Reset, and an animation speed slider.

Run with any static server after `npm install` (e.g. `npx vite`), or bundle with
`esbuild main.js --bundle --format=esm --outfile=bundle.js`.
