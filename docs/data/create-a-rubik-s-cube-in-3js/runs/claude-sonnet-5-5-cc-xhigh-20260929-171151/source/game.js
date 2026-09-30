import { inverseMove, simplifyMoves } from "./cube.js";

const SCRAMBLE_LENGTH = 22;

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

export function randomScramble(length = SCRAMBLE_LENGTH) {
  const moves = [];
  let lastAxis = -1;
  while (moves.length < length) {
    // Never turn the same axis twice in a row, so no move cancels or merges with the last.
    let axis;
    do axis = Math.floor(Math.random() * 3);
    while (axis === lastAxis);
    const layer = Math.random() < 0.5 ? -1 : 1;
    const turns = [1, -1, 2][Math.floor(Math.random() * 3)];
    moves.push({ axis, layer, turns });
    lastAxis = axis;
  }
  return moves;
}

// Game rules on top of the cube: move history, undo, scramble / solve, the
// move counter, the timer and detecting when the puzzle has been solved.
export class Game {
  constructor(cube, hud, onSolved) {
    this.cube = cube;
    this.hud = hud;
    this.onSolved = onSolved;

    this.history = []; // every move since the last reset; `user` marks the undoable ones
    this.moves = 0;
    this.sinceSolved = 0; // user moves since the cube was last solved
    this.solved = true;
    this.auto = false; // a scramble or solve is playing; input is locked
    this.challenge = false; // a scramble is in progress and the clock is (or will be) running
    this.timerStart = null;
    this.timerEnd = null;

    cube.onIdle = () => this.settle();
    this.refresh();
  }

  get canInteract() {
    return !this.auto && !this.cube.dragging;
  }

  tick(now) {
    if (this.timerStart !== null) this.hud.setTime((this.timerEnd ?? now) - this.timerStart);
  }

  // A turn made by the player. The keyboard passes `animate` so the cube plays
  // it; a finished drag has already been played by the cube itself.
  userMove(move, animate = true) {
    if (animate) this.cube.enqueue(move, "user");
    if (this.solved) {
      // Starting from a solved cube begins a fresh attempt.
      this.moves = 0;
      this.timerStart = this.timerEnd = null;
      this.hud.setTime(0);
    }
    this.history.push({ axis: move.axis, layer: move.layer, turns: move.turns, user: true });
    this.moves++;
    this.sinceSolved++;
    this.solved = false;
    if (this.challenge && this.timerStart === null) this.timerStart = performance.now();
    this.hud.setMoves(this.moves);
    this.refresh();
  }

  undo() {
    const last = this.history[this.history.length - 1];
    if (!this.canInteract || !last?.user) return;
    this.history.pop();
    this.moves = Math.max(0, this.moves - 1);
    this.sinceSolved = Math.max(0, this.sinceSolved - 1);
    this.cube.enqueue(inverseMove(last), "undo");
    this.hud.setMoves(this.moves);
    this.refresh();
  }

  scramble() {
    if (!this.canInteract) return;
    this.hud.hideToast();
    this.challenge = false;
    this.timerStart = this.timerEnd = null;
    this.moves = 0;
    this.sinceSolved = 0;
    this.hud.setMoves(0);
    this.hud.setTime(0);

    this.auto = true;
    for (const move of randomScramble()) {
      this.history.push({ ...move, user: false });
      this.cube.enqueue(move, "scramble", 0.4);
    }
    this.cube.enqueueCall(() => {
      this.auto = false;
      this.challenge = true; // the clock starts with the first move
      this.solved = false;
      this.refresh();
    });
    this.refresh();
  }

  // Plays the whole history backwards, which always leads back to the solved cube.
  solve() {
    if (!this.canInteract || this.solved) return;
    const sequence = simplifyMoves(this.history).reverse().map(inverseMove);
    this.history = [];
    this.challenge = false;
    this.timerStart = this.timerEnd = null;

    this.auto = true;
    const timeScale = clamp(10 / Math.max(1, sequence.length), 0.35, 1);
    for (const move of sequence) this.cube.enqueue(move, "solve", timeScale);
    this.cube.enqueueCall(() => {
      this.auto = false;
      this.solved = true;
      this.moves = 0;
      this.sinceSolved = 0;
      this.hud.setMoves(0);
      this.hud.setTime(0);
      this.refresh();
    });
    this.refresh();
  }

  reset() {
    this.cube.reset();
    this.history = [];
    this.moves = 0;
    this.sinceSolved = 0;
    this.solved = true;
    this.auto = false;
    this.challenge = false;
    this.timerStart = this.timerEnd = null;
    this.hud.hideToast();
    this.hud.setMoves(0);
    this.hud.setTime(0);
    this.refresh();
  }

  // Called whenever the cube comes to rest.
  settle() {
    if (this.auto) return;
    const solved = this.cube.isSolved();
    if (solved === this.solved) return this.refresh();

    this.solved = solved;
    this.refresh();
    if (!solved) return;

    const earned = this.challenge || this.sinceSolved >= 3;
    this.sinceSolved = 0;
    if (this.timerStart !== null) this.timerEnd = performance.now();
    if (earned) {
      const time = this.timerStart !== null ? this.timerEnd - this.timerStart : null;
      this.onSolved({ moves: this.moves, time });
    }
    this.challenge = false;
  }

  refresh() {
    const last = this.history[this.history.length - 1];
    this.hud.setEnabled({
      scramble: !this.auto,
      solve: !this.auto && !this.solved,
      undo: !this.auto && Boolean(last?.user),
    });
  }
}
