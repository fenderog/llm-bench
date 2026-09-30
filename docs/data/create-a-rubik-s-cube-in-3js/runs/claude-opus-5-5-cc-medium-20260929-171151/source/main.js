import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";

// ---------- Scene setup ----------
const container = document.getElementById("app");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(6, 5.2, 7.5);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.minDistance = 6;
controls.maxDistance = 20;

scene.add(new THREE.HemisphereLight(0xffffff, 0x404060, 1.4));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
keyLight.position.set(5, 10, 7);
keyLight.castShadow = true;
keyLight.shadow.mapSize.set(1024, 1024);
keyLight.shadow.camera.left = keyLight.shadow.camera.bottom = -4;
keyLight.shadow.camera.right = keyLight.shadow.camera.top = 4;
scene.add(keyLight);
const fill = new THREE.DirectionalLight(0xaabbff, 0.6);
fill.position.set(-6, -3, -5);
scene.add(fill);

const ground = new THREE.Mesh(new THREE.CircleGeometry(6, 64), new THREE.ShadowMaterial({ opacity: 0.3 }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = -2.6;
ground.receiveShadow = true;
scene.add(ground);

// ---------- Cube construction ----------
const SPACING = 1.02;
const COLORS = {
  px: 0xb71234, // right  - red
  nx: 0xff5800, // left   - orange
  py: 0xffffff, // up     - white
  ny: 0xffd500, // down   - yellow
  pz: 0x009b48, // front  - green
  nz: 0x0046ad, // back   - blue
};

const cubeRoot = new THREE.Group();
scene.add(cubeRoot);

const bodyGeo = new RoundedBoxGeometry(1, 1, 1, 4, 0.1);
const bodyMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.6 });

function roundedSquare(size, r) {
  const s = size / 2;
  const shape = new THREE.Shape();
  shape.moveTo(-s + r, -s);
  shape.lineTo(s - r, -s);
  shape.quadraticCurveTo(s, -s, s, -s + r);
  shape.lineTo(s, s - r);
  shape.quadraticCurveTo(s, s, s - r, s);
  shape.lineTo(-s + r, s);
  shape.quadraticCurveTo(-s, s, -s, s - r);
  shape.lineTo(-s, -s + r);
  shape.quadraticCurveTo(-s, -s, -s + r, -s);
  return new THREE.ShapeGeometry(shape, 6);
}
const stickerGeo = roundedSquare(0.84, 0.12);
const stickerMats = {};
for (const [k, c] of Object.entries(COLORS)) {
  stickerMats[k] = new THREE.MeshStandardMaterial({ color: c, roughness: 0.35, metalness: 0.0 });
}

const FACE_DIRS = [
  { key: "px", n: new THREE.Vector3(1, 0, 0) },
  { key: "nx", n: new THREE.Vector3(-1, 0, 0) },
  { key: "py", n: new THREE.Vector3(0, 1, 0) },
  { key: "ny", n: new THREE.Vector3(0, -1, 0) },
  { key: "pz", n: new THREE.Vector3(0, 0, 1) },
  { key: "nz", n: new THREE.Vector3(0, 0, -1) },
];

const cubies = [];
const stickers = [];

function buildCube() {
  for (const c of cubies) cubeRoot.remove(c);
  cubies.length = 0;
  stickers.length = 0;
  for (let x = -1; x <= 1; x++)
    for (let y = -1; y <= 1; y++)
      for (let z = -1; z <= 1; z++) {
        if (x === 0 && y === 0 && z === 0) continue;
        const cubie = new THREE.Group();
        const body = new THREE.Mesh(bodyGeo, bodyMat);
        body.castShadow = true;
        cubie.add(body);
        const pos = [x, y, z];
        for (const f of FACE_DIRS) {
          const axis = f.n.x ? 0 : f.n.y ? 1 : 2;
          if (pos[axis] !== f.n.getComponent(axis)) continue;
          const st = new THREE.Mesh(stickerGeo, stickerMats[f.key]);
          st.position.copy(f.n).multiplyScalar(0.502);
          st.lookAt(f.n.clone().multiplyScalar(2));
          st.userData.color = f.key;
          cubie.add(st);
          stickers.push(st);
        }
        cubie.position.set(x * SPACING, y * SPACING, z * SPACING);
        cubie.userData.coord = new THREE.Vector3(x, y, z);
        cubeRoot.add(cubie);
        cubies.push(cubie);
      }
}
buildCube();

// ---------- Moves ----------
// axis: 0=x 1=y 2=z; layer: -1,0,1; dir: +1 means +90° about the positive axis.
const MOVES = {
  R: { axis: 0, layer: 1, dir: -1 },
  L: { axis: 0, layer: -1, dir: 1 },
  M: { axis: 0, layer: 0, dir: 1 },
  U: { axis: 1, layer: 1, dir: -1 },
  D: { axis: 1, layer: -1, dir: 1 },
  E: { axis: 1, layer: 0, dir: 1 },
  F: { axis: 2, layer: 1, dir: -1 },
  B: { axis: 2, layer: -1, dir: 1 },
  S: { axis: 2, layer: 0, dir: -1 },
};
const AXES = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)];

const queue = [];
let current = null;
const history = [];
let moveCount = 0;
let timerStart = null;
let timerEnd = null;
let awaitingFirstMove = false;

function parseMove(name) {
  const base = MOVES[name[0]];
  const prime = name.endsWith("'");
  return { ...base, dir: prime ? -base.dir : base.dir, name };
}
function invertName(name) {
  return name.endsWith("'") ? name[0] : name + "'";
}

/** Queue a turn. opts.record: push to history; opts.user: counts as player move. */
function enqueue(move, opts = {}) {
  queue.push({ move, record: opts.record ?? true, user: opts.user ?? false, speed: opts.speed ?? 1 });
}

const pivot = new THREE.Object3D();
cubeRoot.add(pivot);

function startNext() {
  const job = queue.shift();
  if (!job) return;
  const { move } = job;
  pivot.rotation.set(0, 0, 0);
  pivot.updateMatrixWorld();
  const layerCubies = cubies.filter((c) => Math.round(c.userData.coord.getComponent(move.axis)) === move.layer);
  for (const c of layerCubies) pivot.attach(c);
  current = { job, cubies: layerCubies, t: 0, duration: 0.22 / job.speed };
}

function finishCurrent() {
  const { job, cubies: layer } = current;
  const { move } = job;
  pivot.rotation.set(0, 0, 0);
  pivot.setRotationFromAxisAngle(AXES[move.axis], (move.dir * Math.PI) / 2);
  pivot.updateMatrixWorld();
  for (const c of layer) {
    cubeRoot.attach(c);
    const coord = c.position.clone().divideScalar(SPACING);
    coord.set(Math.round(coord.x), Math.round(coord.y), Math.round(coord.z));
    c.userData.coord.copy(coord);
    c.position.copy(coord).multiplyScalar(SPACING);
    // Snap rotation to exact multiples of 90°
    const m = new THREE.Matrix4().makeRotationFromQuaternion(c.quaternion);
    m.elements = m.elements.map((v) => Math.round(v));
    c.quaternion.setFromRotationMatrix(m);
  }
  pivot.rotation.set(0, 0, 0);
  if (job.record) history.push(move.name);
  if (job.user) {
    if (awaitingFirstMove) {
      awaitingFirstMove = false;
      timerStart = performance.now();
      timerEnd = null;
    }
    moveCount++;
  }
  current = null;
  updateUI();
  if (queue.length === 0) checkSolved(job.user);
}

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

function updateTurn(dt) {
  if (!current) startNext();
  if (!current) return;
  current.t = Math.min(1, current.t + dt / current.duration);
  const { move } = current.job;
  pivot.setRotationFromAxisAngle(AXES[move.axis], ease(current.t) * move.dir * (Math.PI / 2));
  if (current.t >= 1) finishCurrent();
}

// ---------- Solved check ----------
const banner = document.getElementById("banner");
function isSolved() {
  const seen = new Map();
  const n = new THREE.Vector3();
  cubeRoot.updateMatrixWorld(true);
  for (const st of stickers) {
    n.set(0, 0, 1).transformDirection(st.matrixWorld);
    const key = `${Math.round(n.x)},${Math.round(n.y)},${Math.round(n.z)}`;
    const col = st.userData.color;
    if (!seen.has(key)) seen.set(key, col);
    else if (seen.get(key) !== col) return false;
  }
  return true;
}
function checkSolved(byUser) {
  if (!isSolved()) return;
  history.length = 0;
  if (timerStart !== null && timerEnd === null && byUser) {
    timerEnd = performance.now();
    banner.textContent = `Solved in ${moveCount} moves, ${formatTime(timerEnd - timerStart)}! 🎉`;
    banner.hidden = false;
    setTimeout(() => (banner.hidden = true), 4000);
  }
  awaitingFirstMove = false;
  updateUI();
}

// ---------- UI ----------
const movesEl = document.getElementById("moves");
const timeEl = document.getElementById("time");
const primeBox = document.getElementById("prime");
const btnSolve = document.getElementById("solve");
const btnUndo = document.getElementById("undo");

function formatTime(ms) {
  const s = ms / 1000;
  return `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, "0")}`;
}
function updateUI() {
  movesEl.textContent = moveCount;
  btnSolve.disabled = history.length === 0;
  btnUndo.disabled = history.length === 0;
}
function busy() {
  return current !== null || queue.length > 0;
}

function doUserMove(name) {
  enqueue(parseMove(name), { user: true });
}

document.getElementById("scramble").onclick = () => {
  if (busy()) return;
  banner.hidden = true;
  const faces = "UDLRFB";
  let last = "";
  for (let i = 0; i < 22; i++) {
    let f;
    do f = faces[Math.floor(Math.random() * 6)];
    while (f === last);
    last = f;
    const name = f + (Math.random() < 0.5 ? "'" : "");
    enqueue(parseMove(name), { speed: 2.5 });
    if (Math.random() < 0.25) enqueue(parseMove(name), { speed: 2.5 });
  }
  moveCount = 0;
  timerStart = null;
  timerEnd = null;
  awaitingFirstMove = true;
  updateUI();
};

document.getElementById("solve").onclick = () => {
  if (busy()) return;
  const seq = history.slice().reverse().map(invertName);
  for (const name of seq) enqueue(parseMove(name), { record: false, speed: 2 });
  history.length = 0;
  timerStart = null;
  awaitingFirstMove = false;
  updateUI();
};

function undo() {
  if (busy() || history.length === 0) return;
  const name = history.pop();
  enqueue(parseMove(invertName(name)), { record: false, user: false });
  updateUI();
}
btnUndo.onclick = undo;

document.getElementById("reset").onclick = () => {
  queue.length = 0;
  if (current) {
    for (const c of current.cubies) cubeRoot.attach(c);
    current = null;
  }
  pivot.rotation.set(0, 0, 0);
  buildCube();
  history.length = 0;
  moveCount = 0;
  timerStart = timerEnd = null;
  awaitingFirstMove = false;
  banner.hidden = true;
  updateUI();
};

for (const b of document.querySelectorAll("[data-move]")) {
  b.onclick = () => doUserMove(b.dataset.move + (primeBox.checked ? "'" : ""));
}

window.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
    e.preventDefault();
    undo();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toUpperCase();
  if (MOVES[k]) doUserMove(k + (e.shiftKey ? "'" : ""));
});

// ---------- Drag-to-turn ----------
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let drag = null;

function setPointer(e) {
  const r = renderer.domElement.getBoundingClientRect();
  pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
}
function toScreen(v) {
  const p = v.clone().project(camera);
  return new THREE.Vector2(p.x * window.innerWidth * 0.5, -p.y * window.innerHeight * 0.5);
}
function axisRound(v) {
  const a = [Math.abs(v.x), Math.abs(v.y), Math.abs(v.z)];
  const i = a.indexOf(Math.max(...a));
  const out = new THREE.Vector3();
  out.setComponent(i, Math.sign(v.getComponent(i)));
  return out;
}

renderer.domElement.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  setPointer(e);
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(cubies, true)[0];
  if (!hit) return;
  let cubie = hit.object;
  while (cubie.parent !== cubeRoot && cubie.parent !== pivot) cubie = cubie.parent;
  const normal = axisRound(hit.face.normal.clone().transformDirection(hit.object.matrixWorld));
  controls.enabled = false;
  drag = { cubie, normal, point: hit.point.clone(), start: new THREE.Vector2(e.clientX, e.clientY), done: false };
  renderer.domElement.setPointerCapture(e.pointerId);
});

renderer.domElement.addEventListener("pointermove", (e) => {
  if (!drag || drag.done) return;
  const delta = new THREE.Vector2(e.clientX, e.clientY).sub(drag.start);
  if (delta.length() < 12) return;
  drag.done = true;
  if (busy() && queue.length > 2) return;

  // Candidate world directions tangent to the touched face
  const origin = toScreen(drag.point);
  let best = null;
  let bestDot = -Infinity;
  for (const ax of AXES) {
    if (Math.abs(ax.dot(drag.normal)) > 0.5) continue;
    for (const s of [1, -1]) {
      const d = ax.clone().multiplyScalar(s);
      const sd = toScreen(drag.point.clone().add(d)).sub(origin).normalize();
      const dot = sd.dot(delta.clone().normalize());
      if (dot > bestDot) {
        bestDot = dot;
        best = d;
      }
    }
  }
  // Rotation axis ω satisfies ω × n = drag direction  =>  ω = n × d
  const w = new THREE.Vector3().crossVectors(drag.normal, best);
  const axis = Math.abs(w.x) > 0.5 ? 0 : Math.abs(w.y) > 0.5 ? 1 : 2;
  const dir = Math.sign(w.getComponent(axis));
  const layer = Math.round(drag.cubie.userData.coord.getComponent(axis));
  const name = moveNameFor(axis, layer, dir);
  if (name) doUserMove(name);
});

function moveNameFor(axis, layer, dir) {
  for (const [k, m] of Object.entries(MOVES)) {
    if (m.axis === axis && m.layer === layer) return m.dir === dir ? k : k + "'";
  }
  return null;
}

function endDrag(e) {
  if (!drag) return;
  drag = null;
  controls.enabled = true;
  if (renderer.domElement.hasPointerCapture(e.pointerId)) renderer.domElement.releasePointerCapture(e.pointerId);
}
renderer.domElement.addEventListener("pointerup", endDrag);
renderer.domElement.addEventListener("pointercancel", endDrag);

// ---------- Loop ----------
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
function animate() {
  const dt = Math.min(clock.getDelta(), 0.05);
  updateTurn(dt);
  controls.update();
  if (timerStart !== null) timeEl.textContent = formatTime((timerEnd ?? performance.now()) - timerStart);
  else timeEl.textContent = "0:00.0";
  renderer.render(scene, camera);
}
renderer.setAnimationLoop(animate);
updateUI();
