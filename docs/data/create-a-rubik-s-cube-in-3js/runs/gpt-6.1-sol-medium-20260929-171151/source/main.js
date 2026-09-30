import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const $ = id => document.getElementById(id);
const mount = $('canvas-mount');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, 1, .1, 100);
const home = new THREE.Vector3(6.8, 5.5, 8.2);
camera.position.copy(home);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.setClearColor(0xf7f7f2, 0);
mount.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.minDistance = 7;
controls.maxDistance = 18;
controls.target.set(0, 0, 0);
scene.add(new THREE.AmbientLight(0xffffff, 2.1));
const key = new THREE.DirectionalLight(0xfff8e9, 3.1);
key.position.set(-3, 8, 5); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.left = -6; key.shadow.camera.right = 6;
key.shadow.camera.top = 6; key.shadow.camera.bottom = -6;
key.shadow.normalBias = .04;
key.shadow.bias = -.0003;
scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 1); fill.position.set(5, 2, -4); scene.add(fill);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.ShadowMaterial({color:0x46503a, opacity:.13}));
floor.rotation.x = -Math.PI/2; floor.position.y = -1.8; floor.receiveShadow = true; scene.add(floor);
const cube = new THREE.Group(); scene.add(cube);
const bodyGeometry = new RoundedBoxGeometry(.96,.96,.96, 3, .085);
const stickerGeometry = new RoundedBoxGeometry(.795,.795,.035, 3, .055);
const bodyMat = new THREE.MeshStandardMaterial({color:0x242b29, roughness:.55});
const colors = {U:0xf0efdf,D:0xf4cc47,L:0xda5b4e,R:0xef8944,F:0x37846a,B:0x518bb0};
const materials = Object.fromEntries(Object.entries(colors).map(([f,c]) => [f,new THREE.MeshStandardMaterial({color:c,roughness:.32,metalness:.02})]));
const faces = {U:{axis:'y',layer:1,sign:-1},D:{axis:'y',layer:-1,sign:1},L:{axis:'x',layer:-1,sign:1},R:{axis:'x',layer:1,sign:-1},F:{axis:'z',layer:1,sign:-1},B:{axis:'z',layer:-1,sign:1}};
let cubies = [], stickers = [], history = [], queue = [], active = null, direction = 1, mode = 'idle';
let elapsed = 0, started = null, moveCount = 0;
function buildCube() {
  cube.clear(); cubies = []; stickers = [];
  for(let x=-1;x<=1;x++) for(let y=-1;y<=1;y++) for(let z=-1;z<=1;z++) {
    if(x===0&&y===0&&z===0) continue;
    const piece = new THREE.Group(); piece.position.set(x,y,z);
    const body = new THREE.Mesh(bodyGeometry,bodyMat); body.castShadow = true; body.receiveShadow = true; piece.add(body);
    for(const [face,def] of Object.entries(faces)) {
      if(({x,y,z})[def.axis] !== def.layer) continue;
      const sticker = new THREE.Mesh(stickerGeometry, materials[face]);
      sticker.position[def.axis] = def.layer * .486;
      if(def.axis==='x') sticker.rotation.y = def.layer*Math.PI/2;
      if(def.axis==='y') sticker.rotation.x = -def.layer*Math.PI/2;
      if(def.axis==='z'&&def.layer===-1) sticker.rotation.y = Math.PI;
      sticker.castShadow = true; sticker.receiveShadow = true;
      piece.add(sticker); stickers.push(sticker);
    }
    cube.add(piece); cubies.push(piece);
  }
}
buildCube();
function solved() {
  const groups = {};
  for(const sticker of stickers) {
    const normal = new THREE.Vector3(0,0,1).applyQuaternion(sticker.getWorldQuaternion(new THREE.Quaternion()));
    let axis = ['x','y','z'].reduce((a,b)=>Math.abs(normal[a])>Math.abs(normal[b])?a:b);
    const f = axis+(normal[axis]>0?'+':'-');
    const color = sticker.material.color.getHex();
    if(groups[f]!==undefined&&groups[f]!==color) return false;
    groups[f]=color;
  }
  return true;
}
function updateUI() {
  $('moves').textContent = moveCount;
  const isSolved = !active && !queue.length && solved();
  $('status').textContent = mode==='scramble'?'Mixing…':mode==='solve'?'Solving…':isSolved?'Solved':'In progress';
  $('status').classList.toggle('mixed', !isSolved);
  $('history').replaceChildren();
  if(!history.length) {const empty=document.createElement('span');empty.className='history-empty';empty.textContent='Every great solve starts with a twist.';$('history').append(empty);}
  else for(const move of history.slice(-24)) {const chip=document.createElement('span');chip.className='move-chip';chip.textContent=move.face+(move.dir===-1?'′':'');$('history').append(chip);}
  $('history').scrollTop=$('history').scrollHeight;
}
function turn(face, dir=direction) {
  if(mode!=='idle') return;
  if(started===null) started=performance.now();
  queue.push({face,dir,type:'manual'});
}
function beginMove(move, now) {
  const def=faces[move.face], pivot=new THREE.Group(); cube.add(pivot);
  const pieces=cubies.filter(p=>Math.round(p.position[def.axis])===def.layer);
  for(const piece of pieces) pivot.attach(piece);
  active={...move,pivot,pieces,axis:def.axis,angle:def.sign*move.dir*Math.PI/2,start:now,duration:move.type==='scramble'?95:move.type==='solve'?115:230};
}
function finishMove() {
  const a=active;
  a.pivot.rotation[a.axis]=a.angle; a.pivot.updateMatrixWorld(true);
  for(const p of a.pieces) {cube.attach(p);p.position.set(Math.round(p.position.x),Math.round(p.position.y),Math.round(p.position.z));p.quaternion.normalize();}
  cube.remove(a.pivot);
  if(a.type==='manual'||a.type==='scramble') {history.push({face:a.face,dir:a.dir});if(a.type==='manual') moveCount++;}
  if(a.type==='undo') {history.pop();moveCount=Math.max(0,moveCount-1);}
  if(a.type==='solve') history.pop();
  active=null;
  if(!queue.length) {
    mode='idle';
    if(solved()&&started!==null) {elapsed+=performance.now()-started;started=null;}
  }
  updateUI();
}
$('scramble').onclick=()=>{
  if(active||queue.length) return;
  elapsed=0;started=null;moveCount=0;mode='scramble';
  let last='';const names=Object.keys(faces);
  for(let i=0;i<20;i++){let face;do{face=names[Math.floor(Math.random()*6)];}while(face===last);last=face;queue.push({face,dir:Math.random()<.5?1:-1,type:'scramble'});}
  updateUI();
};
$('undo').onclick=()=>{if(active||queue.length||!history.length)return;const last=history.at(-1);queue.push({face:last.face,dir:-last.dir,type:'undo'});};
$('solve').onclick=()=>{
  if(active||queue.length||!history.length)return;
  if(started!==null){elapsed+=performance.now()-started;started=null;}
  mode='solve';queue=history.slice().reverse().map(m=>({face:m.face,dir:-m.dir,type:'solve'}));updateUI();
};
$('reset').onclick=()=>{queue=[];active=null;history=[];mode='idle';moveCount=0;elapsed=0;started=null;buildCube();updateUI();};
function setDirection(dir){direction=dir;for(const [id,d] of [['clockwise',1],['counterclockwise',-1]]){$(id).classList.toggle('selected',dir===d);$(id).setAttribute('aria-pressed',String(dir===d));}}
$('clockwise').onclick=()=>setDirection(1);$('counterclockwise').onclick=()=>setDirection(-1);
document.querySelectorAll('[data-face]').forEach(b=>b.onclick=()=>turn(b.dataset.face));
window.addEventListener('keydown',e=>{if($('help').open||e.ctrlKey||e.metaKey||e.altKey||e.target.matches('input,textarea'))return;const face=e.key.toUpperCase();if(faces[face]){e.preventDefault();turn(face,e.shiftKey?-1:1);}});
$('viewReset').onclick=()=>{camera.position.copy(home);controls.target.set(0,0,0);controls.update();};
$('helpButton').onclick=()=>$('help').showModal();$('closeHelp').onclick=$('gotIt').onclick=()=>$('help').close();
const raycaster=new THREE.Raycaster();let down=null;
renderer.domElement.addEventListener('pointerdown',e=>{down={x:e.clientX,y:e.clientY,time:performance.now()};});
renderer.domElement.addEventListener('pointerup',e=>{
  if(!down||Math.hypot(e.clientX-down.x,e.clientY-down.y)>6||performance.now()-down.time>450)return;
  const rect=renderer.domElement.getBoundingClientRect();
  raycaster.setFromCamera(new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1),camera);
  const hit=raycaster.intersectObjects(stickers)[0];if(!hit)return;
  const n=new THREE.Vector3(0,0,1).applyQuaternion(hit.object.getWorldQuaternion(new THREE.Quaternion()));
  const axis=['x','y','z'].reduce((a,b)=>Math.abs(n[a])>Math.abs(n[b])?a:b);
  const face=Object.keys(faces).find(f=>faces[f].axis===axis&&faces[f].layer===Math.sign(n[axis]));
  turn(face,e.shiftKey?-direction:direction);
});
new ResizeObserver(()=>{const w=mount.clientWidth,h=mount.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(mount);
function animate(now){
  requestAnimationFrame(animate);
  if(!active&&queue.length)beginMove(queue.shift(),now);
  if(active){const t=Math.min(1,(now-active.start)/active.duration);const ease=t*t*(3-2*t);active.pivot.rotation[active.axis]=active.angle*ease;if(t===1)finishMove();}
  const ms=elapsed+(started===null?0:now-started), seconds=Math.floor(ms/1000);
  $('timer').innerHTML=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}<span>.${Math.floor(ms/100)%10}</span>`;
  controls.update();renderer.render(scene,camera);
}
updateUI();requestAnimationFrame(animate);
