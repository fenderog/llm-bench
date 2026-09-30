import * as THREE from "three";
import { AXES, QUARTER } from "./cube.js";

// Keyboard moves in standard notation. `dir` is the turn (about the positive
// axis) that reads as clockwise when looking at that face from outside.
const KEY_MOVES = {
  U: { axis: 1, layer: 1, dir: -1 },
  D: { axis: 1, layer: -1, dir: 1 },
  R: { axis: 0, layer: 1, dir: -1 },
  L: { axis: 0, layer: -1, dir: 1 },
  F: { axis: 2, layer: 1, dir: -1 },
  B: { axis: 2, layer: -1, dir: 1 },
  M: { axis: 0, layer: 0, dir: 1 },
  E: { axis: 1, layer: 0, dir: 1 },
  S: { axis: 2, layer: 0, dir: -1 },
};

const DRAG_THRESHOLD = 7; // px before a press on the cube turns into a layer drag
const FACE_DISTANCE = 1.2; // world units of drag per radian, so the layer keeps up with the pointer
const FLICK_SPEED = 1.6; // rad/s: faster releases commit to the next quarter turn

export function setupInput({ canvas, camera, controls, cube, game, hud }) {
  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const probe = new THREE.Vector3();
  let gesture = null;

  const pickAt = (e) => {
    const rect = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    return cube.pick(raycaster.ray);
  };

  const toScreen = (point, out) => {
    const rect = canvas.getBoundingClientRect();
    probe.copy(point).project(camera);
    return out.set((probe.x * 0.5 + 0.5) * rect.width, (-probe.y * 0.5 + 0.5) * rect.height);
  };

  // Works out which layer, and which way, a drag that started on `hit` turns.
  // Of the two directions along the face, the one that lines up best with the
  // pointer movement wins; the layer then spins around (face normal x direction).
  const resolveDrag = (hit, dx, dy) => {
    const origin = toScreen(hit.point, new THREE.Vector2());
    const dragLength = Math.hypot(dx, dy);
    let best = null;
    for (let t = 0; t < 3; t++) {
      if (t === hit.axis) continue;
      const s = toScreen(hit.point.clone().add(AXES[t]), new THREE.Vector2()).sub(origin);
      const length = s.length();
      if (length < 1e-3) continue;
      const cos = (s.x * dx + s.y * dy) / (length * dragLength);
      if (!best || Math.abs(cos) > Math.abs(best.cos)) best = { t, s, length, cos };
    }
    if (!best) return null;

    const along = Math.sign(best.cos) || 1;
    const normal = AXES[hit.axis].clone().multiplyScalar(hit.sign);
    const direction = AXES[best.t].clone().multiplyScalar(along);
    const spin = normal.cross(direction); // signed unit axis the layer turns around
    const axis = [spin.x, spin.y, spin.z].findIndex((v) => Math.abs(v) > 0.5);
    return {
      axis,
      layer: hit.cell[axis],
      sign: spin.getComponent(axis),
      // pointer pixels -> angle of the layer, positive when moving along `direction`
      dirX: (best.s.x / best.length) * along,
      dirY: (best.s.y / best.length) * along,
      radiansPerPixel: 1 / (best.length * FACE_DISTANCE),
    };
  };

  const releaseGesture = (cancelled) => {
    const g = gesture;
    gesture = null;
    controls.enabled = true;
    canvas.style.cursor = "";
    if (canvas.hasPointerCapture(g.pointerId)) canvas.releasePointerCapture(g.pointerId);
    if (g.state !== "dragging") return;

    // g.angle is the layer's angle about its positive axis; snap it to a quarter turn,
    // or commit to the next one when the pointer was let go with a quick flick.
    let turns = Math.round(g.angle / QUARTER);
    const flick = g.velocity();
    if (!cancelled && turns === 0 && Math.abs(g.angle) > 0.1 && Math.abs(flick) > FLICK_SPEED) {
      if (Math.sign(flick) === Math.sign(g.angle)) turns = Math.sign(g.angle);
    }
    const move = cube.endDrag(turns);
    if (move) game.userMove(move, false);
  };

  canvas.addEventListener(
    "pointerdown",
    (e) => {
      hud.hideHint();
      if (gesture) {
        // A second finger means pinch / orbit: drop the layer drag, let the controls take over.
        if (e.pointerId !== gesture.pointerId) releaseGesture(true);
        return;
      }
      if (e.button !== 0 || !e.isPrimary) return;

      const hit = pickAt(e);
      if (!hit) return;

      controls.enabled = false; // this press belongs to the cube, not the camera
      const samples = [];
      gesture = {
        pointerId: e.pointerId,
        hit,
        x0: e.clientX,
        y0: e.clientY,
        state: game.canInteract && !cube.busy ? "pending" : "blocked",
        angle: 0,
        velocity() {
          const now = performance.now();
          const recent = samples.filter((s) => now - s.t < 90);
          if (recent.length < 2) return 0;
          const first = recent[0];
          const last = recent[recent.length - 1];
          return last.t > first.t ? ((last.angle - first.angle) / (last.t - first.t)) * 1000 : 0;
        },
        sample(angle) {
          samples.push({ t: performance.now(), angle });
          if (samples.length > 12) samples.shift();
        },
      };
      canvas.setPointerCapture(e.pointerId);
      canvas.style.cursor = "grabbing";
    },
    { capture: true },
  );

  canvas.addEventListener("pointermove", (e) => {
    if (!gesture) {
      if (e.pointerType === "mouse" && e.buttons === 0) canvas.style.cursor = pickAt(e) ? "grab" : "";
      return;
    }
    if (e.pointerId !== gesture.pointerId || gesture.state === "blocked") return;

    const dx = e.clientX - gesture.x0;
    const dy = e.clientY - gesture.y0;

    if (gesture.state === "pending") {
      if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
      const drag = resolveDrag(gesture.hit, dx, dy);
      if (!drag || !cube.beginDrag(drag.axis, drag.layer)) {
        gesture.state = "blocked";
        return;
      }
      Object.assign(gesture, drag, { state: "dragging" });
    }

    const pixels = dx * gesture.dirX + dy * gesture.dirY;
    const along = THREE.MathUtils.clamp(pixels * gesture.radiansPerPixel, -Math.PI, Math.PI);
    gesture.angle = along * gesture.sign;
    gesture.sample(gesture.angle);
    cube.setDragAngle(gesture.angle);
  });

  const onEnd = (cancelled) => (e) => {
    if (gesture && e.pointerId === gesture.pointerId) releaseGesture(cancelled);
  };
  canvas.addEventListener("pointerup", onEnd(false));
  canvas.addEventListener("pointercancel", onEnd(true));

  // ---- keyboard ------------------------------------------------------------

  window.addEventListener("keydown", (e) => {
    if (e.altKey || e.metaKey) return;
    const key = e.key.toUpperCase();

    if (e.ctrlKey) {
      if (key === "Z") {
        e.preventDefault();
        game.undo();
      }
      return;
    }
    if (e.repeat) return;

    if (key === "BACKSPACE") {
      e.preventDefault();
      game.undo();
    } else if (key === "?") {
      hud.toggleHelp();
    } else if (KEY_MOVES[key]) {
      e.preventDefault();
      hud.hideHint();
      if (!game.canInteract) return;
      const { axis, layer, dir } = KEY_MOVES[key];
      game.userMove({ axis, layer, turns: e.shiftKey ? -dir : dir });
    }
  });
}
