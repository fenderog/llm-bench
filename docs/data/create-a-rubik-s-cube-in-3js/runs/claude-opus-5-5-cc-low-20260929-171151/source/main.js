import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(devicePixelRatio);
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.1, 100);
camera.position.set(6, 5, 7);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;

scene.add(new THREE.AmbientLight(0xffffff, 1.2));
const dir = new THREE.DirectionalLight(0xffffff, 1.5);
dir.position.set(5, 10, 7);
scene.add(dir);

// Face colors: +x R, -x L, +y U, -y D, +z F, -z B
const COLORS = [0xb71234, 0xff5800, 0xffffff, 0xffd500, 0x009b48, 0x0046ad];
const black = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.6 });
const stickerMats = COLORS.map(c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.35 }));
const bodyGeo = new THREE.BoxGeometry(0.96, 0.96, 0.96);
const stickerGeo = new THREE.PlaneGeometry(0.82, 0.82);
const normals = [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]];

const cubeGroup = new THREE.Group();
scene.add(cubeGroup);
const cubies = [];
for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
  const c = new THREE.Group();
  c.add(new THREE.Mesh(bodyGeo, black));
  normals.forEach((n, i) => {
    if (n[0] && n[0] !== x || n[1] && n[1] !== y || n[2] && n[2] !== z) return;
    const s = new THREE.Mesh(stickerGeo, stickerMats[i]);
    s.position.set(n[0] * 0.481, n[1] * 0.481, n[2] * 0.481);
    s.lookAt(n[0], n[1], n[2]);
    c.add(s);
  });
  c.position.set(x, y, z);
  cubeGroup.add(c);
  cubies.push(c);
}

// Moves: axis, layer, and clockwise direction (as seen facing the face)
const MOVES = {
  R: ["x", 1, -1], L: ["x", -1, 1],
  U: ["y", 1, -1], D: ["y", -1, 1],
  F: ["z", 1, -1], B: ["z", -1, 1],
};

const queue = [];
let active = null;
const history = [];

function enqueue(name, prime, record = true) {
  queue.push({ name, prime });
  if (record) history.push({ name, prime });
}

function startMove({ name, prime }, duration) {
  const [axis, layer, dirSign] = MOVES[name];
  const pivot = new THREE.Group();
  cubeGroup.add(pivot);
  cubies.filter(c => Math.round(c.position[axis]) === layer).forEach(c => pivot.attach(c));
  active = { pivot, axis, angle: (Math.PI / 2) * dirSign * (prime ? -1 : 1), t: 0, duration };
}

function finishMove() {
  const { pivot } = active;
  pivot.rotation[active.axis] = active.angle;
  pivot.updateMatrixWorld();
  [...pivot.children].forEach(c => {
    cubeGroup.attach(c);
    c.position.set(Math.round(c.position.x), Math.round(c.position.y), Math.round(c.position.z));
    const e = c.rotation;
    const q = Math.PI / 2;
    c.rotation.set(Math.round(e.x / q) * q, Math.round(e.y / q) * q, Math.round(e.z / q) * q);
  });
  cubeGroup.remove(pivot);
  active = null;
}

function scramble() {
  const names = Object.keys(MOVES);
  let last = "";
  for (let i = 0; i < 25; i++) {
    let n;
    do n = names[(Math.random() * 6) | 0]; while (n === last);
    last = n;
    enqueue(n, Math.random() < 0.5);
  }
}

function solve() {
  while (history.length) {
    const m = history.pop();
    queue.push({ name: m.name, prime: !m.prime });
  }
}

// UI
const ui = document.getElementById("ui");
const btn = (label, fn) => {
  const b = document.createElement("button");
  b.textContent = label;
  b.onclick = fn;
  ui.appendChild(b);
};
for (const n of Object.keys(MOVES)) {
  btn(n, () => enqueue(n, false));
  btn(n + "'", () => enqueue(n, true));
}
btn("Scramble", scramble);
btn("Solve", solve);

addEventListener("keydown", e => {
  const k = e.key.toUpperCase();
  if (MOVES[k]) enqueue(k, e.shiftKey);
  else if (e.code === "Space") { e.preventDefault(); scramble(); }
});

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  if (!active && queue.length) startMove(queue.shift(), queue.length > 3 ? 0.12 : 0.25);
  if (active) {
    active.t = Math.min(1, active.t + dt / active.duration);
    const s = active.t * active.t * (3 - 2 * active.t);
    active.pivot.rotation[active.axis] = active.angle * s;
    if (active.t >= 1) finishMove();
  }
  controls.update();
  renderer.render(scene, camera);
});
