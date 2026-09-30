import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import styles from './style.js';
const style = document.createElement('style'); style.textContent = styles; document.head.appendChild(style);

document.body.innerHTML = `
<header><a class="brand" href="#"><span class="brand-icon">▦</span> cube lab<span class="brand-dot">.</span></a><div class="header-right"><span class="live-dot"></span> A PLAYGROUND FOR YOUR MIND <span class="version">01 / INTERACTIVE</span></div></header>
<main><section class="intro"><div class="eyebrow">THE CLASSIC. A NEW PERSPECTIVE.</div><h1>A little twist.<br>A lot of possibility<span>.</span></h1><p>Six colors. Forty-three quintillion combinations.<br>One cube, and a little curiosity.</p><div class="intro-footer"><span class="small-cube">◇</span><span>Made to be played with.<br><b>No instructions required. Mostly.</b></span></div></section>
<section class="playground"><div class="scene-top"><span><i class="live-dot"></i> YOUR CUBE</span><span id="state">SOLVED</span></div><div id="viewport"></div><div class="orbit-hint"><span>↔</span> Drag to explore <i>·</i> Scroll to zoom</div><div class="scene-bottom"><span>3 × 3 × 3</span><span>THE ORIGINAL, SINCE 1974</span></div></section>
<aside class="panel"><div class="panel-heading"><span>MAKE YOUR MOVE</span><span>↗</span></div><p>Pick a face. Give it a spin.</p><div class="direction"><button class="selected" id="cw">↻ Clockwise</button><button id="ccw">↺ Counterclockwise</button></div><div class="face-grid">${[['U','Top','white'],['F','Front','green'],['R','Right','red'],['D','Bottom','yellow'],['B','Back','blue'],['L','Left','orange']].map(([key,label,color])=>`<button class="face" data-face="${key}"><span class="swatch ${color}"></span><span>${label}</span><kbd>${key}</kbd></button>`).join('')}</div><div class="divider"></div><button class="scramble" id="scramble">Shuffle things up <span>⤨</span></button><div class="secondary"><button id="undo">↶ Undo</button><button id="reset">⟲ Reset</button></div><div class="stats"><div><span>MOVES</span><strong id="moves">00</strong></div><div><span>SESSION</span><strong id="timer">00:00</strong></div></div><div class="tip"><span>✳</span><p>A fresh perspective helps.<br>Rotate the cube to see every side.</p></div></aside></main><footer><span>LESS SCROLLING. MORE SOLVING.</span><span>Take your time. Enjoy the process. <span class="footer-mark">✳</span></span></footer>`;

const viewport = document.querySelector('#viewport');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, .1, 100);
camera.position.set(6,5.3,7.5);
const renderer = new THREE.WebGLRenderer({antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
viewport.appendChild(renderer.domElement);
const controls = new OrbitControls(camera,renderer.domElement); controls.enableDamping=true; controls.enablePan=false; controls.minDistance=6; controls.maxDistance=16; controls.maxPolarAngle=Math.PI*.83; controls.target.set(0,0,0);
scene.add(new THREE.AmbientLight(0xffffff,2.1));
const light = new THREE.DirectionalLight(0xffffff,3.3);light.position.set(3,8,6);scene.add(light);
const fill=new THREE.DirectionalLight(0xffffff,1.4);fill.position.set(-6,2,-4);scene.add(fill);
const cube=new THREE.Group(); scene.add(cube);
const cubies=[];
const dark=new THREE.MeshStandardMaterial({color:0x202323,roughness:.45});
const colors=[0xe74d3e,0xff9235,0xf8f6ea,0xf5cb3f,0x23a878,0x3882d7];
const mats=colors.map(c=>new THREE.MeshStandardMaterial({color:c,roughness:.35}));
const bodyGeometry=new THREE.BoxGeometry(.97,.97,.97);
const shape=new THREE.Shape(); const s=.425,r=.07;shape.moveTo(-s+r,-s);shape.lineTo(s-r,-s);shape.quadraticCurveTo(s,-s,s,-s+r);shape.lineTo(s,s-r);shape.quadraticCurveTo(s,s,s-r,s);shape.lineTo(-s+r,s);shape.quadraticCurveTo(-s,s,-s,s-r);shape.lineTo(-s,-s+r);shape.quadraticCurveTo(-s,-s,-s+r,-s);
const tileGeometry=new THREE.ShapeGeometry(shape);
function build(){cube.clear();cubies.length=0;for(let x=-1;x<=1;x++)for(let y=-1;y<=1;y++)for(let z=-1;z<=1;z++){const c=new THREE.Group();c.position.set(x,y,z);c.add(new THREE.Mesh(bodyGeometry,dark));const sides=[x===1,x===-1,y===1,y===-1,z===1,z===-1];sides.forEach((yes,i)=>{if(!yes)return;const tile=new THREE.Mesh(tileGeometry,mats[i]);if(i===0){tile.rotation.y=Math.PI/2;tile.position.x=.488;}if(i===1){tile.rotation.y=-Math.PI/2;tile.position.x=-.488;}if(i===2){tile.rotation.x=-Math.PI/2;tile.position.y=.488;}if(i===3){tile.rotation.x=Math.PI/2;tile.position.y=-.488;}if(i===4)tile.position.z=.488;if(i===5){tile.rotation.y=Math.PI;tile.position.z=-.488;}c.add(tile);});cube.add(c);cubies.push(c);}}
build();
const shadowCanvas=document.createElement('canvas');shadowCanvas.width=256;shadowCanvas.height=256;const ctx=shadowCanvas.getContext('2d');const gradient=ctx.createRadialGradient(128,128,10,128,128,125);gradient.addColorStop(0,'rgba(30,40,30,.22)');gradient.addColorStop(1,'rgba(30,40,30,0)');ctx.fillStyle=gradient;ctx.fillRect(0,0,256,256);const shadow=new THREE.Mesh(new THREE.PlaneGeometry(7,7),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(shadowCanvas),transparent:true,depthWrite:false}));shadow.rotation.x=-Math.PI/2;shadow.position.y=-2.2;scene.add(shadow);
const faces={U:['y',1],D:['y',-1],R:['x',1],L:['x',-1],F:['z',1],B:['z',-1]};
let direction=1,history=[],queue=[],active=null,startTime=null;
function update(){document.querySelector('#moves').textContent=String(history.length).padStart(2,'0');document.querySelector('#undo').disabled=!history.length||!!active||!!queue.length;document.querySelector('#state').textContent=history.length?'IN PROGRESS':'SOLVED';}
function turn(face,dir=direction,record=true){queue.push({face,dir,record});if(!startTime)startTime=Date.now();}
function begin(move){const [axis,layer]=faces[move.face];const pivot=new THREE.Group();cube.add(pivot);cubies.filter(c=>Math.round(c.position[axis])===layer).forEach(c=>pivot.attach(c));active={...move,axis,pivot,start:performance.now(),angle:-layer*move.dir*Math.PI/2};update();}
document.querySelectorAll('.face').forEach(b=>b.onclick=()=>turn(b.dataset.face));
for(const [id,d]of [['cw',1],['ccw',-1]])document.querySelector('#'+id).onclick=()=>{direction=d;document.querySelector('#cw').classList.toggle('selected',d===1);document.querySelector('#ccw').classList.toggle('selected',d===-1);};
document.querySelector('#scramble').onclick=()=>{if(active||queue.length)return;let prev='';for(let i=0;i<20;i++){let f;do{f=Object.keys(faces)[Math.floor(Math.random()*6)];}while(f===prev);prev=f;turn(f,Math.random()>.5?1:-1);}};
document.querySelector('#undo').onclick=()=>{if(active||queue.length||!history.length)return;const m=history.pop();turn(m.face,-m.dir,false);update();};
document.querySelector('#reset').onclick=()=>{queue=[];active=null;history=[];startTime=null;build();update();};
window.addEventListener('keydown',e=>{if(faces[e.key.toUpperCase()]&&!e.ctrlKey&&!e.metaKey){e.preventDefault();turn(e.key.toUpperCase(),e.shiftKey?-1:direction);}});
new ResizeObserver(()=>{const {width,height}=viewport.getBoundingClientRect();renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();}).observe(viewport);
function animate(now){requestAnimationFrame(animate);if(!active&&queue.length)begin(queue.shift());if(active){const t=Math.min((now-active.start)/(queue.length?160:320),1);active.pivot.rotation[active.axis]=active.angle*(t*t*(3-2*t));if(t===1){const m=active;[...m.pivot.children].forEach(c=>{cube.attach(c);c.position.set(Math.round(c.position.x),Math.round(c.position.y),Math.round(c.position.z));});cube.remove(m.pivot);if(m.record)history.push({face:m.face,dir:m.dir});active=null;update();}}const secs=startTime?Math.floor((Date.now()-startTime)/1000):0;document.querySelector('#timer').textContent=String(Math.floor(secs/60)).padStart(2,'0')+':'+String(secs%60).padStart(2,'0');controls.update();renderer.render(scene,camera);}update();requestAnimationFrame(animate);
