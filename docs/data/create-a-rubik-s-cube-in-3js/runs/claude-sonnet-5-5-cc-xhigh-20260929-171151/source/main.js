import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { Confetti } from "./confetti.js";
import { FACE_COLORS, RubiksCube } from "./cube.js";
import { Game } from "./game.js";
import { formatTime, Hud } from "./hud.js";
import { setupInput } from "./input.js";

const FOV = 34;
const CUBE_RADIUS = Math.sqrt(3) * 1.5; // bounding sphere of the 3x3x3 cube
const FLOOR_Y = -1.65;

const easeOutBack = (t) => 1 + 2.70158 * Math.pow(t - 1, 3) + 1.70158 * Math.pow(t - 1, 2);

function createGlowTexture() {
  const size = 256;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "rgba(255,255,255,0.30)");
  g.addColorStop(0.45, "rgba(255,255,255,0.10)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(c);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function main() {
  const canvas = document.getElementById("scene");
  const hud = new Hud();

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch (err) {
    console.error(err);
    document.getElementById("fallback").hidden = false;
    return;
  }
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.VSMShadowMap;

  // ---- scene ---------------------------------------------------------------

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 100);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.75;
  pmrem.dispose();

  scene.add(new THREE.HemisphereLight(0xffffff, 0x556080, 0.35));

  const key = new THREE.DirectionalLight(0xffffff, 1.3);
  key.position.set(-2.5, 10, 3.5);
  key.castShadow = true;
  key.shadow.mapSize.set(512, 512);
  Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: 2, far: 24 });
  key.shadow.camera.updateProjectionMatrix();
  key.shadow.radius = 7;
  key.shadow.blurSamples = 20;
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.02;
  scene.add(key);

  // A soft light riding along with the camera keeps the faces you look at readable from any side.
  const fill = new THREE.DirectionalLight(0xffffff, 0.8);
  fill.position.set(-3, 2, 5);
  camera.add(fill);
  scene.add(camera);

  const glow = new THREE.Mesh(
    new THREE.PlaneGeometry(18, 18),
    new THREE.MeshBasicMaterial({ map: createGlowTexture(), transparent: true, depthWrite: false, toneMapped: false }),
  );
  glow.rotation.x = -Math.PI / 2;
  glow.position.y = FLOOR_Y - 0.01;
  scene.add(glow);

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.32 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = FLOOR_Y;
  floor.receiveShadow = true;
  scene.add(floor);

  const cube = new RubiksCube();
  scene.add(cube.group);

  // ---- camera and controls ---------------------------------------------------

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.09;
  controls.rotateSpeed = 0.9;
  controls.enablePan = false;
  controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_ROTATE };

  const confettiColors = Object.values(FACE_COLORS).map((c) => "#" + c.toString(16).padStart(6, "0"));
  const confetti = new Confetti(document.getElementById("confetti"), confettiColors);

  // Distance at which the whole cube fits the smaller side of the window.
  const fitDistance = (aspect) => {
    const vHalf = THREE.MathUtils.degToRad(FOV) / 2;
    const half = Math.min(vHalf, Math.atan(Math.tan(vHalf) * aspect));
    return (CUBE_RADIUS / Math.sin(half)) * (aspect < 1 ? 1.15 : 1.4);
  };

  let fit = 0;
  const resize = () => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    confetti.resize(w, h, dpr);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();

    // Keep the user's zoom level (relative to "fits the window") across resizes.
    const zoom = fit ? camera.position.distanceTo(controls.target) / fit : 1;
    fit = fitDistance(camera.aspect);
    controls.minDistance = fit * 0.55;
    controls.maxDistance = fit * 1.8;
    camera.position.sub(controls.target).setLength(fit * zoom).add(controls.target);
  };
  camera.position.set(4.7, 4.1, 5.6);
  resize();
  window.addEventListener("resize", resize);

  // ---- game ------------------------------------------------------------------

  const game = new Game(cube, hud, ({ moves, time }) => {
    confetti.burst();
    const stats = [`${moves} ${moves === 1 ? "move" : "moves"}`];
    if (time !== null) stats.unshift(formatTime(time));
    hud.toast("Solved!", stats.join(" · "));
  });

  hud.buttons.scramble.addEventListener("click", () => game.scramble());
  hud.buttons.solve.addEventListener("click", () => game.solve());
  hud.buttons.undo.addEventListener("click", () => game.undo());
  hud.buttons.reset.addEventListener("click", () => {
    game.reset();
    pop(0.86);
  });
  hud.speed.addEventListener("input", () => {
    cube.speed = Number(hud.speed.value);
  });

  setupInput({ canvas, camera, controls, cube, game, hud });

  // ---- animation loop --------------------------------------------------------

  let popFrom = 0.35;
  let popT = 0;
  function pop(from) {
    popFrom = from;
    popT = 0;
  }

  let last = performance.now();
  renderer.setAnimationLoop((now) => {
    const dt = Math.min(0.05, Math.max(0, (now - last) / 1000));
    last = now;

    cube.update(dt);
    game.tick(now);

    if (popT < 1) {
      popT = Math.min(1, popT + dt / 0.6);
      cube.group.scale.setScalar(popFrom + (1 - popFrom) * easeOutBack(popT));
    }

    controls.update();
    renderer.render(scene, camera);
  });
}

main();
