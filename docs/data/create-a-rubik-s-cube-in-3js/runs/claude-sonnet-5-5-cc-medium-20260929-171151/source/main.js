import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
document.body.prepend(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1b1f2a);
const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
camera.position.set(5.5, 5, 7.5);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enablePan = false; controls.enableDamping = true;
controls.minDistance = 6; controls.maxDistance = 20;
scene.add(new THREE.AmbientLight(0xffffff, 1.4));
const dl = new THREE.DirectionalLight(0xffffff, 2.2); dl.position.set(4, 8, 6); scene.add(dl);

const COLORS = { px: 0xb71234, nx: 0xff5800, py: 0xffffff, ny: 0xffd500, pz: 0x009b48, nz: 0x0046ad };
const DIRS = { px: [1,0,0], nx: [-1,0,0], py: [0,1,0], ny: [0,-1,0], pz: [0,0,1], nz: [0,0,-1] };
const bodyGeo = new THREE.BoxGeometry(0.97, 0.97, 0.97);
const bodyMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.6 });
const stickerGeo = new THREE.PlaneGeometry(0.98 * 0.86, 0.98 * 0.86);
const stickerMats = {};
for (const k in COLORS) stickerMats[k] = new THREE.MeshStandardMaterial({ color: COLORS[k], roughness: 0.35 });

const cube = new THREE.Group(); scene.add(cube);
const cubies = [];
function build() {
  cubies.forEach(c => cube.remove(c)); cubies.length = 0;
  for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(bodyGeo, bodyMat));
    for (const k in DIRS) {
      const d = DIRS[k];
      if (d[0] * x + d[1] * y + d[2] * z !== 1) continue;
      const s = new THREE.Mesh(stickerGeo, stickerMats[k]);
      s.position.set(d[0] * 0.486, d[1] * 0.486, d[2] * 0.486);
      s.lookAt(s.position.clone().multiplyScalar(2));
      g.add(s);
    }
    g.position.set(x, y, z);
    cube.add(g); cubies.push(g);
  }
}
build();

// --- move engine ---
const queue = []; let current = null;
const pivot = new THREE.Group(); cube.add(pivot);
const ease = t => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
let speed = 260;

function enqueue(axis, layer, angle, fast) { queue.push({ axis, layer, angle, fast }); }
function startNext() {
  const m = queue.shift(); if (!m) return;
  const ax = "xyz".indexOf(m.axis);
  pivot.rotation.set(0, 0, 0);
  const sel = cubies.filter(c => Math.round(c.position.getComponent(ax)) === m.layer || m.layer === 9);
  sel.forEach(c => pivot.attach(c));
  current = { m, sel, t0: performance.now(), dur: m.fast ? 70 : speed * Math.max(0.5, Math.abs(m.angle) / (Math.PI / 2)), vec: new THREE.Vector3(...DIRS["p" + m.axis]) };
}
function finish() {
  const { sel } = current;
  sel.forEach(c => {
    cube.attach(c);
    c.position.set(Math.round(c.position.x), Math.round(c.position.y), Math.round(c.position.z));
    const m = new THREE.Matrix4().makeRotationFromQuaternion(c.quaternion);
    for (let i = 0; i < 16; i++) m.elements[i] = Math.round(m.elements[i]);
    c.quaternion.setFromRotationMatrix(m);
  });
  pivot.rotation.set(0, 0, 0);
  current = null;
}
function update(now) {
  if (!current && queue.length) startNext();
  if (!current) return;
  const t = Math.min(1, (now - current.t0) / current.dur);
  pivot.setRotationFromAxisAngle(current.vec, current.m.angle * ease(t));
  if (t >= 1) finish();
}

// notation: [axis, layer, sign of clockwise quarter turn]
const FACES = { R: ["x", 1, -1], L: ["x", -1, 1], U: ["y", 1, -1], D: ["y", -1, 1], F: ["z", 1, -1], B: ["z", -1, 1] };
function move(str, fast) {
  const f = FACES[str[0]]; const q = str.endsWith("'") ? -1 : 1, n = str.endsWith("2") ? 2 : 1;
  enqueue(f[0], f[1], f[2] * q * n * Math.PI / 2, fast);
}
function scramble() {
  const keys = Object.keys(FACES); let last = "";
  for (let i = 0; i < 22; i++) {
    let k; do { k = keys[Math.floor(Math.random() * 6)]; } while (k === last); last = k;
    move(k + ["", "'", "2"][Math.floor(Math.random() * 3)], true);
  }
}

// --- UI ---
const ui = document.getElementById("ui");
function btn(label, fn) { const b = document.createElement("button"); b.textContent = label; b.onclick = fn; ui.appendChild(b); }
for (const f of "RLUDFB") { btn(f, () => move(f)); btn(f + "'", () => move(f + "'")); }
btn("Scramble", scramble);
btn("Reset", () => { queue.length = 0; if (current) finish(); build(); });

// --- drag to turn ---
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
let drag = null;
const el = renderer.domElement;
function setNdc(e) { const r = el.getBoundingClientRect(); ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); }
el.addEventListener("pointerdown", e => {
  if (current || queue.length) return;
  setNdc(e); ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(cubies, true)[0];
  if (!hit) return;
  const n = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
  const nn = new THREE.Vector3(Math.round(n.x), Math.round(n.y), Math.round(n.z));
  let owner = hit.object; while (owner.parent !== cube) owner = owner.parent;
  controls.enabled = false;
  drag = { x: e.clientX, y: e.clientY, n: nn, p: owner.position.clone(), id: e.pointerId };
  el.setPointerCapture(e.pointerId);
});
function screenDir(p, t) {
  const a = p.clone().project(camera), b = p.clone().add(t).project(camera);
  return new THREE.Vector2(b.x - a.x, -(b.y - a.y) * 1).normalize();
}
el.addEventListener("pointermove", e => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.hypot(dx, dy) < 14) return;
  const d = new THREE.Vector2(dx, -dy).normalize();
  let best = null, bs = 0;
  for (const t of [new THREE.Vector3(1,0,0), new THREE.Vector3(0,1,0), new THREE.Vector3(0,0,1)]) {
    if (Math.abs(t.dot(drag.n)) > 0.5) continue;
    for (const s of [1, -1]) {
      const tt = t.clone().multiplyScalar(s);
      const sc = screenDir(drag.p, tt).dot(d);
      if (sc > bs) { bs = sc; best = tt; }
    }
  }
  if (best) {
    const a = new THREE.Vector3().crossVectors(drag.n, best);
    const axis = Math.abs(a.x) > 0.5 ? "x" : Math.abs(a.y) > 0.5 ? "y" : "z";
    enqueue(axis, Math.round(drag.p[axis]), Math.sign(a[axis]) * Math.PI / 2);
  }
  drag = null; controls.enabled = true;
});
const end = () => { drag = null; controls.enabled = true; };
el.addEventListener("pointerup", end); el.addEventListener("pointercancel", end);

function resize() {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  camera.position.setLength(camera.position.length());
  camera.updateProjectionMatrix();
}
addEventListener("resize", resize); resize();
renderer.setAnimationLoop(now => { update(performance.now()); controls.update(); renderer.render(scene, camera); });
