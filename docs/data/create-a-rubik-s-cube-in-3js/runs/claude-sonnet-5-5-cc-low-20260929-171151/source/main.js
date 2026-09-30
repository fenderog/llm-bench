import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(devicePixelRatio);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
camera.position.set(5, 4.5, 6.5);
scene.add(new THREE.AmbientLight(0xffffff, 1.4));
const dl = new THREE.DirectionalLight(0xffffff, 1.5);
dl.position.set(5, 8, 6);
scene.add(dl);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enablePan = false;
controls.enableDamping = true;

const COLORS = { x1: 0xb71234, x_1: 0xff5800, y1: 0xffffff, y_1: 0xffd500, z1: 0x009b48, z_1: 0x0046ad };
const body = new THREE.BoxGeometry(0.96, 0.96, 0.96);
const blackMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.6 });
const stickerGeo = new THREE.PlaneGeometry(0.98 * 0.86, 0.98 * 0.86);
const cubies = [];
const cube = new THREE.Group();
scene.add(cube);

function build() {
  cubies.forEach((c) => cube.remove(c));
  cubies.length = 0;
  for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
    const c = new THREE.Group();
    c.add(new THREE.Mesh(body, blackMat));
    const faces = [["x", x], ["y", y], ["z", z]];
    for (const [a, v] of faces) {
      if (!v) continue;
      const m = new THREE.Mesh(stickerGeo, new THREE.MeshStandardMaterial({ color: COLORS[a + (v > 0 ? "1" : "_1")], roughness: 0.35 }));
      m.position[a] = v * 0.485;
      if (a === "x") m.rotation.y = v * Math.PI / 2;
      if (a === "y") m.rotation.x = -v * Math.PI / 2;
      if (a === "z" && v < 0) m.rotation.y = Math.PI;
      c.add(m);
    }
    c.position.set(x, y, z);
    cube.add(c);
    cubies.push(c);
  }
}
build();

const AX = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };
const queue = [];
let busy = false;
function move(axis, layer, dir, fast) {
  queue.push({ axis, layer, dir, fast });
  if (!busy) next();
}
function next() {
  const m = queue.shift();
  if (!m) { busy = false; return; }
  busy = true;
  const pivot = new THREE.Group();
  cube.add(pivot);
  const sel = cubies.filter((c) => Math.round(c.position[m.axis]) === m.layer);
  sel.forEach((c) => pivot.attach(c));
  const dur = m.fast ? 90 : 260, t0 = performance.now(), target = m.dir * Math.PI / 2;
  (function step(t) {
    const k = Math.min(1, (t - t0) / dur), e = k * k * (3 - 2 * k);
    pivot.rotation[m.axis] = target * e;
    if (k < 1) return requestAnimationFrame(step);
    pivot.updateMatrixWorld();
    sel.forEach((c) => {
      cube.attach(c);
      c.position.round();
      const e2 = new THREE.Euler().setFromQuaternion(c.quaternion);
      c.quaternion.setFromEuler(new THREE.Euler(
        Math.round(e2.x / (Math.PI / 2)) * Math.PI / 2, Math.round(e2.y / (Math.PI / 2)) * Math.PI / 2, Math.round(e2.z / (Math.PI / 2)) * Math.PI / 2));
    });
    cube.remove(pivot);
    next();
  })(t0);
}

const keyMap = { u: ["y", 1, -1], d: ["y", -1, 1], r: ["x", 1, -1], l: ["x", -1, 1], f: ["z", 1, -1], b: ["z", -1, 1] };
addEventListener("keydown", (e) => {
  const k = keyMap[e.key.toLowerCase()];
  if (k) move(k[0], k[1], e.shiftKey ? -k[2] : k[2]);
});
document.getElementById("scr").onclick = () => {
  for (let i = 0; i < 25; i++) {
    const a = "xyz"[Math.floor(Math.random() * 3)];
    move(a, Math.floor(Math.random() * 3) - 1, Math.random() < 0.5 ? 1 : -1, true);
  }
};
document.getElementById("rst").onclick = () => { queue.length = 0; if (!busy) build(); };

// drag to turn a layer
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let drag = null;
function setPtr(e) {
  ptr.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(ptr, camera);
}
function toScreen(v) {
  const p = v.clone().project(camera);
  return new THREE.Vector2(p.x * innerWidth / 2, -p.y * innerHeight / 2);
}
renderer.domElement.addEventListener("pointerdown", (e) => {
  if (busy) return;
  setPtr(e);
  const hit = ray.intersectObjects(cubies, true)[0];
  if (!hit || !hit.face) return;
  const n = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
  const na = ["x", "y", "z"].reduce((a, b) => Math.abs(n[a]) > Math.abs(n[b]) ? a : b);
  const normal = new THREE.Vector3().setComponent("xyz".indexOf(na), Math.sign(n[na]));
  let cubie = hit.object; while (cubie.parent !== cube) cubie = cubie.parent;
  drag = { x: e.clientX, y: e.clientY, normal, point: hit.point.clone(), cubie };
  controls.enabled = false;
});
addEventListener("pointermove", (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.hypot(dx, dy) < 12) return;
  const d = new THREE.Vector2(dx, dy).normalize();
  let best = null;
  for (const a of "xyz") {
    if (a === "xyz"[drag.normal.toArray().findIndex((v) => v)]) continue;
    for (const s of [1, -1]) {
      const t = AX[a].clone().multiplyScalar(s);
      const sd = toScreen(drag.point.clone().add(t)).sub(toScreen(drag.point)).normalize();
      const dot = sd.dot(d);
      if (!best || dot > best.dot) best = { dot, t };
    }
  }
  const rot = new THREE.Vector3().crossVectors(drag.normal, best.t);
  const axis = "xyz"[rot.toArray().findIndex((v) => Math.abs(v) > 0.5)];
  move(axis, Math.round(drag.cubie.position[axis]), Math.sign(rot[axis]));
  drag = null;
  controls.enabled = true;
});
addEventListener("pointerup", () => { drag = null; controls.enabled = true; });

function resize() {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
}
addEventListener("resize", resize);
resize();
renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
