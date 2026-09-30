import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

/* ------------------------------------------------------------------ */
/*  Renderer / scene / camera                                          */
/* ------------------------------------------------------------------ */

const container = document.getElementById("scene");

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
  38,
  container.clientWidth / container.clientHeight,
  0.1,
  100
);
camera.position.set(4.8, 4.4, 6.4);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.09;
controls.enablePan = false;
controls.minDistance = 5.5;
controls.maxDistance = 16;
controls.rotateSpeed = 0.85;
controls.zoomSpeed = 0.8;

/* ------------------------------------------------------------------ */
/*  Lighting                                                           */
/* ------------------------------------------------------------------ */

scene.add(new THREE.HemisphereLight(0xdfe9ff, 0x2a3247, 1.15));

const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
keyLight.position.set(7, 11, 8);
keyLight.castShadow = true;
keyLight.shadow.mapSize.set(1024, 1024);
keyLight.shadow.radius = 4;
keyLight.shadow.bias = -0.0005;
const shadowCam = keyLight.shadow.camera;
shadowCam.left = -8;
shadowCam.right = 8;
shadowCam.top = 8;
shadowCam.bottom = -8;
shadowCam.near = 0.5;
shadowCam.far = 40;
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0x9dbbff, 0.85);
fillLight.position.set(-8, -3, -6);
scene.add(fillLight);

const rimLight = new THREE.DirectionalLight(0xffffff, 0.7);
rimLight.position.set(-5, 7, -9);
scene.add(rimLight);

/* Soft contact shadow on a transparent floor. */
const floor = new THREE.Mesh(
  new THREE.CircleGeometry(7, 64),
  new THREE.ShadowMaterial({ opacity: 0.34 })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -2.35;
floor.receiveShadow = true;
scene.add(floor);

/* ------------------------------------------------------------------ */
/*  Cube construction                                                  */
/* ------------------------------------------------------------------ */

const CUBIE_SIZE = 0.94;
const STICKER_SIZE = 0.8;

const FACE_COLORS = {
  right: 0xe8322b, // +x
  left: 0xff8c1a, // -x
  up: 0xf7f7f7, // +y
  down: 0xffd21e, // -y
  front: 0x1fbf4b, // +z
  back: 0x1f6fe0, // -z
};

/* Rounded-rectangle shape, extruded a little to make a nice sticker. */
function roundedRectShape(width, height, radius) {
  const s = new THREE.Shape();
  const x = -width / 2;
  const y = -height / 2;
  s.moveTo(x + radius, y);
  s.lineTo(x + width - radius, y);
  s.quadraticCurveTo(x + width, y, x + width, y + radius);
  s.lineTo(x + width, y + height - radius);
  s.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  s.lineTo(x + radius, y + height);
  s.quadraticCurveTo(x, y + height, x, y + height - radius);
  s.lineTo(x, y + radius);
  s.quadraticCurveTo(x, y, x + radius, y);
  return s;
}

const stickerGeometry = new THREE.ExtrudeGeometry(
  roundedRectShape(STICKER_SIZE, STICKER_SIZE, 0.14),
  { depth: 0.028, bevelEnabled: false, curveSegments: 6 }
);
stickerGeometry.center();

const bodyGeometry = new RoundedBoxGeometry(CUBIE_SIZE, CUBIE_SIZE, CUBIE_SIZE, 4, 0.1);

const bodyMaterial = new THREE.MeshStandardMaterial({
  color: 0x0d0e12,
  roughness: 0.62,
  metalness: 0.25,
});

const stickerMaterials = {};
for (const [name, color] of Object.entries(FACE_COLORS)) {
  stickerMaterials[name] = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.34,
    metalness: 0.05,
    emissive: new THREE.Color(color).multiplyScalar(0.06),
  });
}

const cubeGroup = new THREE.Group();
scene.add(cubeGroup);

const cubies = [];

function addSticker(group, axis, sign, material) {
  const sticker = new THREE.Mesh(stickerGeometry, material);
  const offset = CUBIE_SIZE / 2 - 0.012;
  if (axis === "x") {
    sticker.position.x = sign * offset;
    sticker.rotation.y = sign > 0 ? Math.PI / 2 : -Math.PI / 2;
  } else if (axis === "y") {
    sticker.position.y = sign * offset;
    sticker.rotation.x = sign > 0 ? -Math.PI / 2 : Math.PI / 2;
  } else {
    sticker.position.z = sign * offset;
    sticker.rotation.y = sign > 0 ? 0 : Math.PI;
  }
  sticker.castShadow = false;
  group.add(sticker);
}

for (let x = -1; x <= 1; x++) {
  for (let y = -1; y <= 1; y++) {
    for (let z = -1; z <= 1; z++) {
      const group = new THREE.Group();
      group.position.set(x, y, z);

      const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
      body.castShadow = true;
      body.receiveShadow = true;
      group.add(body);

      if (x === 1) addSticker(group, "x", 1, stickerMaterials.right);
      if (x === -1) addSticker(group, "x", -1, stickerMaterials.left);
      if (y === 1) addSticker(group, "y", 1, stickerMaterials.up);
      if (y === -1) addSticker(group, "y", -1, stickerMaterials.down);
      if (z === 1) addSticker(group, "z", 1, stickerMaterials.front);
      if (z === -1) addSticker(group, "z", -1, stickerMaterials.back);

      const cubie = { group, body, home: new THREE.Vector3(x, y, z) };
      body.userData.cubie = cubie;
      cubies.push(cubie);
      cubeGroup.add(group);
    }
  }
}

/* ------------------------------------------------------------------ */
/*  Move engine                                                        */
/* ------------------------------------------------------------------ */

const AXIS_VECTORS = {
  x: new THREE.Vector3(1, 0, 0),
  y: new THREE.Vector3(0, 1, 0),
  z: new THREE.Vector3(0, 0, 1),
};

/* Standard face turns: which layer around which axis, and the number of
   quarter turns about the POSITIVE axis that counts as clockwise. */
const FACE_TURNS = {
  R: { axis: "x", layer: 1, turns: -1 },
  L: { axis: "x", layer: -1, turns: 1 },
  U: { axis: "y", layer: 1, turns: -1 },
  D: { axis: "y", layer: -1, turns: 1 },
  F: { axis: "z", layer: 1, turns: -1 },
  B: { axis: "z", layer: -1, turns: 1 },
};

const queue = [];
let animating = null;
const DEFAULT_DURATION = 175;

function enqueue(move) {
  queue.push(move);
  startNext();
}

function startNext() {
  if (animating || queue.length === 0) return;

  const move = queue.shift();
  const axisVec = AXIS_VECTORS[move.axis].clone();
  const selected = cubies.filter(
    (c) => Math.round(c.group.position[move.axis]) === move.layer
  );

  const pivot = new THREE.Group();
  cubeGroup.add(pivot);
  for (const c of selected) pivot.add(c.group);

  animating = {
    pivot,
    selected,
    axisVec,
    totalAngle: move.turns * (Math.PI / 2),
    duration: move.duration ?? DEFAULT_DURATION,
    elapsed: 0,
  };
}

function finishMove() {
  const { pivot, selected, axisVec, totalAngle } = animating;
  const rotation = new THREE.Quaternion().setFromAxisAngle(axisVec, totalAngle);

  pivot.quaternion.identity();
  for (const c of selected) {
    c.group.position.applyQuaternion(rotation);
    c.group.position.round();
    c.group.quaternion.premultiply(rotation).normalize();
    cubeGroup.add(c.group); // also detaches from the pivot
  }
  cubeGroup.remove(pivot);

  animating = null;
  startNext();
}

function parseMove(notation) {
  const face = FACE_TURNS[notation[0].toUpperCase()];
  if (!face) return null;
  let turns = face.turns;
  if (notation.includes("'")) turns = -turns;
  if (notation.includes("2")) turns *= 2;
  return { axis: face.axis, layer: face.layer, turns };
}

function hardReset() {
  queue.length = 0;
  if (animating) finishMove();
  for (const c of cubies) {
    c.group.position.copy(c.home);
    c.group.quaternion.identity();
  }
}

function scramble() {
  const faces = Object.keys(FACE_TURNS);
  let last = null;
  for (let i = 0; i < 25; i++) {
    let face;
    do {
      face = faces[Math.floor(Math.random() * faces.length)];
    } while (face === last);
    last = face;

    const base = FACE_TURNS[face];
    const direction = Math.random() < 0.5 ? 1 : -1;
    enqueue({
      axis: base.axis,
      layer: base.layer,
      turns: base.turns * direction,
      duration: 115,
    });
  }
}

/* ------------------------------------------------------------------ */
/*  Drag-to-turn interaction                                           */
/* ------------------------------------------------------------------ */

const raycaster = new THREE.Raycaster();
let faceDrag = null;

function pointerToNDC(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  return new THREE.Vector2(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1
  );
}

function snapToAxis(vector) {
  const abs = [Math.abs(vector.x), Math.abs(vector.y), Math.abs(vector.z)];
  const index = abs.indexOf(Math.max(...abs));
  const snapped = new THREE.Vector3();
  snapped.setComponent(index, Math.sign(vector.getComponent(index)) || 1);
  return snapped;
}

function projectToScreen(vector) {
  const projected = vector.clone().project(camera);
  return new THREE.Vector2(projected.x, projected.y);
}

function onPointerDown(event) {
  if (event.button !== 0) return;

  raycaster.setFromCamera(pointerToNDC(event), camera);
  const bodies = cubies.map((c) => c.body);
  const hits = raycaster.intersectObjects(bodies, false);
  if (hits.length === 0) return;

  const hit = hits[0];
  const cubie = hit.object.userData.cubie;
  const normalMatrix = new THREE.Matrix3().getNormalMatrix(hit.object.matrixWorld);
  const worldNormal = snapToAxis(
    hit.face.normal.clone().applyMatrix3(normalMatrix).normalize()
  );

  faceDrag = {
    cubie,
    normal: worldNormal,
    startPoint: hit.point.clone(),
    startX: event.clientX,
    startY: event.clientY,
    done: false,
  };

  controls.enabled = false;
  renderer.domElement.setPointerCapture?.(event.pointerId);
  event.preventDefault();
}

function onPointerMove(event) {
  if (!faceDrag || faceDrag.done) return;

  const dx = event.clientX - faceDrag.startX;
  const dy = event.clientY - faceDrag.startY;
  if (Math.hypot(dx, dy) < 8) return;

  const dragVec = new THREE.Vector2(dx, -dy).normalize();
  const normal = faceDrag.normal;

  // The two world axes that lie in the dragged face.
  let best = null;
  for (const name of ["x", "y", "z"]) {
    if (Math.abs(normal[name]) > 0.5) continue;
    const axisVec = AXIS_VECTORS[name];
    const from = projectToScreen(faceDrag.startPoint);
    const to = projectToScreen(
      faceDrag.startPoint.clone().addScaledVector(axisVec, 0.6)
    );
    const dir = new THREE.Vector2(to.x - from.x, to.y - from.y);
    if (dir.lengthSq() < 1e-8) continue;
    dir.normalize();
    const dot = dir.dot(dragVec);
    if (!best || Math.abs(dot) > Math.abs(best.dot)) {
      best = { axis: name, dot, axisVec };
    }
  }
  if (!best) return;

  const sign = Math.sign(best.dot) || 1;
  const tangent = best.axisVec.clone().multiplyScalar(sign);
  const rotationAxis = new THREE.Vector3()
    .crossVectors(normal, tangent)
    .normalize();

  // Express the rotation about a positive world axis.
  const index = [rotationAxis.x, rotationAxis.y, rotationAxis.z].findIndex(
    (v) => Math.abs(v) > 0.5
  );
  const axisName = ["x", "y", "z"][index];
  const turns = Math.sign(rotationAxis[axisName]) || 1;
  const layer = Math.round(faceDrag.cubie.group.position[axisName]);

  enqueue({ axis: axisName, layer, turns, duration: 165 });
  faceDrag.done = true;
}

function onPointerUp() {
  if (!faceDrag) return;
  faceDrag = null;
  controls.enabled = true;
}

renderer.domElement.addEventListener("pointerdown", onPointerDown, true);
window.addEventListener("pointermove", onPointerMove);
window.addEventListener("pointerup", onPointerUp);
window.addEventListener("pointercancel", onPointerUp);

/* ------------------------------------------------------------------ */
/*  Keyboard + buttons                                                 */
/* ------------------------------------------------------------------ */

window.addEventListener("keydown", (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  const key = event.key.toUpperCase();
  if (!FACE_TURNS[key]) return;
  const move = parseMove(event.shiftKey ? `${key}'` : key);
  if (move) enqueue(move);
  event.preventDefault();
});

document.querySelectorAll("[data-move]").forEach((button) => {
  button.addEventListener("click", () => {
    const move = parseMove(button.dataset.move);
    if (move) enqueue(move);
  });
});

document.getElementById("scramble").addEventListener("click", scramble);
document.getElementById("reset").addEventListener("click", hardReset);

/* ------------------------------------------------------------------ */
/*  Resize + render loop                                               */
/* ------------------------------------------------------------------ */

function onResize() {
  const width = container.clientWidth;
  const height = container.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}
window.addEventListener("resize", onResize);

function easeInOut(t) {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

let lastTime = performance.now();

function animate(now) {
  requestAnimationFrame(animate);
  const dt = Math.min(64, now - lastTime);
  lastTime = now;

  if (animating) {
    animating.elapsed += dt;
    const t = Math.min(1, animating.elapsed / animating.duration);
    animating.pivot.quaternion.setFromAxisAngle(
      animating.axisVec,
      animating.totalAngle * easeInOut(t)
    );
    if (t >= 1) finishMove();
  }

  // Idle float for a little life when nothing is happening.
  if (!animating && queue.length === 0 && !faceDrag) {
    cubeGroup.position.y = Math.sin(now * 0.0011) * 0.05;
  } else {
    cubeGroup.position.y *= 0.82;
  }

  controls.update();
  renderer.render(scene, camera);
}

requestAnimationFrame(animate);
