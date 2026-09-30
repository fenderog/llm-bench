# Twist

An offline-friendly interactive Rubik’s cube built with Three.js and JavaScript ES modules. Includes rounded 3D cubies, orbit and zoom, animated face turns, a 20-turn scramble, undo, move history, timer, and auto-solve that reverses the recorded moves.

## Use

Serve `index.html` through an ES-module bundler such as Vite, or use the provided packaging workflow. Dependencies are installed with `npm install`.

Drag to orbit, scroll to zoom, or click a face to turn. The U / D / L / R / F / B keys turn faces; hold Shift to reverse. The direction selector also applies to face buttons and clicks.

No network assets or browser storage are used. Styles are referenced by `index.html` for the packaging workflow.

Bundle check: `npx esbuild main.js --bundle --format=esm --outfile=/dev/null`.
