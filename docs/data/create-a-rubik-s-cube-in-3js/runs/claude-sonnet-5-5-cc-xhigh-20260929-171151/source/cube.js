import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

// A move turns one slab of the cube: `axis` is 0/1/2 for x/y/z, `layer` is the
// slab index along that axis (-1, 0 or 1) and `turns` is the number of quarter
// turns (+1 is counter-clockwise looking down the positive axis, so -1, 1 or 2).

export const QUARTER = Math.PI / 2;
export const AXES = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)];

export const FACE_COLORS = {
  R: 0xc8163a,
  L: 0xff5a0a,
  U: 0xf2f2ec,
  D: 0xffd000,
  F: 0x009e4f,
  B: 0x0a48b8,
};

const FACES = [
  { name: "R", normal: new THREE.Vector3(1, 0, 0) },
  { name: "L", normal: new THREE.Vector3(-1, 0, 0) },
  { name: "U", normal: new THREE.Vector3(0, 1, 0) },
  { name: "D", normal: new THREE.Vector3(0, -1, 0) },
  { name: "F", normal: new THREE.Vector3(0, 0, 1) },
  { name: "B", normal: new THREE.Vector3(0, 0, -1) },
];

const BODY_SIZE = 0.97;
const STICKER_SIZE = 0.84;
const STICKER_DEPTH = 0.008;
const STICKER_BEVEL = 0.01;

const BASE_TURN_TIME = 0.27; // seconds for one quarter turn at speed 1

const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

export function normTurns(t) {
  const m = ((t % 4) + 4) % 4;
  return m === 3 ? -1 : m;
}

export function inverseMove(move) {
  return { ...move, turns: normTurns(-move.turns) };
}

// Merges neighbouring moves of the same slab, dropping the ones that cancel out.
export function simplifyMoves(moves) {
  const out = [];
  for (const move of moves) {
    const last = out[out.length - 1];
    if (last && last.axis === move.axis && last.layer === move.layer) {
      const turns = normTurns(last.turns + move.turns);
      if (turns === 0) out.pop();
      else last.turns = turns;
    } else {
      out.push({ axis: move.axis, layer: move.layer, turns: move.turns });
    }
  }
  return out;
}

function roundedSquare(size, radius) {
  const h = size / 2;
  const s = new THREE.Shape();
  s.moveTo(-h + radius, -h);
  s.lineTo(h - radius, -h);
  s.absarc(h - radius, -h + radius, radius, -Math.PI / 2, 0, false);
  s.lineTo(h, h - radius);
  s.absarc(h - radius, h - radius, radius, 0, Math.PI / 2, false);
  s.lineTo(-h + radius, h);
  s.absarc(-h + radius, h - radius, radius, Math.PI / 2, Math.PI, false);
  s.lineTo(-h, -h + radius);
  s.absarc(-h + radius, -h + radius, radius, Math.PI, Math.PI * 1.5, false);
  return s;
}

// Rotates a set of cubies around one of the world axes, keeping their starting
// pose so the angle can be scrubbed freely (dragging) or animated.
class LayerTurn {
  constructor(cubies, axis) {
    this.cubies = cubies;
    this.axisIndex = axis;
    this.axis = AXES[axis];
    this.angle = 0;
    this.base = cubies.map((c) => ({ p: c.position.clone(), q: c.quaternion.clone() }));
    this._q = new THREE.Quaternion();
  }

  setAngle(angle) {
    this.angle = angle;
    this._q.setFromAxisAngle(this.axis, angle);
    this.cubies.forEach((c, i) => {
      c.position.copy(this.base[i].p).applyQuaternion(this._q);
      c.quaternion.copy(this._q).multiply(this.base[i].q);
    });
  }

  // Lands exactly on the target and removes any floating point drift.
  commit(angle) {
    this.setAngle(angle);
    const m = new THREE.Matrix4();
    for (const c of this.cubies) {
      c.position.set(Math.round(c.position.x), Math.round(c.position.y), Math.round(c.position.z));
      m.makeRotationFromQuaternion(c.quaternion);
      m.fromArray(m.elements.map(Math.round));
      c.quaternion.setFromRotationMatrix(m);
    }
  }
}

export class RubiksCube {
  constructor() {
    this.group = new THREE.Group();
    this.cubies = [];
    this.queue = [];
    this.active = null;
    this.speed = 1;
    this.onIdle = null;
    this._wasBusy = false;
    this._pickBox = new THREE.Box3(new THREE.Vector3(-1.5, -1.5, -1.5), new THREE.Vector3(1.5, 1.5, 1.5));
    this._hit = new THREE.Vector3();

    this._buildCubies();
  }

  _buildCubies() {
    const bodyGeo = new RoundedBoxGeometry(BODY_SIZE, BODY_SIZE, BODY_SIZE, 4, 0.085);
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0x101114, roughness: 0.42, metalness: 0.05 });

    const stickerGeo = new THREE.ExtrudeGeometry(roundedSquare(STICKER_SIZE - STICKER_BEVEL * 2, 0.115), {
      depth: STICKER_DEPTH,
      bevelEnabled: true,
      bevelThickness: STICKER_BEVEL,
      bevelSize: STICKER_BEVEL,
      bevelSegments: 2,
      curveSegments: 8,
    });
    const stickerMats = {};
    for (const [name, color] of Object.entries(FACE_COLORS)) {
      stickerMats[name] = new THREE.MeshPhysicalMaterial({
        color,
        roughness: 0.34,
        metalness: 0,
        clearcoat: 0.8,
        clearcoatRoughness: 0.22,
      });
    }

    const zAxis = new THREE.Vector3(0, 0, 1);
    for (let x = -1; x <= 1; x++) {
      for (let y = -1; y <= 1; y++) {
        for (let z = -1; z <= 1; z++) {
          if (x === 0 && y === 0 && z === 0) continue;

          const cubie = new THREE.Group();
          cubie.position.set(x, y, z);

          const body = new THREE.Mesh(bodyGeo, bodyMat);
          body.castShadow = true;
          cubie.add(body);

          const stickers = [];
          for (const face of FACES) {
            const { normal } = face;
            if (normal.x * x + normal.y * y + normal.z * z !== 1) continue;
            const sticker = new THREE.Mesh(stickerGeo, stickerMats[face.name]);
            sticker.quaternion.setFromUnitVectors(zAxis, normal);
            sticker.position.copy(normal).multiplyScalar(BODY_SIZE / 2);
            cubie.add(sticker);
            stickers.push({ normal: normal.clone(), color: face.name });
          }

          cubie.userData = { home: new THREE.Vector3(x, y, z), stickers };
          this.cubies.push(cubie);
          this.group.add(cubie);
        }
      }
    }
  }

  get busy() {
    return this.active !== null || this.queue.length > 0;
  }

  reset() {
    this.queue.length = 0;
    this.active = null;
    this._wasBusy = false;
    for (const c of this.cubies) {
      c.position.copy(c.userData.home);
      c.quaternion.identity();
    }
  }

  // Sticker colours per outward direction; the cube is solved when each
  // direction shows a single colour. Only meaningful while at rest.
  isSolved() {
    const seen = new Map();
    const n = new THREE.Vector3();
    for (const c of this.cubies) {
      for (const s of c.userData.stickers) {
        n.copy(s.normal).applyQuaternion(c.quaternion);
        const key = `${Math.round(n.x)},${Math.round(n.y)},${Math.round(n.z)}`;
        const color = seen.get(key);
        if (color === undefined) seen.set(key, s.color);
        else if (color !== s.color) return false;
      }
    }
    return true;
  }

  // ---- picking -----------------------------------------------------------

  // Intersects a world-space ray with the cube's outer surface. Returns the
  // hit point, the face axis/sign that was hit and the grid cell under it.
  pick(ray) {
    const p = ray.intersectBox(this._pickBox, this._hit);
    if (!p) return null;
    let axis = 0;
    let max = -1;
    for (let i = 0; i < 3; i++) {
      const v = Math.abs(p.getComponent(i));
      if (v > max) {
        max = v;
        axis = i;
      }
    }
    const sign = Math.sign(p.getComponent(axis));
    const cell = [0, 1, 2].map((i) =>
      i === axis ? sign : THREE.MathUtils.clamp(Math.round(p.getComponent(i)), -1, 1),
    );
    return { point: p.clone(), axis, sign, cell };
  }

  // ---- queued, animated moves -------------------------------------------

  enqueue(move, tag = "user", timeScale = 1) {
    this.queue.push({ ...move, tag, timeScale });
  }

  enqueueCall(fn) {
    this.queue.push({ call: fn });
  }

  _slab(axis, layer) {
    return this.cubies.filter((c) => Math.round(c.position.getComponent(axis)) === layer);
  }

  _start(move) {
    const turn = new LayerTurn(this._slab(move.axis, move.layer), move.axis);
    // Keys mashed faster than the cube can turn play back faster instead of lagging behind.
    const pending = this.queue.reduce((n, item) => n + (item.call ? 0 : 1), 0);
    const catchUp = move.tag === "user" || move.tag === "undo";
    const boost = catchUp ? Math.min(4, 1 + pending * 0.4) : 1;
    const size = Math.abs(move.turns) === 2 ? 1.5 : 1;
    this.active = {
      kind: "anim",
      turn,
      move,
      from: 0,
      to: move.turns * QUARTER,
      t: 0,
      duration: (BASE_TURN_TIME * size * move.timeScale) / (this.speed * boost),
      ease: easeInOutCubic,
    };
  }

  update(dt) {
    const a = this.active;
    if (a && a.kind === "anim") {
      a.t = Math.min(1, a.t + dt / a.duration);
      a.turn.setAngle(a.from + (a.to - a.from) * a.ease(a.t));
      if (a.t === 1) {
        a.turn.commit(a.to);
        this.active = null;
      }
    }

    while (!this.active && this.queue.length) {
      const item = this.queue.shift();
      if (item.call) item.call();
      else this._start(item);
    }

    const busy = this.busy;
    if (this._wasBusy && !busy) this.onIdle?.();
    this._wasBusy = busy;
  }

  // ---- interactive dragging ---------------------------------------------

  beginDrag(axis, layer) {
    if (this.active) return false;
    this.active = { kind: "drag", turn: new LayerTurn(this._slab(axis, layer), axis), layer };
    return true;
  }

  get dragging() {
    return this.active?.kind === "drag";
  }

  get dragAngle() {
    return this.dragging ? this.active.turn.angle : 0;
  }

  setDragAngle(angle) {
    if (this.dragging) this.active.turn.setAngle(angle);
  }

  // Lets go of the dragged slab and animates it onto the nearest quarter turn.
  // Returns the committed move, or null when it settles back where it started.
  endDrag(turns) {
    if (!this.dragging) return null;
    const { turn, layer } = this.active;
    const from = turn.angle;
    const to = turns * QUARTER;
    const distance = Math.abs(to - from) / QUARTER;
    const move = { axis: turn.axisIndex, layer, turns: normTurns(turns) };
    this.active = {
      kind: "anim",
      turn,
      move,
      from,
      to,
      t: 0,
      duration: (0.07 + 0.2 * distance) / this.speed,
      ease: easeOutCubic,
    };
    return move.turns === 0 ? null : move;
  }
}
