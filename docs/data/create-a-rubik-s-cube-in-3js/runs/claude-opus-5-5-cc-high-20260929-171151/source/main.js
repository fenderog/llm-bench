import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

// ---------------------------------------------------------------------------
// Renderer, scene, camera
// ---------------------------------------------------------------------------

const app = document.getElementById("app");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 0.95;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 100);
const DEFAULT_CAMERA = new THREE.Vector3(6.1, 5, 7.9);
camera.position.copy(DEFAULT_CAMERA);

const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
keyLight.position.set(5, 8, 6);
scene.add(keyLight);
scene.add(new THREE.AmbientLight(0xffffff, 0.25));

// Soft blob shadow under the cube, generated from a canvas gradient.
{
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, "rgba(0,0,0,0.55)");
  grad.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  const shadow = new THREE.Mesh(
    new THREE.PlaneGeometry(6, 6),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false })
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -2.6;
  scene.add(shadow);
}

// ---------------------------------------------------------------------------
// Cube construction
// ---------------------------------------------------------------------------

const CUBIE_SIZE = 0.94;
const STICKER_SIZE = 0.78;

const FACES = [
  { normal: new THREE.Vector3(1, 0, 0), color: 0xc41e3a }, // R red
  { normal: new THREE.Vector3(-1, 0, 0), color: 0xff6a00 }, // L orange
  { normal: new THREE.Vector3(0, 1, 0), color: 0xf4f4f4 }, // U white
  { normal: new THREE.Vector3(0, -1, 0), color: 0xffd500 }, // D yellow
  { normal: new THREE.Vector3(0, 0, 1), color: 0x009e60 }, // F green
  { normal: new THREE.Vector3(0, 0, -1), color: 0x0051ba }, // B blue
];

function roundedRectShape(size, radius) {
  const h = size / 2;
  const s = new THREE.Shape();
  s.moveTo(-h + radius, -h);
  s.lineTo(h - radius, -h);
  s.quadraticCurveTo(h, -h, h, -h + radius);
  s.lineTo(h, h - radius);
  s.quadraticCurveTo(h, h, h - radius, h);
  s.lineTo(-h + radius, h);
  s.quadraticCurveTo(-h, h, -h, h - radius);
  s.lineTo(-h, -h + radius);
  s.quadraticCurveTo(-h, -h, -h + radius, -h);
  return s;
}

const bodyGeometry = new RoundedBoxGeometry(CUBIE_SIZE, CUBIE_SIZE, CUBIE_SIZE, 3, 0.08);
const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x0c0c0e, roughness: 0.45, metalness: 0.1 });
const stickerGeometry = new THREE.ShapeGeometry(roundedRectShape(STICKER_SIZE, 0.09), 4);
const stickerMaterials = new Map(
  FACES.map((f) => [f.color, new THREE.MeshStandardMaterial({ color: f.color, roughness: 0.3, metalness: 0 })])
);

const cubeGroup = new THREE.Group();
scene.add(cubeGroup);
const pivot = new THREE.Object3D();
cubeGroup.add(pivot);

const cubies = [];
const stickers = [];
const Z_AXIS = new THREE.Vector3(0, 0, 1);

for (let x = -1; x <= 1; x++) {
  for (let y = -1; y <= 1; y++) {
    for (let z = -1; z <= 1; z++) {
      if (x === 0 && y === 0 && z === 0) continue;
      const cubie = new THREE.Group();
      cubie.position.set(x, y, z);
      cubie.userData.home = cubie.position.clone();
      cubie.add(new THREE.Mesh(bodyGeometry, bodyMaterial));

      for (const face of FACES) {
        if (face.normal.dot(cubie.position) !== 1) continue;
        const sticker = new THREE.Mesh(stickerGeometry, stickerMaterials.get(face.color));
        sticker.quaternion.setFromUnitVectors(Z_AXIS, face.normal);
        sticker.position.copy(face.normal).multiplyScalar(CUBIE_SIZE / 2 + 0.004);
        sticker.userData = { color: face.color, normal: face.normal };
        cubie.add(sticker);
        stickers.push(sticker);
      }
      cubeGroup.add(cubie);
      cubies.push(cubie);
    }
  }
}

// ---------------------------------------------------------------------------
// Move model
// ---------------------------------------------------------------------------
// A move is { axis: 'x'|'y'|'z', layers: number[], turns: int } where `turns`
// counts quarter turns in the positive (right-handed) direction about the axis.

const ALL = [-1, 0, 1];
const HALF_PI = Math.PI / 2;

// `sign` is the direction of a clockwise turn (seen from the face) about the positive axis.
const MOVE_DEFS = {
  R: { axis: "x", layers: [1], sign: -1 },
  L: { axis: "x", layers: [-1], sign: 1 },
  U: { axis: "y", layers: [1], sign: -1 },
  D: { axis: "y", layers: [-1], sign: 1 },
  F: { axis: "z", layers: [1], sign: -1 },
  B: { axis: "z", layers: [-1], sign: 1 },
  M: { axis: "x", layers: [0], sign: 1 },
  E: { axis: "y", layers: [0], sign: 1 },
  S: { axis: "z", layers: [0], sign: -1 },
  x: { axis: "x", layers: ALL, sign: -1 },
  y: { axis: "y", layers: ALL, sign: -1 },
  z: { axis: "z", layers: ALL, sign: -1 },
};
const FACE_NAMES = ["U", "D", "L", "R", "F", "B"];

const sameLayers = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
const normTurns = (t) => {
  const m = ((t % 4) + 4) % 4;
  return m === 3 ? -1 : m;
};
const isRotation = (move) => move.layers.length === 3;

function makeMove(name, prime = false, double = false) {
  const def = MOVE_DEFS[name];
  return { axis: def.axis, layers: def.layers.slice(), turns: def.sign * (double ? 2 : 1) * (prime ? -1 : 1) };
}

function invert(move) {
  return { ...move, turns: -move.turns };
}

function notation(move) {
  for (const [name, def] of Object.entries(MOVE_DEFS)) {
    if (def.axis !== move.axis || !sameLayers(def.layers, move.layers)) continue;
    const q = ((move.turns * def.sign) % 4 + 4) % 4;
    return q === 1 ? name : q === 2 ? name + "2" : q === 3 ? name + "'" : "";
  }
  return "?";
}

// ---------------------------------------------------------------------------
// Layer rotation mechanics
// ---------------------------------------------------------------------------

function selectLayers(axis, layers) {
  return cubies.filter((c) => layers.includes(Math.round(c.position[axis])));
}

function attachToPivot(list) {
  pivot.rotation.set(0, 0, 0);
  pivot.updateMatrixWorld(true);
  for (const c of list) pivot.attach(c);
}

const snapMatrix = new THREE.Matrix4();
function releasePivot(list) {
  pivot.updateMatrixWorld(true);
  for (const c of list) {
    cubeGroup.attach(c);
    c.position.set(Math.round(c.position.x), Math.round(c.position.y), Math.round(c.position.z));
    snapMatrix.makeRotationFromQuaternion(c.quaternion);
    const e = snapMatrix.elements;
    for (let i = 0; i < 16; i++) e[i] = Math.round(e[i]);
    c.quaternion.setFromRotationMatrix(snapMatrix);
  }
  pivot.rotation.set(0, 0, 0);
}

const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);

// ---------------------------------------------------------------------------
// Game state
// ---------------------------------------------------------------------------

const queue = []; // pending { move, kind, fast }
let active = null; // animation in progress
let drag = null; // pointer drag in progress
let history = []; // merged moves since the solved state (for undo / solve)
let log = []; // human readable recent moves
let moveCount = 0;
let timerArmed = false;
let timerStart = 0;
let timerEnd = 0;
let timerRunning = false;
let scramblePending = 0;

function speedFactor() {
  // slider 0..1 -> duration multiplier 1.8..0.35
  const v = parseFloat(speedInput.value);
  return 1.8 - v * 1.45;
}

function enqueue(move, kind = "user", fast = false) {
  queue.push({ move, kind, fast });
}

function startNext() {
  const item = queue.shift();
  const { move } = item;
  const list = selectLayers(move.axis, move.layers);
  attachToPivot(list);
  const base = 260 * speedFactor() * (Math.abs(move.turns) === 2 ? 1.5 : 1) * (item.fast ? 0.45 : 1);
  active = {
    axis: move.axis,
    cubies: list,
    from: 0,
    to: move.turns * HALF_PI,
    start: performance.now(),
    duration: Math.max(40, base),
    ease: easeInOut,
    onDone: () => onMoveDone(move, item.kind),
  };
}

function onMoveDone(move, kind) {
  // Undo/solve moves are inverses, so they cancel entries off the end of the history.
  pushHistory(move);
  const label = notation(move);
  if (label) {
    log.push(label);
    if (log.length > 14) log.shift();
  }

  if (kind === "scramble") {
    scramblePending--;
    if (scramblePending === 0) timerArmed = true;
  } else if (kind === "user" && !isRotation(move)) {
    moveCount++;
    if (timerArmed && !timerRunning) {
      timerRunning = true;
      timerStart = performance.now();
      timerEnd = 0;
    }
  }
  checkSolved();
  updateUI();
}

function pushHistory(move) {
  const last = history[history.length - 1];
  if (last && last.axis === move.axis && sameLayers(last.layers, move.layers)) {
    last.turns = normTurns(last.turns + move.turns);
    if (last.turns === 0) history.pop();
  } else {
    history.push({ axis: move.axis, layers: move.layers.slice(), turns: normTurns(move.turns) });
  }
}

const tmpNormal = new THREE.Vector3();
function isSolved() {
  const seen = {};
  for (const s of stickers) {
    tmpNormal.copy(s.userData.normal).applyQuaternion(s.parent.quaternion);
    const key = `${Math.round(tmpNormal.x)},${Math.round(tmpNormal.y)},${Math.round(tmpNormal.z)}`;
    if (seen[key] === undefined) seen[key] = s.userData.color;
    else if (seen[key] !== s.userData.color) return false;
  }
  return true;
}

function checkSolved() {
  if (queue.length || active) return;
  if (!isSolved()) return;
  history = [];
  if (timerRunning) {
    timerRunning = false;
    timerEnd = performance.now();
    timerArmed = false;
    showToast("Solved! 🎉", `${moveCount} moves in ${formatTime(timerEnd - timerStart)}`);
  }
  timerArmed = false;
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function scramble() {
  if (drag) return;
  queue.length = 0;
  const axisOf = (f) => MOVE_DEFS[f].axis;
  let prevAxis = null;
  const n = 25;
  for (let i = 0; i < n; i++) {
    let face;
    do face = FACE_NAMES[Math.floor(Math.random() * 6)];
    while (axisOf(face) === prevAxis);
    prevAxis = axisOf(face);
    const r = Math.random();
    enqueue(makeMove(face, r < 0.4, r > 0.8), "scramble", true);
  }
  scramblePending = n;
  moveCount = 0;
  timerRunning = false;
  timerArmed = false;
  timerStart = timerEnd = 0;
  log = [];
  hideToast();
  updateUI();
}

function solve() {
  if (drag) return;
  queue.length = 0;
  scramblePending = 0;
  const moves = history.slice().reverse().map(invert);
  timerRunning = false;
  timerArmed = false;
  for (const m of moves) enqueue(m, "solve", true);
  updateUI();
}

function undo() {
  if (drag) return;
  // Undo the most recent queued-but-not-started user move first.
  for (let i = queue.length - 1; i >= 0; i--) {
    if (queue[i].kind === "user") {
      queue.splice(i, 1);
      return;
    }
  }
  if (active || queue.length) return;
  const last = history[history.length - 1];
  // The inverse merges with (and cancels) the last history entry when it completes.
  if (last) enqueue(invert(last), "undo");
}

function reset() {
  queue.length = 0;
  if (active) {
    releasePivot(active.cubies);
    active = null;
  }
  if (drag && drag.locked) releasePivot(drag.locked.list);
  drag = null;
  controls.enabled = true;
  for (const c of cubies) {
    c.position.copy(c.userData.home);
    c.quaternion.identity();
  }
  history = [];
  log = [];
  moveCount = 0;
  scramblePending = 0;
  timerArmed = timerRunning = false;
  timerStart = timerEnd = 0;
  hideToast();
  updateUI();
}

// ---------------------------------------------------------------------------
// UI
// ---------------------------------------------------------------------------

const movesEl = document.getElementById("moves");
const timeEl = document.getElementById("time");
const stateEl = document.getElementById("state");
const logEl = document.getElementById("log");
const toastEl = document.getElementById("toast");
const speedInput = document.getElementById("speed");

function formatTime(ms) {
  const s = ms / 1000;
  const m = Math.floor(s / 60);
  const rest = (s - m * 60).toFixed(1).padStart(4, "0");
  return `${m}:${rest}`;
}

function updateUI() {
  movesEl.textContent = moveCount;
  logEl.textContent = log.join(" ");
  const busy = active || queue.length;
  if (scramblePending > 0) stateEl.textContent = "Scrambling…";
  else if (busy && queue.some((q) => q.kind === "solve")) stateEl.textContent = "Solving…";
  else if (!busy && !drag && isSolved()) stateEl.textContent = "Solved";
  else if (timerRunning) stateEl.textContent = "Solving";
  else if (timerArmed) stateEl.textContent = "Ready";
  else stateEl.textContent = "Scrambled";
}

function updateTimer(now) {
  let ms = 0;
  if (timerRunning) ms = now - timerStart;
  else if (timerEnd) ms = timerEnd - timerStart;
  timeEl.textContent = formatTime(ms);
}

let toastTimeout = 0;
function showToast(title, sub) {
  toastEl.innerHTML = "";
  toastEl.append(title);
  const small = document.createElement("small");
  small.textContent = sub;
  toastEl.append(small);
  toastEl.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(hideToast, 4000);
}
function hideToast() {
  toastEl.classList.remove("show");
}

const pad = document.getElementById("pad");
for (const face of FACE_NAMES) {
  for (const prime of [false, true]) {
    const b = document.createElement("button");
    b.textContent = face + (prime ? "'" : "");
    b.title = `${face}${prime ? "'" : ""} (${prime ? "Shift+" : ""}${face})`;
    b.addEventListener("click", () => enqueue(makeMove(face, prime)));
    pad.appendChild(b);
  }
}

document.getElementById("scramble").addEventListener("click", scramble);
document.getElementById("solve").addEventListener("click", solve);
document.getElementById("undo").addEventListener("click", undo);
document.getElementById("reset").addEventListener("click", reset);
document.getElementById("view").addEventListener("click", () => {
  viewTween = { from: camera.position.clone(), start: performance.now() };
});
const helpEl = document.getElementById("help");
helpEl.querySelector(".head").addEventListener("click", () => {
  helpEl.classList.toggle("collapsed");
  document.getElementById("helpToggle").textContent = helpEl.classList.contains("collapsed") ? "+" : "–";
});
// Keep buttons from stealing keyboard focus (so Space doesn't re-click them).
for (const b of document.querySelectorAll("button")) b.addEventListener("mousedown", (e) => e.preventDefault());

const KEY_TO_MOVE = {
  KeyU: "U", KeyD: "D", KeyL: "L", KeyR: "R", KeyF: "F", KeyB: "B",
  KeyM: "M", KeyE: "E", KeyS: "S", KeyX: "x", KeyY: "y", KeyZ: "z",
};

window.addEventListener("keydown", (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.target instanceof HTMLInputElement) return;
  const name = KEY_TO_MOVE[e.code];
  if (name) {
    e.preventDefault();
    enqueue(makeMove(name, e.shiftKey));
  } else if (e.code === "Backspace") {
    e.preventDefault();
    undo();
  } else if (e.code === "Space") {
    e.preventDefault();
    scramble();
  }
});

// ---------------------------------------------------------------------------
// Pointer interaction: drag a face to turn its layer
// ---------------------------------------------------------------------------

const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
const canvas = renderer.domElement;
const AXES = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };

function dominantAxis(v) {
  const ax = Math.abs(v.x), ay = Math.abs(v.y), az = Math.abs(v.z);
  return ax >= ay && ax >= az ? "x" : ay >= az ? "y" : "z";
}

function toScreen(localPoint) {
  const v = cubeGroup.localToWorld(localPoint.clone()).project(camera);
  const rect = canvas.getBoundingClientRect();
  return new THREE.Vector2(((v.x + 1) / 2) * rect.width, ((1 - v.y) / 2) * rect.height);
}

// Registered before OrbitControls so we can disable it when a drag starts on the cube.
canvas.addEventListener(
  "pointerdown",
  (e) => {
    if (drag || (e.pointerType === "mouse" && e.button !== 0)) return;
    const rect = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    const hit = raycaster.intersectObjects(cubies, true)[0];
    if (!hit) return;

    controls.enabled = false;
    canvas.setPointerCapture(e.pointerId);
    if (active || queue.length) {
      drag = { pointerId: e.pointerId, blocked: true };
      return;
    }
    const point = cubeGroup.worldToLocal(hit.point.clone());
    const normalAxis = dominantAxis(point);
    const normal = new THREE.Vector3();
    normal[normalAxis] = Math.sign(point[normalAxis]);
    let cubie = hit.object;
    while (cubie.parent !== cubeGroup) cubie = cubie.parent;
    drag = { pointerId: e.pointerId, startX: e.clientX, startY: e.clientY, point, normal, normalAxis, cubie, locked: null };
  },
  { capture: true }
);

canvas.addEventListener("pointermove", (e) => {
  if (!drag || drag.blocked || e.pointerId !== drag.pointerId) return;
  const dx = e.clientX - drag.startX;
  const dy = e.clientY - drag.startY;

  if (!drag.locked) {
    if (Math.hypot(dx, dy) < 8) return;
    // Pick the in-face direction whose on-screen projection best matches the drag.
    const origin = toScreen(drag.point);
    let best = null;
    for (const ax of ["x", "y", "z"]) {
      if (ax === drag.normalAxis) continue;
      const s = toScreen(drag.point.clone().add(AXES[ax])).sub(origin);
      const len = s.length();
      if (len < 1e-3) continue;
      const score = Math.abs((dx * s.x + dy * s.y) / len);
      if (!best || score > best.score) best = { ax, s, score };
    }
    if (!best) return;
    // Turning about (normal × dir) by a positive angle moves the grabbed point along +dir.
    const rot = new THREE.Vector3().crossVectors(drag.normal, AXES[best.ax]);
    const rotAxis = dominantAxis(rot);
    const layer = Math.round(drag.cubie.position[rotAxis]);
    const list = selectLayers(rotAxis, [layer]);
    attachToPivot(list);
    drag.locked = {
      rotAxis,
      sign: Math.sign(rot[rotAxis]),
      s: best.s,
      layer,
      list,
      angle: 0,
      velocity: 0,
      lastAngle: 0,
      lastTime: performance.now(),
    };
  }

  const L = drag.locked;
  const units = (dx * L.s.x + dy * L.s.y) / L.s.lengthSq();
  L.angle = (L.sign * units) / 1.4;
  pivot.rotation.set(0, 0, 0);
  pivot.rotation[L.rotAxis] = L.angle;

  const now = performance.now();
  const dt = now - L.lastTime;
  if (dt > 0) {
    const v = (L.angle - L.lastAngle) / dt;
    L.velocity = L.velocity * 0.6 + v * 0.4;
    L.lastAngle = L.angle;
    L.lastTime = now;
  }
});

function endDrag(e) {
  if (!drag || e.pointerId !== drag.pointerId) return;
  const d = drag;
  drag = null;
  controls.enabled = true;
  if (canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
  if (d.blocked || !d.locked) return;

  const L = d.locked;
  const q = L.angle / HALF_PI;
  let turns = Math.round(q);
  // A quick flick commits to the next quarter turn in the flick direction.
  const recent = performance.now() - L.lastTime < 80;
  if (recent && Math.abs(L.velocity) > 0.004) {
    turns = L.velocity > 0 ? Math.ceil(q - 0.05) : Math.floor(q + 0.05);
  }
  const to = turns * HALF_PI;
  const move = { axis: L.rotAxis, layers: [L.layer], turns };
  active = {
    axis: L.rotAxis,
    cubies: L.list,
    from: L.angle,
    to,
    start: performance.now(),
    duration: Math.max(60, 220 * Math.min(1, Math.abs(to - L.angle) / HALF_PI + 0.2)),
    ease: easeOut,
    onDone: () => {
      if (normTurns(turns) !== 0) onMoveDone(move, "user");
      else updateUI();
    },
  };
}
canvas.addEventListener("pointerup", endDrag);
canvas.addEventListener("pointercancel", endDrag);

const controls = new OrbitControls(camera, canvas);
controls.enablePan = false;
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 6;
controls.maxDistance = 18;
controls.rotateSpeed = 0.8;

// ---------------------------------------------------------------------------
// Main loop
// ---------------------------------------------------------------------------

let viewTween = null;

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

renderer.setAnimationLoop((now) => {
  if (!active && !drag && queue.length) startNext();

  if (active) {
    const t = Math.min(1, (now - active.start) / active.duration);
    pivot.rotation.set(0, 0, 0);
    pivot.rotation[active.axis] = active.from + (active.to - active.from) * active.ease(t);
    if (t >= 1) {
      releasePivot(active.cubies);
      const done = active;
      active = null;
      done.onDone();
    }
  }

  if (viewTween) {
    const t = Math.min(1, (now - viewTween.start) / 600);
    camera.position.lerpVectors(viewTween.from, DEFAULT_CAMERA, easeInOut(t));
    if (t >= 1) viewTween = null;
  }

  controls.update();
  updateTimer(now);
  renderer.render(scene, camera);
});

updateUI();
