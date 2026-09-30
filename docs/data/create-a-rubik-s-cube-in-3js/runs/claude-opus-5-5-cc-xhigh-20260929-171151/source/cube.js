import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export const SPACING = 1;
export const QUARTER = Math.PI / 2;

const CUBIE_SIZE = 0.96;
const STICKER_SIZE = 0.84;
const STICKER_RADIUS = 0.11;

// Face order: +X (R), -X (L), +Y (U), -Y (D), +Z (F), -Z (B), standard Western colour scheme.
export const FACE_COLORS = ['#c41e3a', '#ff6a13', '#f4f4f4', '#ffd500', '#009e60', '#0051ba'];

export const AXES = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)];

const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);

const _q = new THREE.Quaternion();
const _m = new THREE.Matrix4();
const _v = new THREE.Vector3();
const _z = new THREE.Vector3(0, 0, 1);

/** Wraps a quarter-turn count into -1, 0, 1 or 2. */
export function normalizeTurns(turns) {
  const t = ((turns % 4) + 4) % 4;
  return t === 3 ? -1 : t;
}

/**
 * A move is { axis: 0|1|2, layers: number[], turns }, where layers are indices 0..size-1
 * along the axis and positive turns rotate counter-clockwise about the positive axis.
 */
export function invertMove(move) {
  return { axis: move.axis, layers: [...move.layers], turns: normalizeTurns(-move.turns) };
}

function faceKey(v) {
  let axis = 0;
  for (let a = 1; a < 3; a++) if (Math.abs(v.getComponent(a)) > Math.abs(v.getComponent(axis))) axis = a;
  return axis * 2 + (v.getComponent(axis) > 0 ? 0 : 1);
}

function createStickerGeometry() {
  const s = STICKER_SIZE / 2;
  const r = STICKER_RADIUS;
  const shape = new THREE.Shape();
  shape.moveTo(-s + r, -s);
  shape.lineTo(s - r, -s);
  shape.absarc(s - r, -s + r, r, -Math.PI / 2, 0, false);
  shape.lineTo(s, s - r);
  shape.absarc(s - r, s - r, r, 0, Math.PI / 2, false);
  shape.lineTo(-s + r, s);
  shape.absarc(-s + r, s - r, r, Math.PI / 2, Math.PI, false);
  shape.lineTo(-s, -s + r);
  shape.absarc(-s + r, -s + r, r, Math.PI, Math.PI * 1.5, false);

  const bevel = 0.006;
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: 0.006,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 2,
    curveSegments: 6,
  });
  // Put the underside of the sticker at z = 0.
  geometry.translate(0, 0, bevel);
  return geometry;
}

export class RubiksCube {
  constructor() {
    this.group = new THREE.Group();
    this.size = 0;
    this.cubies = [];
    this.queue = [];
    this.turn = null; // layer currently detached from the grid (animating or being dragged)
    this.anim = null;
    this.turnDuration = 190;
    this.onIdle = null;

    this.bodyGeometry = new RoundedBoxGeometry(CUBIE_SIZE, CUBIE_SIZE, CUBIE_SIZE, 3, 0.08);
    this.bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x111114, roughness: 0.45, metalness: 0.05 });
    this.stickerGeometry = createStickerGeometry();
    this.stickerMaterials = FACE_COLORS.map(
      (color) =>
        new THREE.MeshPhysicalMaterial({ color, roughness: 0.3, clearcoat: 0.6, clearcoatRoughness: 0.2 }),
    );
  }

  get busy() {
    return this.turn !== null || this.queue.length > 0;
  }

  build(size) {
    this.queue.length = 0;
    this.anim = null;
    this.turn = null;
    for (const cubie of this.cubies) this.group.remove(cubie);
    this.cubies = [];
    this.size = size;

    const half = (size - 1) / 2;
    for (let x = 0; x < size; x++) {
      for (let y = 0; y < size; y++) {
        for (let z = 0; z < size; z++) {
          const coord = [x, y, z];
          if (!coord.some((c) => c === 0 || c === size - 1)) continue; // hidden core

          const cubie = new THREE.Group();
          cubie.add(new THREE.Mesh(this.bodyGeometry, this.bodyMaterial));

          const stickers = [];
          for (let axis = 0; axis < 3; axis++) {
            for (const sign of [1, -1]) {
              if (coord[axis] !== (sign > 0 ? size - 1 : 0)) continue;
              const face = axis * 2 + (sign > 0 ? 0 : 1);
              const normal = AXES[axis].clone().multiplyScalar(sign);
              const sticker = new THREE.Mesh(this.stickerGeometry, this.stickerMaterials[face]);
              sticker.quaternion.setFromUnitVectors(_z, normal);
              sticker.position.copy(normal).multiplyScalar(CUBIE_SIZE / 2 - 0.002);
              sticker.userData = { face, normal };
              cubie.add(sticker);
              stickers.push(sticker);
            }
          }

          cubie.position.set((x - half) * SPACING, (y - half) * SPACING, (z - half) * SPACING);
          cubie.userData = {
            coord,
            stickers,
            basePosition: new THREE.Vector3(),
            baseQuaternion: new THREE.Quaternion(),
          };
          this.group.add(cubie);
          this.cubies.push(cubie);
        }
      }
    }
  }

  /** Queues an animated move. `duration` (ms) overrides the default speed. */
  enqueue(move, duration) {
    this.queue.push({ move, duration });
  }

  /** Detaches a set of layers so they can be rotated freely. */
  beginTurn(axis, layers) {
    const cubies = this.cubies.filter((c) => layers.includes(c.userData.coord[axis]));
    for (const c of cubies) {
      c.userData.basePosition.copy(c.position);
      c.userData.baseQuaternion.copy(c.quaternion);
    }
    this.turn = { axis, layers, cubies, angle: 0 };
  }

  setTurnAngle(angle) {
    const turn = this.turn;
    turn.angle = angle;
    _q.setFromAxisAngle(AXES[turn.axis], angle);
    for (const c of turn.cubies) {
      c.position.copy(c.userData.basePosition).applyQuaternion(_q);
      c.quaternion.copy(_q).multiply(c.userData.baseQuaternion);
    }
  }

  /** Animates the detached layer from wherever it is to the nearest whole number of quarter turns. */
  settleTurn(turns) {
    const from = this.turn.angle;
    const to = turns * QUARTER;
    const duration = 70 + Math.min(1.5, Math.abs(to - from) / QUARTER) * 150;
    this.anim = { from, to, turns, start: performance.now(), duration, ease: easeOut };
  }

  endTurn(turns) {
    this.setTurnAngle(turns * QUARTER);
    for (const c of this.turn.cubies) this.snap(c);
    this.turn = null;
  }

  /** Removes floating-point drift and refreshes the cubie's grid coordinates. */
  snap(cubie) {
    const half = (this.size - 1) / 2;
    for (let a = 0; a < 3; a++) {
      const i = Math.round(cubie.position.getComponent(a) / SPACING + half);
      cubie.userData.coord[a] = i;
      cubie.position.setComponent(a, (i - half) * SPACING);
    }
    _m.makeRotationFromQuaternion(cubie.quaternion);
    const e = _m.elements;
    for (let i = 0; i < 16; i++) e[i] = Math.round(e[i]);
    cubie.quaternion.setFromRotationMatrix(_m);
  }

  update(now) {
    if (this.anim) {
      const a = this.anim;
      const t = Math.min(1, Math.max(0, (now - a.start) / a.duration));
      this.setTurnAngle(a.from + (a.to - a.from) * a.ease(t));
      if (t < 1) return;
      this.anim = null;
      this.endTurn(a.turns);
      if (this.queue.length === 0) this.onIdle?.();
    }

    if (!this.turn && this.queue.length > 0) {
      const { move, duration } = this.queue.shift();
      let ms = duration ?? this.turnDuration * (this.queue.length > 1 ? 0.6 : 1);
      if (Math.abs(move.turns) === 2) ms *= 1.4;
      this.beginTurn(move.axis, move.layers);
      this.anim = { from: 0, to: move.turns * QUARTER, turns: move.turns, start: now, duration: ms, ease: easeInOut };
    }
  }

  /** True when every face shows a single colour, regardless of whole-cube orientation. */
  isSolved() {
    const seen = [-1, -1, -1, -1, -1, -1];
    for (const cubie of this.cubies) {
      for (const sticker of cubie.userData.stickers) {
        _v.copy(sticker.userData.normal).applyQuaternion(cubie.quaternion);
        const key = faceKey(_v);
        if (seen[key] === -1) seen[key] = sticker.userData.face;
        else if (seen[key] !== sticker.userData.face) return false;
      }
    }
    return true;
  }
}
