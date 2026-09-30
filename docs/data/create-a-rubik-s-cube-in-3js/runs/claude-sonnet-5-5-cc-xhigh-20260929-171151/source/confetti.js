// A tiny 2D confetti burst drawn on a canvas that sits above the 3D scene.
export class Confetti {
  constructor(canvas, colors) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.colors = colors;
    this.parts = [];
    this.running = false;
    this._last = 0;
    this._frame = this._frame.bind(this);
    this.reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  resize(width, height, dpr) {
    this.canvas.width = Math.round(width * dpr);
    this.canvas.height = Math.round(height * dpr);
    this.dpr = dpr;
    this.width = width;
    this.height = height;
  }

  burst(count = 160) {
    if (this.reducedMotion) return;
    const { width, height } = this;
    for (let i = 0; i < count; i++) {
      const fromLeft = i % 2 === 0;
      const angle = (fromLeft ? -0.35 : -Math.PI + 0.35) + (Math.random() - 0.5) * 0.9;
      const speed = 500 + Math.random() * 700;
      this.parts.push({
        x: fromLeft ? width * 0.12 : width * 0.88,
        y: height * 0.75,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        w: 6 + Math.random() * 7,
        h: 4 + Math.random() * 5,
        rot: Math.random() * Math.PI * 2,
        spin: (Math.random() - 0.5) * 14,
        flip: Math.random() * Math.PI * 2,
        color: this.colors[Math.floor(Math.random() * this.colors.length)],
        life: 2.6 + Math.random() * 1.4,
        age: 0,
      });
    }
    if (!this.running) {
      this.running = true;
      this._last = performance.now();
      requestAnimationFrame(this._frame);
    }
  }

  _frame(now) {
    const dt = Math.min(0.05, (now - this._last) / 1000);
    this._last = now;
    const { ctx, dpr } = this;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);

    this.parts = this.parts.filter((p) => p.age < p.life && p.y < this.height + 40);
    for (const p of this.parts) {
      p.age += dt;
      p.vy += 1100 * dt;
      p.vx *= 1 - 1.4 * dt;
      p.vy *= 1 - 0.9 * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.rot += p.spin * dt;
      p.flip += 9 * dt;

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.scale(1, Math.cos(p.flip));
      ctx.globalAlpha = Math.min(1, (p.life - p.age) * 2);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    }

    if (this.parts.length) {
      requestAnimationFrame(this._frame);
    } else {
      this.running = false;
      ctx.clearRect(0, 0, this.width, this.height);
    }
  }
}
