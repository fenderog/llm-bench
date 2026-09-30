import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

// ---------- Setup ----------
const canvas = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
camera.position.set(5.2, 4.2, 6.6);

const key = new THREE.DirectionalLight(0xffffff, 1.2);
key.position.set(4, 8, 6);
scene.add(key);

const orbit = (() => {
  // Our pointerdown listener must be registered before OrbitControls' so it can disable it.
  canvas.addEventListener("pointerdown", onPointerDown);
  const c = new OrbitControls(camera, canvas);
  c.enableDamping = true;
  c.enablePan = false;
  c.minDistance = 6;
  c.maxDistance = 20;
  return c;
})();

// Soft blob shadow under the cube
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
    new THREE.PlaneGeometry(7, 7),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false })
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -2.6;
  scene.add(shadow);
}

// ---------- Cube model ----------
const FACES = {
  U: { n: new THREE.Vector3(0, 1, 0), color: 0xffffff },
  D: { n: new THREE.Vector3(0, -1, 0), color: 0xffd500 },
  R: { n: new THREE.Vector3(1, 0, 0), color: 0xc41e3a },
  L: { n: new THREE.Vector3(-1, 0, 0), color: 0xff5800 },
  F: { n: new THREE.Vector3(0, 0, 1), color: 0x009e60 },
  B: { n: new THREE.Vector3(0, 0, -1), color: 0x0051ba },
};

// Move = rotate one layer about a world axis. dir is the right-hand sense about +axis.
// Standard notation: clockwise when looking at that face.
const MOVES = {
  U: { axis: "y", layer: 1, dir: -1 },
  D: { axis: "y", layer: -1, dir: 1 },
  R: { axis: "x", layer: 1, dir: -1 },
  L: { axis: "x", layer: -1, dir: 1 },
  F: { axis: "z", layer: 1, dir: -1 },
  B: { axis: "z", layer: -1, dir: 1 },
};

const bodyGeo = new RoundedBoxGeometry(1, 1, 1, 4, 0.1);
const bodyMat = new THREE.MeshStandardMaterial({ color: 0x0d0d0f, roughness: 0.55, metalness: 0.1 });

function roundedRect(size, r) {
  const h = size / 2;
  const s = new THREE.Shape();
  s.moveTo(-h + r, -h);
  s.lineTo(h - r, -h);
  s.absarc(h - r, -h + r, r, -Math.PI / 2, 0);
  s.lineTo(h, h - r);
  s.absarc(h - r, h - r, r, 0, Math.PI / 2);
  s.lineTo(-h + r, h);
  s.absarc(-h + r, h - r, r, Math.PI / 2, Math.PI);
  s.lineTo(-h, -h + r);
  s.absarc(-h + r, -h + r, r, Math.PI, Math.PI * 1.5);
  return new THREE.ShapeGeometry(s, 6);
}
const stickerGeo = roundedRect(0.86, 0.14);
const stickerMats = {};
for (const [name, f] of Object.entries(FACES)) {
  stickerMats[name] = new THREE.MeshPhysicalMaterial({
    color: f.color, roughness: 0.4, metalness: 0, clearcoat: 0.7, clearcoatRoughness: 0.25,
  });
}

const cube = new THREE.Group();
scene.add(cube);
let cubies = [];

function buildCube() {
  for (const c of cubies) c.parent?.remove(c);
  cubies = [];
  for (let x = -1; x <= 1; x++) {
    for (let y = -1; y <= 1; y++) {
      for (let z = -1; z <= 1; z++) {
        const cubie = new THREE.Group();
        cubie.position.set(x, y, z);
        cubie.add(new THREE.Mesh(bodyGeo, bodyMat));
        for (const [name, f] of Object.entries(FACES)) {
          if (x * f.n.x + y * f.n.y + z * f.n.z !== 1) continue;
          const s = new THREE.Mesh(stickerGeo, stickerMats[name]);
          s.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), f.n);
          s.position.copy(f.n).multiplyScalar(0.502);
          s.userData = { face: name, normal: f.n };
          cubie.add(s);
        }
        cube.add(cubie);
        cubies.push(cubie);
      }
    }
  }
}
buildCube();

// ---------- Move queue & animation ----------
const speedInput = document.getElementById("speed");
const baseDuration = () => 480 - speedInput.value * 4.2; // 480ms .. 60ms
const queue = [];
let current = null; // { move, pivot, group, start, duration }
let history = [];
let moveCount = 0;

const inverse = (m) => ({ ...m, dir: -m.dir });
const sameLayer = (a, b) => a.axis === b.axis && a.layer === b.layer;

function enqueue(move, { record = true, fast = false, user = false } = {}) {
  queue.push({ move, fast, user });
  if (record) {
    const last = history[history.length - 1];
    if (last && sameLayer(last, move) && last.dir === -move.dir) history.pop();
    else history.push(move);
  }
}

function startNext() {
  const item = queue.shift();
  const { move } = item;
  statusEl.textContent = "";
  const pivot = new THREE.Group();
  cube.add(pivot);
  const group = cubies.filter((c) => Math.round(c.position[move.axis]) === move.layer);
  for (const c of group) pivot.attach(c);
  let duration = baseDuration();
  if (item.fast) duration = Math.max(45, duration * 0.4);
  current = { move, pivot, group, start: performance.now(), duration, user: item.user };
}

function snap(cubie) {
  cubie.position.round();
  const m = new THREE.Matrix4().makeRotationFromQuaternion(cubie.quaternion);
  m.elements = m.elements.map((e) => Math.round(e));
  cubie.quaternion.setFromRotationMatrix(m);
}

function finishCurrent() {
  const { move, pivot, group, user } = current;
  pivot.rotation[move.axis] = move.dir * Math.PI / 2;
  pivot.updateMatrixWorld(true);
  for (const c of group) {
    cube.attach(c);
    snap(c);
  }
  cube.remove(pivot);
  if (user) moveCount++;
  current = null;
  updateHud();
}

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

function stepAnimation(now) {
  if (!current && queue.length) startNext();
  if (!current) return;
  const t = Math.min(1, (now - current.start) / current.duration);
  current.pivot.rotation[current.move.axis] = current.move.dir * (Math.PI / 2) * ease(t);
  if (t >= 1) finishCurrent();
}

function isSolved() {
  const seen = {};
  const v = new THREE.Vector3();
  for (const c of cubies) {
    for (const s of c.children) {
      if (!s.userData.face) continue;
      v.copy(s.userData.normal).applyQuaternion(c.quaternion).round();
      const k = `${v.x},${v.y},${v.z}`;
      if (seen[s.userData.face] === undefined) seen[s.userData.face] = k;
      else if (seen[s.userData.face] !== k) return false;
    }
  }
  return true;
}

const movesEl = document.getElementById("moves");
const statusEl = document.getElementById("status");
let scrambled = false;
function updateHud() {
  movesEl.textContent = `${moveCount} move${moveCount === 1 ? "" : "s"}`;
  const busy = current || queue.length;
  if (!busy && scrambled && isSolved()) {
    statusEl.textContent = "Solved!";
    scrambled = false;
  } else if (!isSolved() || busy) {
    statusEl.textContent = "";
  }
}

// ---------- Controls: buttons, keys ----------
const moveButtons = document.getElementById("moveButtons");
for (const prime of [false, true]) {
  for (const name of Object.keys(MOVES)) {
    const b = document.createElement("button");
    b.textContent = name + (prime ? "'" : "");
    b.style.setProperty("--c", "#" + FACES[name].color.toString(16).padStart(6, "0"));
    b.title = `Turn ${name} ${prime ? "counter-" : ""}clockwise`;
    b.addEventListener("click", () => userMove(name, prime));
    moveButtons.appendChild(b);
  }
}

function userMove(name, prime) {
  const m = MOVES[name];
  enqueue(prime ? inverse(m) : m, { user: true });
}

window.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toUpperCase();
  if (MOVES[k] && e.target.tagName !== "INPUT") userMove(k, e.shiftKey);
});

document.getElementById("scramble").addEventListener("click", () => {
  const names = Object.keys(MOVES);
  let lastName = null;
  moveCount = 0;
  for (let i = 0; i < 24; i++) {
    let n;
    do n = names[Math.floor(Math.random() * names.length)];
    while (n === lastName);
    lastName = n;
    const m = MOVES[n];
    enqueue(Math.random() < 0.5 ? m : inverse(m), { fast: true });
  }
  scrambled = true;
  updateHud();
});

document.getElementById("solve").addEventListener("click", () => {
  const undo = history.slice().reverse().map(inverse);
  history = [];
  for (const m of undo) enqueue(m, { record: false, fast: true });
  moveCount = 0;
  updateHud();
});

document.getElementById("reset").addEventListener("click", () => {
  queue.length = 0;
  if (current) {
    current.pivot.parent?.remove(current.pivot);
    current = null;
  }
  history = [];
  moveCount = 0;
  scrambled = false;
  buildCube();
  updateHud();
});

// ---------- Pointer interaction: drag a sticker to turn a layer ----------
const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let drag = null;

function pick(e) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  raycaster.setFromCamera(ndc, camera);
  const hit = raycaster.intersectObjects(cubies, true)[0];
  if (!hit) return null;
  const n = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
  // snap to dominant axis (bevels give diagonal normals)
  const ax = ["x", "y", "z"].sort((a, b) => Math.abs(n[b]) - Math.abs(n[a]))[0];
  const normal = new THREE.Vector3();
  normal[ax] = Math.sign(n[ax]);
  const cubie = hit.object.parent;
  // must be an outward-facing side of the cube
  if (Math.round(cubie.position[ax]) !== normal[ax]) return null;
  return { cubie, normal, point: hit.point.clone() };
}

function onPointerDown(e) {
  if (e.button !== 0 || current || queue.length) {
    if (e.button === 0 && pick(e)) orbit.enabled = false; // block orbiting while busy on the cube
    return;
  }
  const p = pick(e);
  if (!p) return;
  orbit.enabled = false;
  drag = { ...p, x: e.clientX, y: e.clientY, id: e.pointerId };
}

function toScreen(v) {
  const r = canvas.getBoundingClientRect();
  const p = v.clone().project(camera);
  return new THREE.Vector2(((p.x + 1) / 2) * r.width, ((1 - p.y) / 2) * r.height);
}

window.addEventListener("pointermove", (e) => {
  if (!drag) {
    if (e.target === canvas && !e.buttons) canvas.style.cursor = pick(e) ? "grab" : "";
    return;
  }
  const d = new THREE.Vector2(e.clientX - drag.x, e.clientY - drag.y);
  if (d.length() < 14) return;

  const origin = toScreen(drag.point);
  let best = null;
  for (const ax of ["x", "y", "z"]) {
    if (drag.normal[ax] !== 0) continue;
    const t = new THREE.Vector3();
    t[ax] = 1;
    const s = toScreen(drag.point.clone().add(t)).sub(origin);
    const score = d.dot(s) / (s.length() || 1);
    if (!best || Math.abs(score) > Math.abs(best.score)) best = { t, score };
  }
  if (best) {
    const tangent = best.t.multiplyScalar(Math.sign(best.score));
    const a = new THREE.Vector3().crossVectors(drag.normal, tangent); // rotation axis (signed)
    const axis = a.x ? "x" : a.y ? "y" : "z";
    enqueue(
      { axis, layer: Math.round(drag.cubie.position[axis]), dir: Math.sign(a[axis]) },
      { user: true }
    );
  }
  drag = null;
  orbit.enabled = true;
});

function endPointer() {
  drag = null;
  orbit.enabled = true;
}
window.addEventListener("pointerup", endPointer);
window.addEventListener("pointercancel", endPointer);

// ---------- Main loop ----------
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  // keep the cube comfortably in view on narrow screens
  camera.fov = w / h < 0.8 ? 55 : 40;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

renderer.setAnimationLoop(() => {
  stepAnimation(performance.now());
  orbit.update();
  renderer.render(scene, camera);
});
