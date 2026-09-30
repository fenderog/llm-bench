const $ = (id) => document.getElementById(id);

export function formatTime(ms) {
  const total = Math.floor(ms / 1000);
  const s = String(total % 60).padStart(2, "0");
  const m = Math.floor(total / 60) % 60;
  const h = Math.floor(total / 3600);
  return h ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
}

// Thin wrapper around the page's DOM controls.
export class Hud {
  constructor() {
    this.moves = $("moves");
    this.time = $("time");
    this.toastEl = $("toast");
    this.hint = $("hint");
    this.help = $("help");
    this.helpToggle = $("help-toggle");
    this.buttons = {
      scramble: $("scramble"),
      solve: $("solve"),
      undo: $("undo"),
      reset: $("reset"),
    };
    this.speed = $("speed");
    this._toastTimer = 0;

    this.helpToggle.addEventListener("click", () => this.toggleHelp());
  }

  setMoves(n) {
    this.moves.textContent = String(n);
  }

  setTime(ms) {
    const text = formatTime(ms);
    if (this.time.textContent !== text) this.time.textContent = text;
  }

  setEnabled({ scramble, solve, undo }) {
    this.buttons.scramble.disabled = !scramble;
    this.buttons.solve.disabled = !solve;
    this.buttons.undo.disabled = !undo;
  }

  hideHint() {
    this.hint.classList.add("hidden");
  }

  toggleHelp(open = this.help.hidden) {
    this.help.hidden = !open;
    this.helpToggle.setAttribute("aria-expanded", String(open));
  }

  toast(title, detail, duration = 4500) {
    this.toastEl.replaceChildren(title);
    if (detail) {
      const small = document.createElement("small");
      small.textContent = detail;
      this.toastEl.append(small);
    }
    this.toastEl.classList.add("show");
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => this.hideToast(), duration);
  }

  hideToast() {
    clearTimeout(this._toastTimer);
    this.toastEl.classList.remove("show");
  }
}
