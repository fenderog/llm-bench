import * as THREE from 'three';
import { normalizeTurns } from './cube.js';

const SUFFIX = ['', '', '2', "'"];
const suffix = (amount) => SUFFIX[((amount % 4) + 4) % 4];

/** Formats a single-layer move in standard notation (SiGN prefixes like "2R" for inner layers). */
export function formatMove({ axis, layers, turns }, size) {
  const layer = layers[0];
  if (size === 3 && layer === 1) {
    // M follows L, E follows D, S follows F.
    return 'MES'[axis] + suffix(axis === 2 ? -turns : turns);
  }
  if (layer >= (size - 1) / 2) {
    const depth = size - layer;
    return (depth > 1 ? depth : '') + 'RUF'[axis] + suffix(-turns);
  }
  return (layer > 0 ? layer + 1 : '') + 'LDB'[axis] + suffix(turns);
}

/**
 * Random-move scramble. Middle layers of odd cubes are skipped so the centres stay put, and
 * no layer is turned twice within a run of moves on the same axis (avoids R R and R L R).
 */
export function generateScramble(size, length) {
  const middle = (size - 1) / 2;
  const layers = [...Array(size).keys()].filter((l) => l !== middle);
  const pick = (list) => list[Math.floor(Math.random() * list.length)];
  const moves = [];
  let runAxis = -1;
  let runLayers = new Set();
  while (moves.length < length) {
    const axis = Math.floor(Math.random() * 3);
    const layer = pick(layers);
    if (axis === runAxis && runLayers.has(layer)) continue;
    if (axis !== runAxis) {
      runAxis = axis;
      runLayers = new Set();
    }
    runLayers.add(layer);
    moves.push({ axis, layers: [layer], turns: pick([1, -1, 2]) });
  }
  return moves;
}

/** Collapses consecutive moves on the same layers (R R' disappears, R R becomes R2). */
export function mergeMoves(moves) {
  const out = [];
  for (const move of moves) {
    const prev = out[out.length - 1];
    if (prev && prev.axis === move.axis && prev.layers.join() === move.layers.join()) {
      const turns = normalizeTurns(prev.turns + move.turns);
      if (turns === 0) out.pop();
      else prev.turns = turns;
    } else {
      out.push({ ...move, layers: [...move.layers] });
    }
  }
  return out;
}

function dominantAxis(v, exclude = -1) {
  let axis = -1;
  for (let a = 0; a < 3; a++) {
    if (a === exclude) continue;
    if (axis === -1 || Math.abs(v.getComponent(a)) > Math.abs(v.getComponent(axis))) axis = a;
  }
  return { axis, sign: v.getComponent(axis) >= 0 ? 1 : -1 };
}

const toVector = ({ axis, sign }) => new THREE.Vector3().setComponent(axis, sign);
const opposite = ({ axis, sign }) => ({ axis, sign: -sign });

/** Works out which cube face is front / up / right from the camera's point of view. */
export function viewFrame(camera, target) {
  const F = dominantAxis(camera.position.clone().sub(target));
  const U = dominantAxis(new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion), F.axis);
  const R = dominantAxis(toVector(U).cross(toVector(F)));
  return { F, U, R, B: opposite(F), D: opposite(U), L: opposite(R) };
}

/**
 * Maps a key press to a move, relative to the current view. `depth` selects an inner layer
 * (1 = outer face) for U/D/L/R/F/B.
 */
export function keyMove(key, prime, depth, size, frame) {
  const amount = prime ? -1 : 1;
  const all = [...Array(size).keys()];
  // Clockwise when looking at the face = negative rotation about its outward normal.
  const turn = (face, layers) => ({ axis: face.axis, layers, turns: -face.sign * amount });

  if ('UDLRFB'.includes(key)) {
    const face = frame[key];
    const d = Math.min(Math.max(depth, 1), size);
    return turn(face, [face.sign > 0 ? size - d : d - 1]);
  }
  if ('MES'.includes(key)) {
    if (size < 3) return null;
    return turn(frame[{ M: 'L', E: 'D', S: 'F' }[key]], all.slice(1, -1));
  }
  if ('XYZ'.includes(key)) {
    return turn(frame[{ X: 'R', Y: 'U', Z: 'F' }[key]], all);
  }
  return null;
}
