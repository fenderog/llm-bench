# Cubiq

An interactive Three.js Rubik’s cube with rounded cubies, animated face turns, orbit controls, and a responsive dark-and-lime interface.

## Run

```sh
npm install
npm run dev
```

Open the local URL printed by Vite. Entry point: `index.html`; application: `main.js`; styles: `style.css`.

## Controls

- Drag to orbit; scroll or pinch to zoom.
- Click a colored face, or press **U D L R F B**, to turn it.
- Hold **Shift** to reverse a turn; the direction button also toggles reverse turns.
- **Space** scrambles; **Ctrl/⌘ + Z** undoes.
- **Solve** animates the inverse of all recorded turns, including the scramble.
- Includes move history, session timer, reset, optional synthesized sound, and a shortcut guide.

All geometry and assets are generated locally. No runtime network requests or browser storage.

Bundle compatibility check (no build output):

```sh
npm run check
```
