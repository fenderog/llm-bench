import * as THREE from 'three';
import { SPACING, QUARTER, normalizeTurns } from './cube.js';

const DRAG_THRESHOLD = 7; // px before a press becomes a layer turn
const FLICK_SPEED = 2.5; // rad/s; a quick flick completes the turn even if it was short

/**
 * Lets the user grab any sticker and drag its layer around. Presses that miss the cube fall
 * through to OrbitControls, which is disabled for the duration of a layer drag.
 */
export class DragController {
  constructor(dom, camera, cube, { onTurn, onPress } = {}) {
    this.dom = dom;
    this.camera = camera;
    this.cube = cube;
    this.controls = null;
    this.onTurn = onTurn;
    this.onPress = onPress;
    this.drag = null;
    this.raycaster = new THREE.Raycaster();
    this.ndc = new THREE.Vector2();
    this.box = new THREE.Box3();

    // Capture phase on window runs before OrbitControls' own listener on the canvas.
    window.addEventListener('pointerdown', this.onDown, { capture: true });
    window.addEventListener('pointermove', this.onMove);
    window.addEventListener('pointerup', this.onUp);
    window.addEventListener('pointercancel', this.onUp);
    window.addEventListener('blur', () => this.release());
  }

  get active() {
    return this.drag !== null;
  }

  /** Intersects the cube's bounding box; returns the hit point and the face it lies on. */
  pick(clientX, clientY) {
    const rect = this.dom.getBoundingClientRect();
    this.ndc.set(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
    this.raycaster.setFromCamera(this.ndc, this.camera);
    const h = (this.cube.size * SPACING) / 2 - 0.02;
    this.box.min.setScalar(-h);
    this.box.max.setScalar(h);
    const point = this.raycaster.ray.intersectBox(this.box, new THREE.Vector3());
    if (!point) return null;
    let axis = 0;
    for (let a = 1; a < 3; a++) if (Math.abs(point.getComponent(a)) > Math.abs(point.getComponent(axis))) axis = a;
    return { point, axis, sign: Math.sign(point.getComponent(axis)) || 1 };
  }

  toScreen(v) {
    const rect = this.dom.getBoundingClientRect();
    const p = v.clone().project(this.camera);
    return new THREE.Vector2(((p.x + 1) / 2) * rect.width, ((1 - p.y) / 2) * rect.height);
  }

  onDown = (e) => {
    if (e.target !== this.dom) return;
    this.onPress?.();
    if (this.drag || !e.isPrimary || e.button !== 0 || this.cube.busy) return;
    const hit = this.pick(e.clientX, e.clientY);
    if (!hit) return;
    if (this.controls) this.controls.enabled = false;
    this.drag = {
      id: e.pointerId,
      start: new THREE.Vector2(e.clientX, e.clientY),
      hit,
      rotating: false,
      samples: [{ t: performance.now(), angle: 0 }],
    };
    this.dom.setPointerCapture?.(e.pointerId);
    this.dom.style.cursor = 'grabbing';
  };

  onMove = (e) => {
    const d = this.drag;
    if (!d) {
      if (e.target === this.dom && e.buttons === 0) {
        this.dom.style.cursor = this.pick(e.clientX, e.clientY) ? 'grab' : '';
      }
      return;
    }
    if (e.pointerId !== d.id) return;

    const delta = new THREE.Vector2(e.clientX, e.clientY).sub(d.start);
    if (!d.rotating) {
      if (delta.length() < DRAG_THRESHOLD) return;
      if (this.cube.busy) return this.release();
      this.beginRotation(d, delta);
    }

    // Distance dragged along the chosen direction, converted to world units and then to an
    // angle so the grabbed sticker roughly follows the pointer.
    const along = delta.dot(d.direction) / d.pixelsPerUnit;
    const angle = (along / d.radius) * d.sign;
    this.cube.setTurnAngle(angle);

    const now = performance.now();
    d.samples.push({ t: now, angle });
    while (d.samples.length > 2 && d.samples[0].t < now - 120) d.samples.shift();
  };

  /** Chooses which layer to turn from the face that was grabbed and the initial drag direction. */
  beginRotation(d, delta) {
    const { point, axis: normalAxis, sign: normalSign } = d.hit;
    const origin = this.toScreen(point);

    // Of the two in-plane axes of the grabbed face, pick the one whose on-screen direction best
    // matches the drag.
    let best = null;
    for (let a = 0; a < 3; a++) {
      if (a === normalAxis) continue;
      const moved = point.clone();
      moved.setComponent(a, moved.getComponent(a) + SPACING);
      const v = this.toScreen(moved).sub(origin);
      const length = v.length();
      if (length < 1e-6) continue;
      const alignment = Math.abs(v.dot(delta)) / length;
      if (!best || alignment > best.alignment) best = { axis: a, v, length, alignment };
    }

    // Turning about n × d moves the grabbed point along +d.
    const dragAxis = best.axis;
    const turnAxis = 3 - normalAxis - dragAxis;
    const cyclic = (dragAxis - normalAxis + 3) % 3 === 1;
    const half = (this.cube.size * SPACING) / 2;
    const layer = THREE.MathUtils.clamp(
      Math.floor((point.getComponent(turnAxis) + half) / SPACING),
      0,
      this.cube.size - 1,
    );

    this.cube.beginTurn(turnAxis, [layer]);
    Object.assign(d, {
      rotating: true,
      axis: turnAxis,
      layer,
      sign: normalSign * (cyclic ? 1 : -1),
      direction: best.v.clone().normalize(),
      pixelsPerUnit: best.length / SPACING,
      radius: half,
    });
  }

  onUp = (e) => {
    if (!this.drag || e.pointerId !== this.drag.id) return;
    // Browsers coalesce pointermoves per frame, so fold in the release position for quick flicks.
    if (e.type === 'pointerup') this.onMove(e);
    this.release();
  };

  release() {
    const d = this.drag;
    if (!d) return;
    this.drag = null;
    if (this.controls) this.controls.enabled = true;
    this.dom.style.cursor = '';
    if (!d.rotating || !this.cube.turn) return;

    const angle = this.cube.turn.angle;
    const quarters = angle / QUARTER;
    let turns = Math.round(quarters);

    const now = performance.now();
    const recent = d.samples.filter((s) => s.t >= now - 120);
    if (recent.length >= 2 && Math.abs(quarters) < 1) {
      const first = recent[0];
      const last = recent[recent.length - 1];
      const velocity = (last.angle - first.angle) / Math.max(0.001, (last.t - first.t) / 1000);
      if (Math.abs(velocity) > FLICK_SPEED) {
        turns = Math.sign(velocity) === Math.sign(quarters) ? Math.sign(quarters) : 0;
      }
    }

    this.cube.settleTurn(turns);
    const normalized = normalizeTurns(turns);
    if (normalized !== 0) this.onTurn?.({ axis: d.axis, layers: [d.layer], turns: normalized });
  }
}
