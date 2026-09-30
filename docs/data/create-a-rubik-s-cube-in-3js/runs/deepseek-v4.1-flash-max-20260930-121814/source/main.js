/**
 * main.js — interactive Rubik's cube.
 *
 * Controls
 *   • Drag a sticker/face → turn that layer
 *   • Drag the background → orbit the camera
 *   • Wheel / pinch      → zoom
 *   • U D L R F B (hold Shift for inverse), M E S slices, X Y Z whole cube
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { RubiksCube, parseMove, randomScramble } from './cube.js';

// ---------------------------------------------------------------------------
// Renderer / scene / camera
// ---------------------------------------------------------------------------

const stage = document.getElementById('stage');

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.domElement.setAttribute('aria-label', "Interactive Rubik's cube");
stage.appendChild(renderer.domElement);

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(4.7, 4.1, 5.7);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.enablePan = false;
controls.minDistance = 4.6;
controls.maxDistance = 14;
controls.minPolarAngle = 0.12;
controls.maxPolarAngle = Math.PI - 0.12;
controls.rotateSpeed = 0.85;
controls.zoomSpeed = 0.9;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.7;

// ---------------------------------------------------------------------------
// Lighting (all procedural — no external assets)
// ---------------------------------------------------------------------------

const pmrem = new THREE.PMREMGenerator(renderer);
const environment = pmrem.fromScene(new RoomEnvironment(), 0.04);
scene.environment = environment.texture;
scene.environmentIntensity = 0.65;
pmrem.dispose();

const hemi = new THREE.HemisphereLight(0xdfe9ff, 0x2c3242, 0.7);
scene.add(hemi);

const keyLight = new THREE.DirectionalLight(0xffffff, 2.1);
keyLight.position.set(6, 10, 7);
keyLight.castShadow = true;
keyLight.shadow.mapSize.set(2048, 2048);
keyLight.shadow.camera.left = -6;
keyLight.shadow.camera.right = 6;
keyLight.shadow.camera.top = 6;
keyLight.shadow.camera.bottom = -6;
keyLight.shadow.camera.near = 1;
keyLight.shadow.camera.far = 30;
keyLight.shadow.bias = -0.0004;
keyLight.shadow.normalBias = 0.02;
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0x9db8ff, 0.55);
fillLight.position.set(-7, -4, -6);
scene.add(fillLight);

const rimLight = new THREE.DirectionalLight(0xffe3c2, 0.4);
rimLight.position.set(-4, 6, -8);
scene.add(rimLight);

// Soft shadow catcher so the cube appears to float over the background.
const shadowPlane = new THREE.Mesh(
  new THREE.PlaneGeometry(40, 40),
  new THREE.ShadowMaterial({ color: 0x000000, opacity: 0.32, transparent: true }),
);
shadowPlane.rotation.x = -Math.PI / 2;
shadowPlane.position.y = -1.78;
shadowPlane.receiveShadow = true;
scene.add(shadowPlane);

// ---------------------------------------------------------------------------
// The cube
// ---------------------------------------------------------------------------

const cube = new RubiksCube();
scene.add(cube);

// ---------------------------------------------------------------------------
// Pointer interaction: drag a face to turn its layer
// ---------------------------------------------------------------------------

const raycaster = new THREE.Raycaster();
const pointerNdc = new THREE.Vector2();
const timer = new THREE.Timer();

/** @type {null | {pointerId:number, startX:number, startY:number, cubie:THREE.Group, normal:THREE.Vector3, tangents:THREE.Vector3[], screenDirs:{x:number,y:number}[], triggered:boolean}} */
let drag = null;

function castCubie(clientX, clientY) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointerNdc.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  pointerNdc.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointerNdc, camera);

  const hits = raycaster.intersectObjects(cube.cubies, true);
  if (hits.length === 0) return null;

  let object = hits[0].object;
  while (object && !object.userData.cubie) object = object.parent;
  if (!object) return null;

  return { cubie: object.userData.cubie, point: hits[0].point.clone() };
}

/** Screen-space direction (px) of a world-space direction at a world point. */
function screenDirection(worldPoint, worldDir) {
  const p1 = worldPoint.clone().project(camera);
  const p2 = worldPoint
    .clone()
    .addScaledVector(worldDir, 0.25)
    .project(camera);
  const dx = ((p2.x - p1.x) * window.innerWidth) / 2;
  const dy = (-(p2.y - p1.y) * window.innerHeight) / 2;
  const len = Math.hypot(dx, dy) || 1e-6;
  return { x: dx / len, y: dy / len };
}

const _worldQuat = new THREE.Quaternion();

function onPointerDown(event) {
  if (event.pointerType === 'mouse' && event.button !== 0) return;
  if (drag) return;

  // Let orbit controls handle the gesture while a turn is animating.
  if (cube.busy) return;

  const hit = castCubie(event.clientX, event.clientY);
  if (!hit) return;

  const { cubie } = hit;

  // Which face did we grab? Work in cube-local space and snap the hit
  // offset from the cubie center to the dominant axis.
  const localPoint = cube.worldToLocal(hit.point.clone());
  const offset = localPoint.sub(cubie.position);
  let axis = 'x';
  if (Math.abs(offset.y) > Math.abs(offset[axis])) axis = 'y';
  if (Math.abs(offset.z) > Math.abs(offset[axis])) axis = 'z';

  const normal = new THREE.Vector3();
  normal[axis] = Math.sign(offset[axis]) || 1;

  // The two in-plane axes are the candidate drag directions.
  const tangents = ['x', 'y', 'z']
    .filter((name) => name !== axis)
    .map((name) => new THREE.Vector3(name === 'x' ? 1 : 0, name === 'y' ? 1 : 0, name === 'z' ? 1 : 0));

  cube.getWorldQuaternion(_worldQuat);
  const screenDirs = tangents.map((t) => screenDirection(hit.point, t.clone().applyQuaternion(_worldQuat)));

  drag = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    cubie,
    normal,
    tangents,
    screenDirs,
    triggered: false,
  };

  controls.enabled = false; // this gesture turns layers, it doesn't orbit
  controls.autoRotate = false;
  renderer.domElement.setPointerCapture(event.pointerId);
}

function onPointerMove(event) {
  if (!drag || event.pointerId !== drag.pointerId) return;
  if (drag.triggered) return; // one turn per drag gesture

  const dx = event.clientX - drag.startX;
  const dy = event.clientY - drag.startY;
  if (Math.hypot(dx, dy) < 12) return;

  // Pick the in-plane axis the drag points along most strongly.
  let best = 0;
  let bestScore = -Infinity;
  let bestSign = 1;
  for (let i = 0; i < drag.tangents.length; i++) {
    const dir = drag.screenDirs[i];
    const dot = dx * dir.x + dy * dir.y;
    if (Math.abs(dot) > bestScore) {
      bestScore = Math.abs(dot);
      best = i;
      bestSign = Math.sign(dot) || 1;
    }
  }

  // Rotating about (faceNormal × dragDirection) moves the face along the
  // drag when the angle is positive.
  const dragDir = drag.tangents[best].clone().multiplyScalar(bestSign);
  const axisVec = new THREE.Vector3().crossVectors(drag.normal, dragDir);
  const axisName = ['x', 'y', 'z'].reduce((a, b) => (Math.abs(axisVec[a]) >= Math.abs(axisVec[b]) ? a : b));
  const layer = Math.round(drag.cubie.position[axisName]);

  cube.enqueue({
    notation: 'drag',
    axis: axisVec.normalize(),
    axisName,
    layer,
    angle: Math.PI / 2,
    duration: 0.15,
    elapsed: 0,
  });
  drag.triggered = true;
  hud.userMove();
}

function endPointer(event) {
  if (!drag || (event && event.pointerId !== drag.pointerId)) return;
  drag = null;
  controls.enabled = true;
}

renderer.domElement.addEventListener(
  'pointerdown',
  () => {
    controls.autoRotate = false;
  },
  { once: true },
);
renderer.domElement.addEventListener('pointerdown', onPointerDown);
renderer.domElement.addEventListener('pointermove', onPointerMove);
renderer.domElement.addEventListener('pointerup', endPointer);
renderer.domElement.addEventListener('pointercancel', endPointer);

// ---------------------------------------------------------------------------
// Keyboard
// ---------------------------------------------------------------------------

window.addEventListener('keydown', (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  const notation = event.key.length === 1 ? event.key + (event.shiftKey ? "'" : '') : '';
  const move = parseMove(notation, 0.16);
  if (!move) return;
  event.preventDefault();
  controls.autoRotate = false;
  hud.userMove();
  cube.enqueue(move);
});

// ---------------------------------------------------------------------------
// HUD: timer, move counter, toast
// ---------------------------------------------------------------------------

const timerEl = document.getElementById('timer');
const movesEl = document.getElementById('moves');
const toastEl = document.getElementById('toast');

const hud = {
  scrambled: false,
  scrambling: false,
  timerRunning: false,
  timerStart: 0,
  timerElapsed: 0,
  moves: 0,
  solvedShown: false,
  lastScramble: [],

  formatTime(seconds) {
    return seconds.toFixed(2);
  },

  refresh() {
    timerEl.textContent = this.formatTime(this.timerElapsed);
    movesEl.textContent = String(this.moves);
  },

  resetStats() {
    this.timerRunning = false;
    this.timerStart = 0;
    this.timerElapsed = 0;
    this.moves = 0;
    this.solvedShown = false;
    this.refresh();
    toastEl.classList.remove('show');
  },

  userMove() {
    this.moves += 1;
    this.refresh();
    if (this.scrambled && !this.scrambling && !this.timerRunning) {
      this.timerRunning = true;
      this.timerStart = performance.now();
    }
    if (this.solvedShown) {
      this.solvedShown = false;
      toastEl.classList.remove('show');
    }
  },

  tick(now) {
    if (!this.timerRunning) return;
    this.timerElapsed = (now - this.timerStart) / 1000;
    timerEl.textContent = this.formatTime(this.timerElapsed);
  },

  stopTimer() {
    if (!this.timerRunning) return;
    this.timerElapsed = (performance.now() - this.timerStart) / 1000;
    this.timerRunning = false;
    this.refresh();
  },
};

document.getElementById('scramble').addEventListener('click', () => {
  hud.resetStats();
  hud.scrambling = true;
  hud.scrambled = true;
  hud.lastScramble = randomScramble(20);
  for (const notation of hud.lastScramble) {
    cube.enqueue(parseMove(notation, 0.085));
  }
});

document.getElementById('reset').addEventListener('click', () => {
  cube.reset();
  hud.scrambling = false;
  hud.scrambled = false;
  hud.resetStats();
});

cube.addEventListener('movecomplete', () => {
  if (hud.scrambling && !cube.busy && cube.queue.length === 0) {
    hud.scrambling = false;
  }
  if (hud.scrambled && hud.timerRunning && !hud.scrambling && cube.isSolved()) {
    hud.stopTimer();
    hud.solvedShown = true;
    toastEl.textContent = `Solved in ${hud.formatTime(hud.timerElapsed)}s · ${hud.moves} moves`;
    toastEl.classList.add('show');
  }
});

// ---------------------------------------------------------------------------
// Resize + render loop
// ---------------------------------------------------------------------------

function onResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
}
window.addEventListener('resize', onResize);

function frame(now) {
  timer.update(now);
  const dt = Math.min(timer.getDelta(), 0.05);
  controls.update();
  cube.update(dt);
  hud.tick(now);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// Handy for debugging / automated checks.
window.__rubik = {
  cube,
  camera,
  scene,
  renderer,
  controls,
  hud,
  apply: (notation) => {
    const move = parseMove(notation, 0.16);
    if (move) {
      hud.userMove();
      cube.enqueue(move);
    }
    return move;
  },
  scramble: () => document.getElementById('scramble').click(),
  reset: () => document.getElementById('reset').click(),
};
