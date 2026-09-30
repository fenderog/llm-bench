import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const $ = (id) => document.getElementById(id);
const container = $('canvas-container');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
const home = new THREE.Vector3(5.4, 4.5, 6.8);
camera.position.copy(home);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
container.appendChild(renderer.domElement);
renderer.domElement.setAttribute('aria-label', '3D Rubik’s cube. Drag to orbit, click a face to turn.');
const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
const environment = pmrem.fromScene(room, 0.04);
scene.environment = environment.texture;
scene.environmentIntensity = 0.65;
room.dispose();
pmrem.dispose();
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
orbit.dampingFactor = 0.08;
orbit.enablePan = false;
orbit.minDistance = 6.5;
orbit.maxDistance = 14;
orbit.minPolarAngle = 0.15;
orbit.maxPolarAngle = Math.PI - 0.15;
orbit.rotateSpeed = 0.65;
scene.add(new THREE.HemisphereLight(0xf5ffed, 0x36452c, 0.9));
const light = new THREE.DirectionalLight(0xfff8e8, 2.4);
light.position.set(-3, 7, 5);
light.castShadow = true;
light.shadow.mapSize.set(1024, 1024);
light.shadow.camera.left = -5;
light.shadow.camera.right = 5;
light.shadow.camera.top = 5;
light.shadow.camera.bottom = -5;
light.shadow.normalBias = 0.025;
light.shadow.bias = -0.0001;
light.shadow.radius = 6;
scene.add(light);
const rim = new THREE.DirectionalLight(0xcce9c1, 0.9);
rim.position.set(5, 2, -5);
scene.add(rim);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.ShadowMaterial({ opacity: 0.10 }));
floor.rotation.x = -Math.PI / 2;
floor.position.y = -1.68;
floor.receiveShadow = true;
scene.add(floor);
// A soft contact shadow, generated locally; no external assets.
const shadowCanvas = document.createElement('canvas');
shadowCanvas.width = shadowCanvas.height = 128;
const ctx = shadowCanvas.getContext('2d');
const gradient = ctx.createRadialGradient(64, 64, 5, 64, 64, 64);
gradient.addColorStop(0, 'rgba(0,0,0,0.45)');
gradient.addColorStop(1, 'rgba(0,0,0,0)');
ctx.fillStyle = gradient;
ctx.fillRect(0, 0, 128, 128);
const shadow = new THREE.Mesh(new THREE.PlaneGeometry(5.8, 5.8), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(shadowCanvas), transparent: true, depthWrite: false }));
shadow.rotation.x = -Math.PI / 2;
shadow.position.y = -1.64;
scene.add(shadow);

const faces = {
  U: { axis: 'y', layer: 1, normal: new THREE.Vector3(0, 1, 0), color: 0xf4f0df },
  D: { axis: 'y', layer: -1, normal: new THREE.Vector3(0, -1, 0), color: 0xf2ce38 },
  L: { axis: 'x', layer: -1, normal: new THREE.Vector3(-1, 0, 0), color: 0xf38c35 },
  R: { axis: 'x', layer: 1, normal: new THREE.Vector3(1, 0, 0), color: 0xe84638 },
  F: { axis: 'z', layer: 1, normal: new THREE.Vector3(0, 0, 1), color: 0x43af72 },
  B: { axis: 'z', layer: -1, normal: new THREE.Vector3(0, 0, -1), color: 0x397bdb },
};
const bodyGeometry = new RoundedBoxGeometry(0.99, 0.99, 0.99, 3, 0.064);
const tileShape = new THREE.Shape();
const h = 0.424, r = 0.055;
tileShape.moveTo(-h + r, -h);
tileShape.lineTo(h - r, -h);
tileShape.quadraticCurveTo(h, -h, h, -h + r);
tileShape.lineTo(h, h - r);
tileShape.quadraticCurveTo(h, h, h - r, h);
tileShape.lineTo(-h + r, h);
tileShape.quadraticCurveTo(-h, h, -h, h - r);
tileShape.lineTo(-h, -h + r);
tileShape.quadraticCurveTo(-h, -h, -h + r, -h);
const tileGeometry = new THREE.ExtrudeGeometry(tileShape, { depth: 0.018, bevelEnabled: true, bevelSegments: 3, steps: 1, bevelSize: 0.006, bevelThickness: 0.008, curveSegments: 8 });
tileGeometry.translate(0, 0, -0.009);
const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x0c100e, roughness: 0.42, metalness: 0.025 });
const tileMaterials = Object.fromEntries(Object.entries(faces).map(([face, data]) => [face, new THREE.MeshPhysicalMaterial({ color: data.color, roughness: 0.29, metalness: 0, clearcoat: 0.28, clearcoatRoughness: 0.3 })]));
const cube = new THREE.Group();
scene.add(cube);
let cubies = [];
let tiles = [];
function buildCube() {
  cube.clear();
  cubies = [];
  tiles = [];
  for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
    if (x === 0 && y === 0 && z === 0) continue;
    const cubie = new THREE.Group();
    cubie.position.set(x * 1.025, y * 1.025, z * 1.025);
    cubie.userData.grid = { x, y, z };
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.castShadow = true;
    body.receiveShadow = true;
    cubie.add(body);
    for (const [face, data] of Object.entries(faces)) {
      if ({ x, y, z }[data.axis] !== data.layer) continue;
      const tile = new THREE.Mesh(tileGeometry, tileMaterials[face]);
      tile.position.copy(data.normal).multiplyScalar(0.502);
      tile.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), data.normal);
      tile.userData.colorFace = face;
      tile.userData.normal = data.normal.clone();
      tile.castShadow = true;
      tile.receiveShadow = true;
      cubie.add(tile);
      tiles.push(tile);
    }
    cube.add(cubie);
    cubies.push(cubie);
  }
}
buildCube();

let queue = [];
let active = null;
let path = [];
let history = [];
let moveCount = 0;
let reverse = false;
let mode = 'play';
let startTime = null;
let frozenTime = 0;
let soundEnabled = false;
let audio;
let toastTimeout;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
function toast(message) {
  $('toast').textContent = message;
  $('toast').classList.add('show');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => $('toast').classList.remove('show'), 2300);
}
function clickSound() {
  if (!soundEnabled) return;
  try {
    audio ??= new (window.AudioContext || window.webkitAudioContext)();
    if (audio.state === 'suspended') audio.resume();
    const oscillator = audio.createOscillator();
    const gain = audio.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(480, audio.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(170, audio.currentTime + 0.045);
    gain.gain.setValueAtTime(0.035, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.065);
    oscillator.connect(gain).connect(audio.destination);
    oscillator.start();
    oscillator.stop(audio.currentTime + 0.07);
  } catch { /* Sound is optional in restricted browsers. */ }
}
function solved() {
  const colors = {};
  for (const tile of tiles) {
    const n = tile.userData.normal.clone().applyQuaternion(tile.parent.quaternion);
    const axis = Math.abs(n.x) > 0.9 ? 'x' : Math.abs(n.y) > 0.9 ? 'y' : 'z';
    const side = axis + Math.round(n[axis]);
    if (colors[side] && colors[side] !== tile.userData.colorFace) return false;
    colors[side] = tile.userData.colorFace;
  }
  return true;
}
function updateUI() {
  $('move-count').textContent = String(moveCount).padStart(2, '0');
  $('history-count').textContent = `${history.length} ${history.length === 1 ? 'turn' : 'turns'}`;
  const list = $('history-list');
  list.replaceChildren();
  if (!history.length) {
    const placeholder = document.createElement('span');
    placeholder.className = 'history-placeholder';
    placeholder.textContent = mode === 'scramble' ? 'Mixing things up…' : 'A fresh start. Your moves will appear here.';
    list.appendChild(placeholder);
  } else for (const move of history) {
    const token = document.createElement('span');
    token.className = 'move-token';
    token.textContent = move.face + (move.dir < 0 ? '′' : '');
    list.appendChild(token);
  }
  list.scrollLeft = list.scrollWidth;
  const busy = mode !== 'play' || !!active || queue.length > 0;
  $('undo').disabled = busy || !path.length;
  $('solve').disabled = busy || !path.length || solved();
  $('scramble').disabled = busy;
  document.querySelectorAll('[data-face]').forEach(button => button.disabled = mode !== 'play');
  $('status-text').textContent = mode === 'scramble' ? 'MIXING' : mode === 'solve' ? 'SOLVING' : solved() ? 'SOLVED' : 'IN PLAY';
}
function beginMove(move, now) {
  const data = faces[move.face];
  const pivot = new THREE.Group();
  cube.add(pivot);
  const selected = cubies.filter(c => c.userData.grid[data.axis] === data.layer);
  for (const c of selected) pivot.attach(c);
  active = { ...move, pivot, selected, axis: data.axis, angle: -data.layer * move.dir * Math.PI / 2, start: now, duration: reducedMotion ? 35 : move.kind === 'manual' || move.kind === 'undo' ? 270 : 105 };
  clickSound();
}
function finishMove() {
  const move = active;
  move.pivot.rotation[move.axis] = move.angle;
  move.pivot.updateMatrixWorld(true);
  for (const c of move.selected) {
    cube.attach(c);
    for (const axis of ['x', 'y', 'z']) {
      c.userData.grid[axis] = Math.round(c.position[axis] / 1.025);
      c.position[axis] = c.userData.grid[axis] * 1.025;
    }
    // Snap orientations to exact quarter-turns to prevent accumulated drift.
    const matrix = new THREE.Matrix4().makeRotationFromQuaternion(c.quaternion);
    for (let i = 0; i < 12; i++) matrix.elements[i] = Math.round(matrix.elements[i]);
    c.quaternion.setFromRotationMatrix(matrix).normalize();
  }
  cube.remove(move.pivot);
  if (move.kind === 'manual' || move.kind === 'scramble') path.push({ face: move.face, dir: move.dir });
  if (move.kind === 'manual') {
    history.push({ face: move.face, dir: move.dir });
    moveCount++;
  }
  if (move.kind === 'undo') {
    path.pop();
    if (history.length) { history.pop(); moveCount = Math.max(0, moveCount - 1); }
  }
  active = null;
  if (!queue.length) {
    if (mode === 'scramble') { mode = 'play'; toast('A little chaos. Your challenge starts now.'); }
    else if (mode === 'solve') {
      mode = 'play'; path = []; toast('Back in harmony. Beautiful, isn’t it?');
      if (startTime !== null) frozenTime = performance.now() - startTime;
      startTime = null;
    } else if (solved() && path.length) {
      toast('All in order. Nicely done!');
      if (startTime !== null) frozenTime = performance.now() - startTime;
      startTime = null;
      path = [];
    }
  }
  updateUI();
}
function turn(face, dir = reverse ? -1 : 1) {
  if (mode !== 'play' || queue.length > 24) return;
  if (startTime === null) startTime = performance.now() - frozenTime;
  queue.push({ face, dir, kind: 'manual' });
  const button = document.querySelector(`[data-face="${face}"]`);
  button.classList.add('pulse');
  setTimeout(() => button.classList.remove('pulse'), 220);
  updateUI();
}
function reset(notify = true) {
  queue = []; active = null; mode = 'play'; path = []; history = []; moveCount = 0;
  startTime = null; frozenTime = 0;
  buildCube();
  updateUI();
  $('timer').textContent = '00:00';
  if (notify) toast('A fresh start. Take your time.');
}
function scramble() {
  if (active || queue.length || mode !== 'play') return;
  reset(false);
  mode = 'scramble';
  let previousAxis;
  const keys = Object.keys(faces);
  for (let i = 0; i < 22; i++) {
    let face;
    do { face = keys[Math.floor(Math.random() * keys.length)]; } while (faces[face].axis === previousAxis);
    previousAxis = faces[face].axis;
    queue.push({ face, dir: Math.random() < 0.5 ? -1 : 1, kind: 'scramble' });
  }
  toast('Mixing things up…');
  updateUI();
}
function undo() {
  if (active || queue.length || !path.length || mode !== 'play') return;
  const last = path[path.length - 1];
  queue.push({ face: last.face, dir: -last.dir, kind: 'undo' });
  updateUI();
}
function solve() {
  if (active || queue.length || mode !== 'play' || !path.length || solved()) return;
  mode = 'solve';
  queue = [...path].reverse().map(move => ({ face: move.face, dir: -move.dir, kind: 'solve' }));
  toast('Retracing your turns, one twist at a time.');
  updateUI();
}
document.querySelectorAll('[data-face]').forEach(button => button.addEventListener('click', event => turn(button.dataset.face, event.shiftKey || reverse ? -1 : 1)));
$('scramble').addEventListener('click', scramble);
$('reset').addEventListener('click', () => reset());
$('undo').addEventListener('click', undo);
$('solve').addEventListener('click', solve);
$('direction').addEventListener('click', () => {
  reverse = !reverse;
  $('direction').setAttribute('aria-pressed', String(reverse));
  $('direction-text').textContent = reverse ? 'Counterclockwise' : 'Clockwise';
});
$('view-reset').addEventListener('click', () => {
  camera.position.copy(home); orbit.target.set(0, 0, 0); orbit.update();
  toast('Back to the best angle.');
});
function setTab(guide) {
  $('play-tab').classList.toggle('active', !guide);
  $('guide-tab').classList.toggle('active', guide);
  $('play-tab').setAttribute('aria-selected', String(!guide));
  $('guide-tab').setAttribute('aria-selected', String(guide));
  $('play-content').hidden = guide;
  $('guide-content').hidden = !guide;
}
$('play-tab').addEventListener('click', () => setTab(false));
$('guide-tab').addEventListener('click', () => setTab(true));
$('sound').addEventListener('click', () => {
  soundEnabled = !soundEnabled;
  $('sound').style.color = soundEnabled ? '#d1ed93' : '';
  $('sound').setAttribute('aria-label', soundEnabled ? 'Mute sound' : 'Enable sound');
  $('sound').title = soundEnabled ? 'Mute sound' : 'Enable sound';
  $('sound-wave').setAttribute('d', soundEnabled ? 'M15 8a5 5 0 0 1 0 8m3-11a9 9 0 0 1 0 14' : 'm16 9 5 6m0-6-5 6');
  clickSound();
  toast(soundEnabled ? 'Sound on. A satisfying little click.' : 'Sound off. A moment of quiet.');
});
$('fullscreen').addEventListener('click', async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch { toast('Fullscreen isn’t available in this view.'); }
});
const dialog = $('shortcut-dialog');
$('shortcuts').addEventListener('click', () => dialog.showModal());
$('close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
window.addEventListener('keydown', event => {
  if (dialog.open || event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); undo(); return; }
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  const face = event.key.toUpperCase();
  if (faces[face]) { event.preventDefault(); if (!event.repeat) turn(face, event.shiftKey || reverse ? -1 : 1); }
  if (event.code === 'Space' && event.target === document.body) { event.preventDefault(); if (!event.repeat) scramble(); }
  if (event.key === '?') dialog.showModal();
});

const raycaster = new THREE.Raycaster();
let pointerDown;
renderer.domElement.addEventListener('pointerdown', event => { pointerDown = { x: event.clientX, y: event.clientY, time: performance.now() }; });
renderer.domElement.addEventListener('pointerup', event => {
  if (!pointerDown || Math.hypot(event.clientX - pointerDown.x, event.clientY - pointerDown.y) > 5 || performance.now() - pointerDown.time > 500) return;
  if (active || mode !== 'play' || event.button !== 0) return;
  const rect = renderer.domElement.getBoundingClientRect();
  raycaster.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1), camera);
  const hit = raycaster.intersectObjects(tiles, false)[0];
  if (!hit) return;
  const normal = hit.object.userData.normal.clone().applyQuaternion(hit.object.parent.quaternion);
  const face = Object.entries(faces).find(([, data]) => data.normal.dot(normal) > 0.9)?.[0];
  if (face) turn(face, event.shiftKey || reverse ? -1 : 1);
});
function resize() {
  const { width, height } = container.getBoundingClientRect();
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(container);
resize();
updateUI();
renderer.setAnimationLoop(now => {
  if (!active && queue.length) beginMove(queue.shift(), now);
  if (active) {
    const t = Math.min(1, (now - active.start) / active.duration);
    const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    active.pivot.rotation[active.axis] = active.angle * eased;
    if (t >= 1) finishMove();
  }
  const elapsed = startTime === null ? frozenTime : performance.now() - startTime;
  const seconds = Math.floor(elapsed / 1000);
  $('timer').textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
  orbit.update();
  renderer.render(scene, camera);
});
