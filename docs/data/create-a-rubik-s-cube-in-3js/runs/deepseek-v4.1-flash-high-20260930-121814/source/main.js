import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/* ------------------------------------------------------------------ *
 * Scene / renderer
 * ------------------------------------------------------------------ */

const container = document.getElementById("app");

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
  42,
  window.innerWidth / window.innerHeight,
  0.1,
  100
);
camera.position.set(5.4, 5.0, 7.4);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.09;
controls.enablePan = false;
controls.rotateSpeed = 0.85;
controls.zoomSpeed = 0.8;
controls.minDistance = 6;
controls.maxDistance = 18;
controls.target.set(0, 0, 0);

/* ------------------------------------------------------------------ *
 * Lighting
 * ------------------------------------------------------------------ */

scene.add(new THREE.HemisphereLight(0xdbe6ff, 0x1b1f2a, 1.15));

const keyLight = new THREE.DirectionalLight(0xffffff, 2.1);
keyLight.position.set(6, 9, 7);
keyLight.castShadow = true;
keyLight.shadow.mapSize.set(2048, 2048);
keyLight.shadow.camera.near = 1;
keyLight.shadow.camera.far = 30;
keyLight.shadow.camera.left = -8;
keyLight.shadow.camera.right = 8;
keyLight.shadow.camera.top = 8;
keyLight.shadow.camera.bottom = -8;
keyLight.shadow.bias = -0.0006;
keyLight.shadow.radius = 4;
scene.add(keyLight);

const rimLight = new THREE.DirectionalLight(0x89b8ff, 0.9);
rimLight.position.set(-7, 3, -6);
scene.add(rimLight);

const fillLight = new THREE.DirectionalLight(0xffd9b0, 0.5);
fillLight.position.set(-3, -6, 4);
scene.add(fillLight);

/* ------------------------------------------------------------------ *
 * Cube construction
 * ------------------------------------------------------------------ */

const CUBE_SIZE = 1; // spacing between cubie centres
const CUBIE_SIZE = 0.94;
const STICKER_SIZE = 0.82;
const STICKER_RADIUS = 0.13;

const COLORS = {
  right: 0xd92b32, // +X  red
  left: 0xf07d1c, //  -X  orange
  up: 0xf6f7fb, //    +Y  white
  down: 0xf6d21e, //  -Y  yellow
  front: 0x1eaa5c, // +Z  green
  back: 0x2464d8, //  -Z  blue
  body: 0x14161c,
};

const cube = new THREE.Group();
scene.add(cube);

const cubies = [];

const bodyMaterial = new THREE.MeshStandardMaterial({
  color: COLORS.body,
  roughness: 0.72,
  metalness: 0.05,
});

const stickerMaterials = {};
for (const [name, color] of Object.entries(COLORS)) {
  if (name === "body") continue;
  stickerMaterials[name] = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.34,
    metalness: 0.02,
    emissive: new THREE.Color(color).multiplyScalar(0.06),
  });
}

function roundedRectShape(size, radius) {
  const s = new THREE.Shape();
  const h = size / 2;
  const r = radius;
  s.moveTo(-h + r, -h);
  s.lineTo(h - r, -h);
  s.quadraticCurveTo(h, -h, h, -h + r);
  s.lineTo(h, h - r);
  s.quadraticCurveTo(h, h, h - r, h);
  s.lineTo(-h + r, h);
  s.quadraticCurveTo(-h, h, -h, h - r);
  s.lineTo(-h, -h + r);
  s.quadraticCurveTo(-h, -h, -h + r, -h);
  return s;
}

const stickerGeometry = new THREE.ShapeGeometry(
  roundedRectShape(STICKER_SIZE, STICKER_RADIUS),
  6
);

const bodyGeometry = new THREE.BoxGeometry(CUBIE_SIZE, CUBIE_SIZE, CUBIE_SIZE);

// Each sticker is a small plane placed on an outer face of its cubie.
const STICKER_LAYOUT = [
  { dir: [1, 0, 0], color: "right", position: [0.5, 0, 0], rotation: [0, Math.PI / 2, 0] },
  { dir: [-1, 0, 0], color: "left", position: [-0.5, 0, 0], rotation: [0, -Math.PI / 2, 0] },
  { dir: [0, 1, 0], color: "up", position: [0, 0.5, 0], rotation: [-Math.PI / 2, 0, 0] },
  { dir: [0, -1, 0], color: "down", position: [0, -0.5, 0], rotation: [Math.PI / 2, 0, 0] },
  { dir: [0, 0, 1], color: "front", position: [0, 0, 0.5], rotation: [0, 0, 0] },
  { dir: [0, 0, -1], color: "back", position: [0, 0, -0.5], rotation: [0, Math.PI, 0] },
];

function buildCubie(x, y, z) {
  const group = new THREE.Group();
  group.position.set(x * CUBE_SIZE, y * CUBE_SIZE, z * CUBE_SIZE);

  const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
  body.castShadow = true;
  body.receiveShadow = true;
  body.userData.cubie = group;
  group.add(body);

  for (const layout of STICKER_LAYOUT) {
    const [dx, dy, dz] = layout.dir;
    // Only place a sticker on a face that is actually visible from outside.
    if (x * dx + y * dy + z * dz !== 1) continue;

    const sticker = new THREE.Mesh(stickerGeometry, stickerMaterials[layout.color]);
    sticker.position.set(...layout.position);
    sticker.rotation.set(...layout.rotation);
    sticker.castShadow = false;
    sticker.receiveShadow = true;
    sticker.userData.cubie = group;
    group.add(sticker);
  }

  group.userData.home = { position: group.position.clone() };
  return group;
}

for (let x = -1; x <= 1; x++) {
  for (let y = -1; y <= 1; y++) {
    for (let z = -1; z <= 1; z++) {
      const cubie = buildCubie(x, y, z);
      cube.add(cubie);
      cubies.push(cubie);
    }
  }
}

/* ------------------------------------------------------------------ *
 * Soft contact shadow under the cube
 * ------------------------------------------------------------------ */

const shadowTexture = (() => {
  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createRadialGradient(
    size / 2,
    size / 2,
    0,
    size / 2,
    size / 2,
    size / 2
  );
  gradient.addColorStop(0, "rgba(0,0,0,0.55)");
  gradient.addColorStop(0.55, "rgba(0,0,0,0.25)");
  gradient.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
})();

const contactShadow = new THREE.Mesh(
  new THREE.PlaneGeometry(7.5, 7.5),
  new THREE.MeshBasicMaterial({
    map: shadowTexture,
    transparent: true,
    depthWrite: false,
  })
);
contactShadow.rotation.x = -Math.PI / 2;
contactShadow.position.y = -2.35;
scene.add(contactShadow);

/* ------------------------------------------------------------------ *
 * Move engine
 * ------------------------------------------------------------------ */

const AXES = ["x", "y", "z"];
const HALF_TURN = Math.PI / 2;
const MOVE_DURATION = 190; // ms per quarter turn

const queue = [];
const history = [];
let activeMove = null;
let animating = false;

const statusEl = document.getElementById("status");
const buttons = {
  scramble: document.getElementById("scramble"),
  reset: document.getElementById("reset"),
  undo: document.getElementById("undo"),
  top: document.getElementById("top"),
};

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function isSolved() {
  // A cube is solved when every visible sticker shares the colour of the
  // face it currently points at (checked in the cube's local frame).
  for (const cubie of cubies) {
    for (const child of cubie.children) {
      if (!child.userData.cubie) continue;
      const normal = new THREE.Vector3(0, 0, 1)
        .applyQuaternion(child.quaternion)
        .applyQuaternion(cubie.quaternion);
      const axis = normalToAxis(normal);
      if (!axis) return false;
      const expected = stickerColorNameForAxis(axis.name, Math.sign(axis.value));
      if (child.material !== stickerMaterials[expected]) return false;
    }
  }
  return true;
}

function normalToAxis(normal) {
  const abs = [Math.abs(normal.x), Math.abs(normal.y), Math.abs(normal.z)];
  const max = Math.max(...abs);
  if (max < 0.9) return null;
  const index = abs.indexOf(max);
  const name = AXES[index];
  const value = normal[name] >= 0 ? 1 : -1;
  return { name, value };
}

function stickerColorNameForAxis(name, sign) {
  if (name === "x") return sign > 0 ? "right" : "left";
  if (name === "y") return sign > 0 ? "up" : "down";
  return sign > 0 ? "front" : "back";
}

function updateStatus() {
  if (animating || queue.length > 0) {
    const remaining = queue.length + (activeMove ? 1 : 0);
    statusEl.textContent = remaining > 0 ? `Turning\u2026 ${remaining} queued` : "Turning\u2026";
    return;
  }
  statusEl.textContent = isSolved() ? "Solved" : "Scrambled";
}

function enqueue(axis, layer, dir, { record = true, speed = 1 } = {}) {
  queue.push({ axis, layer, dir, duration: MOVE_DURATION * speed, record });
  if (!animating) nextMove();
  updateStatus();
}

function nextMove() {
  if (queue.length === 0) {
    animating = false;
    activeMove = null;
    updateStatus();
    return;
  }

  const move = queue.shift();
  activeMove = move;
  animating = true;
  updateStatus();

  const pivot = new THREE.Group();
  cube.add(pivot);

  const start = performance.now();

  for (const cubie of cubies) {
    if (Math.round(cubie.position[move.axis]) === move.layer) {
      pivot.attach(cubie);
    }
  }

  const target = move.dir * HALF_TURN;

  function step(now) {
    const t = Math.min(1, (now - start) / move.duration);
    pivot.rotation[move.axis] = target * easeInOutCubic(t);

    if (t < 1) {
      requestAnimationFrame(step);
      return;
    }

    pivot.rotation[move.axis] = target;
    pivot.updateMatrixWorld(true);
    for (const child of [...pivot.children]) {
      cube.attach(child);
      snapTransform(child);
    }
    cube.remove(pivot);

    if (move.record) {
      history.push({ axis: move.axis, layer: move.layer, dir: move.dir });
    }

    activeMove = null;
    nextMove();
  }

  requestAnimationFrame(step);
}

function snapTransform(object) {
  object.position.set(
    Math.round(object.position.x),
    Math.round(object.position.y),
    Math.round(object.position.z)
  );

  // Snap orientation to the nearest right-angle rotation.
  const matrix = new THREE.Matrix4().makeRotationFromQuaternion(object.quaternion);
  const e = matrix.elements;
  for (let i = 0; i < 16; i++) e[i] = Math.round(e[i]);
  object.quaternion.setFromRotationMatrix(matrix);
}

/* ------------------------------------------------------------------ *
 * Drag-to-turn interaction
 * ------------------------------------------------------------------ */

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const clock = new THREE.Clock();

const DRAG_THRESHOLD = 9; // px

let dragState = null;

function setPointer(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
}

function pickCubie() {
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(cubies, true);
  for (const hit of hits) {
    if (hit.object.userData.cubie) return hit;
  }
  return null;
}

function worldNormal(hit) {
  const normal = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
  const abs = [Math.abs(normal.x), Math.abs(normal.y), Math.abs(normal.z)];
  const index = abs.indexOf(Math.max(...abs));
  const axisName = AXES[index];
  const name = axisName;
  const value = normal[axisName] >= 0 ? 1 : -1;
  return { name, value, vector: normal.normalize() };
}

// Screen-space direction that a positive rotation about `normal` would push
// the grabbed point, used to decide the turn direction from the drag vector.
function tangentDirection(hitPoint, normalAxis) {
  const axisVector = new THREE.Vector3();
  axisVector[normalAxis.name] = normalAxis.value;

  const perp = hitPoint.clone().sub(
    axisVector.clone().multiplyScalar(hitPoint.dot(axisVector))
  );
  const tangent = new THREE.Vector3().crossVectors(axisVector, perp);
  if (tangent.lengthSq() < 1e-6) {
    // Fall back to an arbitrary tangent when the point sits on the axis.
    tangent.set(0, 1, 0).cross(axisVector);
  }
  return tangent.normalize();
}

function toScreen(point, out) {
  const projected = point.clone().project(camera);
  out.set(projected.x, projected.y);
  return out;
}

function beginLayerDrag(hit, event) {
  const cubie = hit.object.userData.cubie;
  const normal = worldNormal(hit);
  const hitPoint = hit.point.clone();
  const cubiePosition = new THREE.Vector3();
  cubie.getWorldPosition(cubiePosition);

  dragState = {
    cubie,
    normal,
    hitPoint,
    cubiePosition,
    startX: event.clientX,
    startY: event.clientY,
    resolved: false,
  };

  controls.enabled = false;
}

function resolveLayerDrag(event) {
  const dx = event.clientX - dragState.startX;
  const dy = event.clientY - dragState.startY;
  if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return;

  // Client-space dy grows downward; NDC y grows upward, so flip it before
  // comparing against the projected tangent.
  const drag = new THREE.Vector2(dx, -dy).normalize();

  const tangent = tangentDirection(dragState.hitPoint, dragState.normal);
  const a = new THREE.Vector2();
  const b = new THREE.Vector2();
  toScreen(dragState.hitPoint, a);
  toScreen(dragState.hitPoint.clone().add(tangent.clone().multiplyScalar(0.4)), b);
  const screenTangent = b.sub(a);
  if (screenTangent.lengthSq() < 1e-9) {
    screenTangent.set(1, 0);
  }
  screenTangent.normalize();

  const alignment = drag.dot(screenTangent);

  const layer = Math.round(dragState.cubiePosition[dragState.normal.name]);
  const dir = alignment >= 0 ? 1 : -1;

  enqueue(dragState.normal.name, layer, dir);
  dragState.resolved = true;
  endLayerDrag();
}

function endLayerDrag() {
  if (!dragState) return;
  dragState = null;
  controls.enabled = true;
}

renderer.domElement.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  if (animating || queue.length > 0) return;

  setPointer(event);
  const hit = pickCubie();
  if (hit) {
    beginLayerDrag(hit, event);
  }
});

renderer.domElement.addEventListener("pointermove", (event) => {
  if (!dragState || dragState.resolved) return;
  resolveLayerDrag(event);
});

renderer.domElement.addEventListener("pointerup", () => {
  endLayerDrag();
});

renderer.domElement.addEventListener("pointercancel", () => {
  endLayerDrag();
});

renderer.domElement.addEventListener("contextmenu", (event) => {
  event.preventDefault();
});

/* ------------------------------------------------------------------ *
 * Keyboard moves
 * ------------------------------------------------------------------ */

const MOVE_KEYS = {
  u: { axis: "y", layer: 1, dir: -1 },
  d: { axis: "y", layer: -1, dir: 1 },
  r: { axis: "x", layer: 1, dir: -1 },
  l: { axis: "x", layer: -1, dir: 1 },
  f: { axis: "z", layer: 1, dir: -1 },
  b: { axis: "z", layer: -1, dir: 1 },
  m: { axis: "x", layer: 0, dir: 1 },
  e: { axis: "y", layer: 0, dir: -1 },
  s: { axis: "z", layer: 0, dir: 1 },
};

window.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  const move = MOVE_KEYS[key];
  if (!move) return;
  event.preventDefault();
  const dir = event.shiftKey ? -move.dir : move.dir;
  enqueue(move.axis, move.layer, dir);
});

/* ------------------------------------------------------------------ *
 * Buttons
 * ------------------------------------------------------------------ */

function scramble(count = 24) {
  if (animating || queue.length > 0) return;
  let lastAxis = null;
  for (let i = 0; i < count; i++) {
    let axis;
    do {
      axis = AXES[Math.floor(Math.random() * 3)];
    } while (axis === lastAxis);
    lastAxis = axis;

    const layer = [-1, 1][Math.floor(Math.random() * 2)];
    const dir = Math.random() < 0.5 ? 1 : -1;
    enqueue(axis, layer, dir, { record: true, speed: 0.55 });
  }
}

function resetCube() {
  if (animating || queue.length > 0) return;
  queue.length = 0;
  history.length = 0;
  activeMove = null;
  for (const cubie of cubies) {
    cubie.position.copy(cubie.userData.home.position);
    cubie.quaternion.identity();
  }
  updateStatus();
}

function undo() {
  if (animating || queue.length > 0 || history.length === 0) return;
  const move = history.pop();
  queue.push({
    axis: move.axis,
    layer: move.layer,
    dir: -move.dir,
    duration: MOVE_DURATION,
    record: false,
  });
  nextMove();
}

buttons.scramble.addEventListener("click", () => scramble());
buttons.reset.addEventListener("click", resetCube);
buttons.undo.addEventListener("click", undo);
buttons.top.addEventListener("click", () => {
  camera.position.set(0.001, 11, 0.001);
  controls.target.set(0, 0, 0);
  controls.update();
});

/* ------------------------------------------------------------------ *
 * Resize + render loop
 * ------------------------------------------------------------------ */

function onResize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

window.addEventListener("resize", onResize);

function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();
  contactShadow.rotation.z = t * 0.04;
  controls.update();
  renderer.render(scene, camera);
}

updateStatus();
animate();
