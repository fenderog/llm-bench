/**
 * cube.js — the Rubik's cube model.
 *
 * The cube is made of 26 rounded "cubies" (the core is invisible).  Each
 * cubie carries colored stickers as children.  Turns are animatable:
 * a temporary pivot group is rotated, cubies of the selected layer are
 * attached to it, and when the turn finishes they are re-attached to the
 * cube and their transforms are snapped to the exact 90° lattice so the
 * cube never drifts.
 */

import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

export const CUBIE_SIZE = 0.94; // world units, cubies are spaced 1.0 apart
const STICKER_SIZE = 0.72;
const STICKER_RADIUS = 0.13;
const STICKER_LIFT = 0.012;
const DEFAULT_TURN_TIME = 0.16; // seconds

/** Sticker colors, one per face (western color scheme). */
export const FACE_COLORS = {
  R: 0xd63031, // +x  red
  L: 0xff7f1f, // -x  orange
  U: 0xf7f7f7, // +y  white
  D: 0xffd21e, // -y  yellow
  F: 0x21b25c, // +z  green
  B: 0x1e6fd9, // -z  blue
};

const FACE_DEFS = [
  { key: 'R', normal: new THREE.Vector3(1, 0, 0) },
  { key: 'L', normal: new THREE.Vector3(-1, 0, 0) },
  { key: 'U', normal: new THREE.Vector3(0, 1, 0) },
  { key: 'D', normal: new THREE.Vector3(0, -1, 0) },
  { key: 'F', normal: new THREE.Vector3(0, 0, 1) },
  { key: 'B', normal: new THREE.Vector3(0, 0, -1) },
];

/**
 * Turn definitions.  `axis` is the rotation axis (a unit vector along a
 * signed basis direction) and a positive angle follows it.  A clockwise
 * face turn (seen from outside the face) rotates about the face's inward
 * normal, hence the negated axes.
 */
const TURN_DEFS = {
  U: { axis: [0, -1, 0], name: 'y', layer: 1 },
  D: { axis: [0, 1, 0], name: 'y', layer: -1 },
  R: { axis: [-1, 0, 0], name: 'x', layer: 1 },
  L: { axis: [1, 0, 0], name: 'x', layer: -1 },
  F: { axis: [0, 0, -1], name: 'z', layer: 1 },
  B: { axis: [0, 0, 1], name: 'z', layer: -1 },
  M: { axis: [1, 0, 0], name: 'x', layer: 0 }, // middle slice, follows L
  E: { axis: [0, 1, 0], name: 'y', layer: 0 }, // equator slice, follows D
  S: { axis: [0, 0, -1], name: 'z', layer: 0 }, // standing slice, follows F
  X: { axis: [-1, 0, 0], name: 'x', layer: 'all' }, // whole cube, follows R
  Y: { axis: [0, -1, 0], name: 'y', layer: 'all' }, // whole cube, follows U
  Z: { axis: [0, 0, -1], name: 'z', layer: 'all' }, // whole cube, follows F
};

const Z_AXIS = new THREE.Vector3(0, 0, 1);

/** Rounded-square ShapeGeometry used for every sticker. */
function roundedRectGeometry(size, radius) {
  const h = size / 2;
  const r = Math.min(radius, h);
  const shape = new THREE.Shape();
  shape.moveTo(-h + r, -h);
  shape.lineTo(h - r, -h);
  shape.quadraticCurveTo(h, -h, h, -h + r);
  shape.lineTo(h, h - r);
  shape.quadraticCurveTo(h, h, h - r, h);
  shape.lineTo(-h + r, h);
  shape.quadraticCurveTo(-h, h, -h, h - r);
  shape.lineTo(-h, -h + r);
  shape.quadraticCurveTo(-h, -h, -h + r, -h);
  return new THREE.ShapeGeometry(shape, 10);
}

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/** Snap a cubie to the exact position/rotation lattice after a turn. */
function snapCubie(cubie) {
  const p = cubie.position;
  p.set(Math.round(p.x), Math.round(p.y), Math.round(p.z));

  const m = new THREE.Matrix4().makeRotationFromQuaternion(cubie.quaternion);
  const e = m.elements;
  for (let i = 0; i < 16; i++) e[i] = Math.round(e[i]);
  cubie.quaternion.setFromRotationMatrix(m);
}

/**
 * Parse standard cube notation: "R", "R'", "M", "x", "Y'" ...
 * Returns a move description understood by RubiksCube#enqueue.
 */
export function parseMove(notation, duration = DEFAULT_TURN_TIME) {
  if (typeof notation !== 'string' || notation.length === 0) return null;
  const face = notation[0].toUpperCase();
  const def = TURN_DEFS[face];
  if (!def) return null;
  const suffix = notation.slice(1);
  const prime = suffix === "'" || suffix === '’' || suffix.toLowerCase() === 'i';

  const axis = new THREE.Vector3(...def.axis).normalize();
  return {
    notation: face + (prime ? "'" : ''),
    axis,
    axisName: def.name,
    layer: def.layer,
    angle: ((prime ? -1 : 1) * Math.PI) / 2,
    duration,
    elapsed: 0,
  };
}

/** A random face-turn sequence (no two turns on the same face in a row). */
export function randomScramble(count = 22) {
  const faces = ['U', 'D', 'L', 'R', 'F', 'B'];
  const moves = [];
  let last = null;
  while (moves.length < count) {
    const face = faces[(Math.random() * faces.length) | 0];
    if (face === last) continue;
    last = face;
    moves.push(face + (Math.random() < 0.5 ? "'" : ''));
  }
  return moves;
}

export class RubiksCube extends THREE.Group {
  constructor() {
    super();
    this.name = 'RubiksCube';

    /** @type {THREE.Group[]} */
    this.cubies = [];
    /** @type {object[]} moves waiting to be animated */
    this.queue = [];
    /** @type {object|null} move currently being animated */
    this.active = null;

    // Turning is done by rotating a pivot group and moving the affected
    // cubies onto it for the duration of the animation.  (Note: the name
    // must not be `pivot` — three's Object3D has a built-in pivot point.)
    this.turnPivot = new THREE.Group();
    this.turnPivot.name = 'turnPivot';
    this.add(this.turnPivot);

    this._bodyGeometry = new RoundedBoxGeometry(CUBIE_SIZE, CUBIE_SIZE, CUBIE_SIZE, 4, 0.075);
    this._bodyMaterial = new THREE.MeshStandardMaterial({
      color: 0x14161a,
      roughness: 0.42,
      metalness: 0.12,
      envMapIntensity: 0.7,
    });
    this._stickerGeometry = roundedRectGeometry(STICKER_SIZE, STICKER_RADIUS);
    this._stickerMaterials = new Map();

    this._build();
  }

  _build() {
    for (let x = -1; x <= 1; x++) {
      for (let y = -1; y <= 1; y++) {
        for (let z = -1; z <= 1; z++) {
          if (x === 0 && y === 0 && z === 0) continue; // invisible core
          this.add(this._buildCubie(x, y, z));
        }
      }
    }
  }

  _buildCubie(x, y, z) {
    const cubie = new THREE.Group();
    cubie.position.set(x, y, z);
    cubie.userData.home = cubie.position.clone();
    cubie.userData.stickers = [];

    const body = new THREE.Mesh(this._bodyGeometry, this._bodyMaterial);
    body.castShadow = true;
    body.receiveShadow = true;
    body.userData.cubie = cubie;
    cubie.add(body);

    for (const face of FACE_DEFS) {
      const { normal } = face;
      // Only cubies on the outside of that face get a sticker.
      const onFace =
        (normal.x !== 0 && x === normal.x) ||
        (normal.y !== 0 && y === normal.y) ||
        (normal.z !== 0 && z === normal.z);
      if (!onFace) continue;

      const sticker = new THREE.Mesh(this._stickerGeometry, this._stickerMaterial(face.key));
      sticker.quaternion.setFromUnitVectors(Z_AXIS, normal);
      sticker.position.copy(normal).multiplyScalar(CUBIE_SIZE / 2 + STICKER_LIFT);
      sticker.userData.cubie = cubie;
      sticker.userData.normal = normal.clone();
      sticker.userData.color = face.key;
      cubie.add(sticker);
      cubie.userData.stickers.push(sticker);
    }

    this.cubies.push(cubie);
    return cubie;
  }

  _stickerMaterial(faceKey) {
    if (!this._stickerMaterials.has(faceKey)) {
      this._stickerMaterials.set(
        faceKey,
        new THREE.MeshPhysicalMaterial({
          color: FACE_COLORS[faceKey],
          roughness: 0.34,
          metalness: 0.0,
          clearcoat: 1.0,
          clearcoatRoughness: 0.24,
          envMapIntensity: 0.9,
        }),
      );
    }
    return this._stickerMaterials.get(faceKey);
  }

  /** True while a turn animation is running. */
  get busy() {
    return this.active !== null;
  }

  /** Queue a move; `move` comes from parseMove(). */
  enqueue(move) {
    if (!move) return;
    this.queue.push(move);
    // Never let an over-eager key repeat build an unbounded backlog.
    if (this.queue.length > 120) this.queue.splice(0, this.queue.length - 120);
  }

  /** Advance the current animation (dt in seconds). */
  update(dt) {
    if (!this.active) {
      const next = this.queue.shift();
      if (!next) return;
      this._begin(next);
    }

    const move = this.active;
    const duration = move.duration ?? DEFAULT_TURN_TIME;
    move.elapsed += dt;
    const t = duration > 0 ? Math.min(1, move.elapsed / duration) : 1;
    this.turnPivot.quaternion.setFromAxisAngle(move.axis, move.angle * easeInOutCubic(t));

    if (t >= 1) this._finish();
  }

  _begin(move) {
    this.active = move;
    this.turnPivot.quaternion.identity();
    this.updateMatrixWorld(true);

    for (const cubie of this.cubies) {
      const coord = Math.round(cubie.position[move.axisName]);
      if (move.layer === 'all' || coord === move.layer) {
        this.turnPivot.attach(cubie);
      }
    }
  }

  _finish() {
    const move = this.active;
    this.turnPivot.quaternion.setFromAxisAngle(move.axis, move.angle);
    this.turnPivot.updateMatrixWorld(true);

    for (const cubie of this.cubies) {
      if (cubie.parent !== this.turnPivot) continue;
      this.attach(cubie);
      snapCubie(cubie);
    }

    this.turnPivot.quaternion.identity();
    this.active = null;
    this.dispatchEvent({ type: 'movecomplete', move });
  }

  /** Instantly restore the solved state. */
  reset() {
    this.queue.length = 0;
    this.active = null;
    this.turnPivot.quaternion.identity();
    for (const cubie of this.cubies) {
      if (cubie.parent !== this) this.add(cubie);
      cubie.position.copy(cubie.userData.home);
      cubie.quaternion.identity();
    }
  }

  /**
   * True when every face shows a single color (any whole-cube orientation
   * counts as solved).
   */
  isSolved() {
    const dir = new THREE.Vector3();
    for (const face of FACE_DEFS) {
      const { normal } = face;
      let color = null;
      for (const cubie of this.cubies) {
        if (Math.round(cubie.position.dot(normal)) !== 1) continue;
        for (const sticker of cubie.userData.stickers) {
          dir.copy(sticker.userData.normal).applyQuaternion(cubie.quaternion);
          if (dir.dot(normal) > 0.9) {
            const key = sticker.userData.color;
            if (color === null) color = key;
            else if (key !== color) return false;
          }
        }
      }
    }
    return true;
  }
}
