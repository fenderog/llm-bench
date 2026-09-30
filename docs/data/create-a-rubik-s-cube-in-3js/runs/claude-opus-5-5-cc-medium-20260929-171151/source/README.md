# Rubik's Cube (three.js)

An interactive 3×3 Rubik's Cube rendered with three.js.

- **Drag a face** to turn that layer (direction follows your drag); drag empty space to orbit, scroll to zoom.
- **Keyboard:** `U D L R F B M E S` turn layers clockwise, hold **Shift** for counter-clockwise; `Ctrl/Cmd+Z` undoes.
- **Buttons:** Scramble, Solve (plays back the inverse of all moves), Undo, Reset, and on-screen move buttons.
- Move counter and timer (starts on your first move after a scramble); a banner appears when solved.

Run: `npm install`, then serve the folder with any static server that resolves bare imports (e.g. `npx vite`), or bundle with esbuild.
