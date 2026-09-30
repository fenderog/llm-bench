import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RubiksCube, FACE_COLORS, invertMove } from './cube.js';
import { DragController } from './drag.js';
import { Confetti } from './confetti.js';
import { formatMove, generateScramble, keyMove, mergeMoves, viewFrame } from './notation.js';

const SCRAMBLE_LENGTH = { 2: 11, 3: 22, 4: 40, 5: 60 };
const SCRAMBLE_TURN_MS = 55;

const $ = (id) => document.getElementById(id);
const ui = {
  app: $('app'),
  time: $('time'),
  moves: $('moves'),
  scramble: $('scramble'),
  toast: $('toast'),
  help: $('help'),
  undo: $('btn-undo'),
  solve: $('btn-solve'),
  sizes: [...document.querySelectorAll('[data-size]')],
};

// ---------------------------------------------------------------------------------------------
// Scene

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.domElement.id = 'scene';
ui.app.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.85;

const keyLight = new THREE.DirectionalLight(0xffffff, 1.3);
keyLight.position.set(5, 9, 7);
const rimLight = new THREE.DirectionalLight(0xa8bcff, 0.5);
rimLight.position.set(-6, -4, -5);
scene.add(keyLight, rimLight);

const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0.62, 0.55, 1);

const cube = new RubiksCube();
scene.add(cube.group);
const confetti = new Confetti(scene, FACE_COLORS);

// Created before OrbitControls so layer drags can claim the pointer first.
const drag = new DragController(renderer.domElement, camera, cube, {
  onTurn: (move) => recordMove(move, 'user'),
  onPress: stopIntroSpin,
});

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.enablePan = false;
controls.rotateSpeed = 0.9;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.7;
drag.controls = controls;

/** Camera distance at which a cube of this size fits the viewport with some margin. */
function fitDistance(size) {
  const radius = size * 0.5 * Math.sqrt(3);
  const vHalf = THREE.MathUtils.degToRad(camera.fov / 2);
  const hHalf = Math.atan(Math.tan(vHalf) * camera.aspect);
  return (radius / Math.sin(Math.min(vHalf, hHalf))) * 1.15;
}

/** Frames the cube; `zoom` is the camera distance relative to the snug fit. */
function fitCamera(size, zoom = 1) {
  const distance = fitDistance(size);
  camera.position.setLength(distance * zoom);
  controls.minDistance = size * 0.5 * Math.sqrt(3) * 1.3;
  controls.maxDistance = distance * 2.5;
  controls.update();
}

function stopIntroSpin() {
  controls.autoRotate = false;
}

window.addEventListener('resize', () => {
  const zoom = camera.position.length() / fitDistance(cube.size);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  fitCamera(cube.size, zoom);
});

// ---------------------------------------------------------------------------------------------
// Game state
//
// phase: idle (free play) → scrambling → ready (inspection) → solving (timer running) → idle
//        or autosolve while the Solve button rewinds the history.

const state = {
  phase: 'idle',
  history: [], // { move, kind } in the order the moves were issued
  moves: 0,
  timerStart: 0,
  elapsed: 0,
  depth: 1, // inner-layer prefix typed with the number keys
};

const isRotation = (move) => move.layers.length === cube.size;
const locked = () => drag.active || state.phase === 'scrambling' || state.phase === 'autosolve';

function recordMove(move, kind) {
  state.history.push({ move, kind });
  if (kind === 'user' && !isRotation(move)) {
    state.moves++;
    if (state.phase === 'ready') {
      state.phase = 'solving';
      state.timerStart = performance.now();
    }
  }
  refreshUI();
}

function perform(move, kind, duration) {
  cube.enqueue(move, duration);
  recordMove(move, kind);
}

function resetSession() {
  state.phase = 'idle';
  state.history = [];
  state.moves = 0;
  state.elapsed = 0;
  ui.scramble.hidden = true;
  hideToast();
  refreshUI();
}

function reset(size = cube.size) {
  if (drag.active) return;
  const resized = size !== cube.size;
  cube.build(size);
  if (resized) fitCamera(size);
  resetSession();
}

function scramble() {
  if (drag.active) return;
  cube.build(cube.size); // always scramble from solved so the listed sequence reproduces it
  resetSession();
  const moves = generateScramble(cube.size, SCRAMBLE_LENGTH[cube.size]);
  state.phase = 'scrambling';
  for (const move of moves) perform(move, 'scramble', SCRAMBLE_TURN_MS);
  ui.scramble.textContent = moves.map((m) => formatMove(m, cube.size)).join(' ');
  ui.scramble.hidden = false;
  refreshUI();
}

function undo() {
  if (locked()) return;
  const last = state.history.pop();
  if (!last) return;
  cube.enqueue(invertMove(last.move));
  if (last.kind === 'user' && !isRotation(last.move)) state.moves = Math.max(0, state.moves - 1);
  refreshUI();
}

/** Plays the whole history backwards (with trivial cancellations merged). */
function solve() {
  if (locked() || state.history.length === 0) return;
  const moves = mergeMoves(state.history.map((h) => invertMove(h.move)).reverse());
  state.history = [];
  if (state.phase === 'solving') state.elapsed = performance.now() - state.timerStart;
  ui.scramble.hidden = true;
  state.phase = moves.length > 0 ? 'autosolve' : 'idle';
  const duration = THREE.MathUtils.clamp(3000 / moves.length, 60, 160);
  for (const move of moves) cube.enqueue(move, duration);
  refreshUI();
}

cube.onIdle = () => {
  const solved = cube.isSolved();
  if (state.phase === 'scrambling') {
    state.phase = solved ? 'idle' : 'ready';
    if (!solved) showToast('Scrambled: the timer starts on your first turn');
  } else if (solved) {
    if (state.phase === 'solving') {
      state.elapsed = performance.now() - state.timerStart;
      showToast(`Solved in ${formatTime(state.elapsed)} · ${state.moves} moves`, 6000);
      confetti.burst(cube.size);
    }
    state.phase = 'idle';
    state.history = [];
    ui.scramble.hidden = true;
  }
  refreshUI();
};

// ---------------------------------------------------------------------------------------------
// UI

function formatTime(ms) {
  const cs = Math.floor(Math.max(0, ms) / 10);
  const minutes = Math.floor(cs / 6000);
  const seconds = Math.floor(cs / 100) % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}.${String(cs % 100).padStart(2, '0')}`;
}

function refreshUI() {
  ui.moves.textContent = state.moves;
  if (state.phase !== 'solving') ui.time.textContent = formatTime(state.elapsed);
  ui.time.classList.toggle('running', state.phase === 'solving');
  ui.time.classList.toggle('armed', state.phase === 'ready');
  ui.undo.disabled = state.history.length === 0;
  ui.solve.disabled = state.history.length === 0;
  for (const button of ui.sizes) button.classList.toggle('active', Number(button.dataset.size) === cube.size);
}

let toastTimer = 0;
function showToast(text, ms = 3000) {
  ui.toast.textContent = text;
  ui.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(hideToast, ms);
}
function hideToast() {
  ui.toast.hidden = true;
}

function toggleHelp(show = ui.help.hidden) {
  ui.help.hidden = !show;
}

function onClick(element, handler) {
  element.addEventListener('click', () => {
    element.blur();
    stopIntroSpin();
    handler();
  });
}
onClick($('btn-scramble'), scramble);
onClick(ui.undo, undo);
onClick(ui.solve, solve);
onClick($('btn-reset'), () => reset());
onClick($('btn-help'), () => toggleHelp());
onClick($('btn-help-close'), () => toggleHelp(false));
for (const button of ui.sizes) onClick(button, () => reset(Number(button.dataset.size)));

let depthTimer = 0;
window.addEventListener('keydown', (e) => {
  if (e.repeat) return;
  stopIntroSpin();

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
    e.preventDefault();
    undo();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === 'Backspace') {
    e.preventDefault();
    undo();
    return;
  }
  if (e.key === '?') return toggleHelp();
  if (e.key === 'Escape') return toggleHelp(false);

  if (/^[1-9]$/.test(e.key)) {
    state.depth = Number(e.key);
    clearTimeout(depthTimer);
    depthTimer = setTimeout(() => (state.depth = 1), 1500);
    return;
  }

  const move = keyMove(e.key.toUpperCase(), e.shiftKey, state.depth, cube.size, viewFrame(camera, controls.target));
  if (!move) return;
  e.preventDefault();
  state.depth = 1;
  if (locked()) return;
  perform(move, 'user');
});

// ---------------------------------------------------------------------------------------------
// Start

cube.build(3);
fitCamera(3);
refreshUI();

let lastFrame = performance.now();
renderer.setAnimationLoop(() => {
  const now = performance.now();
  const dt = Math.min(0.05, (now - lastFrame) / 1000);
  lastFrame = now;

  cube.update(now);
  controls.update(dt);
  confetti.update(dt);
  if (state.phase === 'solving') ui.time.textContent = formatTime(now - state.timerStart);

  renderer.render(scene, camera);
});
