# Rubik's Cube

An interactive 3×3×3 Rubik's Cube in the browser, built with [three.js](https://threejs.org/).
Open `index.html` (through a bundler or dev server) and start twisting.

## Controls

| Input | Action |
| --- | --- |
| Drag a face | Turn that layer; let go and it snaps to the nearest quarter turn (a quick flick commits the turn) |
| Drag the background, right-drag, or two fingers | Orbit the camera; scroll or pinch to zoom |
| `U` `D` `L` `R` `F` `B` | Turn a face clockwise; hold `Shift` for counter-clockwise |
| `M` `E` `S` | Turn the middle slices |
| `Backspace` / `Ctrl+Z` | Undo your last move |
| `?` | Show or hide the controls panel |

Buttons: **Scramble** (22 random turns, then the clock starts on your first move), **Solve** (plays your
moves back to the solved cube), **Undo**, **Reset**, and a **Speed** slider for the turn animations.
Solving a scrambled cube stops the clock and shows your time and move count.

## Code

- `main.js` – renderer, lights, camera/orbit controls, render loop, wiring
- `cube.js` – the cube model: 26 cubies, layer turns, animation queue, picking, solved check
- `input.js` – drag-to-turn on the cube and keyboard moves
- `game.js` – history, undo, scramble/solve, move counter, timer, win detection
- `hud.js`, `confetti.js`, `style.css` – interface and celebration effect

Everything (geometry, materials, lighting environment, textures) is generated in code, so the page has
no external assets and needs no network or storage.

## Development

```sh
npm install
esbuild main.js --bundle --format=esm --outfile=/dev/null   # checks that it packages
```
