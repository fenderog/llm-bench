import * as THREE from 'three';

const LIFETIME = 3.2;
const GRAVITY = 9;

/** A burst of sticker-coloured confetti, drawn as one instanced mesh. */
export class Confetti {
  constructor(scene, colors, count = 320) {
    this.count = count;
    this.life = 0;
    this.mesh = new THREE.InstancedMesh(
      new THREE.PlaneGeometry(0.14, 0.22),
      new THREE.MeshStandardMaterial({ side: THREE.DoubleSide, roughness: 0.5 }),
      count,
    );
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.mesh.frustumCulled = false;
    this.mesh.visible = false;

    const color = new THREE.Color();
    for (let i = 0; i < count; i++) this.mesh.setColorAt(i, color.set(colors[i % colors.length]));

    this.particles = Array.from({ length: count }, () => ({
      position: new THREE.Vector3(),
      velocity: new THREE.Vector3(),
      quaternion: new THREE.Quaternion(),
      spinAxis: new THREE.Vector3(),
      spin: 0,
    }));
    this.dummy = new THREE.Object3D();
    this.step = new THREE.Quaternion();
    scene.add(this.mesh);
  }

  burst(cubeSize) {
    const scale = cubeSize / 3;
    for (const p of this.particles) {
      const dir = new THREE.Vector3().randomDirection();
      dir.y = Math.abs(dir.y) * 0.8 + 0.2;
      dir.normalize();
      p.position.copy(dir).multiplyScalar(cubeSize * 0.45);
      p.velocity.copy(dir).multiplyScalar((5 + Math.random() * 6) * scale);
      p.spinAxis.randomDirection();
      p.spin = 4 + Math.random() * 10;
      p.quaternion.setFromAxisAngle(p.spinAxis, Math.random() * Math.PI * 2);
    }
    this.life = LIFETIME;
    this.mesh.visible = true;
  }

  update(dt) {
    if (!this.mesh.visible) return;
    this.life -= dt;
    if (this.life <= 0) {
      this.mesh.visible = false;
      return;
    }
    const fade = Math.min(1, this.life / 0.8);
    this.particles.forEach((p, i) => {
      p.velocity.y -= GRAVITY * dt;
      p.velocity.multiplyScalar(1 - 1.6 * dt);
      p.position.addScaledVector(p.velocity, dt);
      p.quaternion.multiply(this.step.setFromAxisAngle(p.spinAxis, p.spin * dt));
      this.dummy.position.copy(p.position);
      this.dummy.quaternion.copy(p.quaternion);
      this.dummy.scale.setScalar(fade);
      this.dummy.updateMatrix();
      this.mesh.setMatrixAt(i, this.dummy.matrix);
    });
    this.mesh.instanceMatrix.needsUpdate = true;
  }
}
