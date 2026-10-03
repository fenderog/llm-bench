// A run's output on screen. The sandbox-critical code lives here and only here: games and pages are embedded only by
// sandboxedGame() (never allow-same-origin), model-made images and SVGs only through mediaElement() (<img>, ADR-0004).

import { el, badge } from "./dom.js";
import { fmtBytes } from "./fmt.js";

// What differs per kind in the UI: its name, the run page's output tab, what a run without output says,
// and the badge for a kind step that failed. Anything else (kinds the viewer doesn't know) reads as a game.
const KIND_UI = {
  godot: { label: "Game", tab: "Game", none: "No playable build recorded for this run.", failed: "export failed" },
  media: { label: "Media", tab: "Output", none: "No output files recorded for this run.", failed: "output failed" },
  web: { label: "Web", tab: "Page", none: "No packaged page recorded for this run.", failed: "packaging failed" },
};

export function kindUi(kind) {
  return KIND_UI[kind] ?? KIND_UI.godot;
}

export function outputOk(run) {
  return run.output?.ok === true;
}

// true / false once the output was checked (booted, loaded offline, files readable), null when it wasn't.
export function outputVerified(run) {
  return run.output?.verified ?? null;
}

// A badge for a run whose agent finished but whose output step failed ("export failed"), else null.
export function outputBadge(run) {
  return run.output && !run.output.ok ? badge(kindUi(run.kind).failed, "bad") : null;
}

// The one place games are embedded: sandboxed without allow-same-origin, so game
// code gets an opaque origin and can't touch this site's storage or cookies.
export function sandboxedGame(entryUrl) {
  return el("iframe", {
    attrs: { src: entryUrl, sandbox: "allow-scripts allow-pointer-lock", allow: "fullscreen; autoplay; gamepad" },
  });
}

// Builds a click-to-play `.game-frame`: an overlay (thumb + play button,
// carrying `data-play`) that is replaced in place by a sandboxed iframe on
// click. Games never boot on their own. Returns the frame element.
export function buildGameFrame(entryUrl, thumbUrl) {
  const frame = el("div", { class: "game-frame" });
  const overlay = el(
    "button",
    {
      class: "play-overlay",
      attrs: { type: "button", "data-play": "1", "aria-label": "Play" },
    },
    [el("span", { class: "play-icon", text: "▶" }), el("span", { class: "play-label", text: "Click to play" })]
  );
  if (thumbUrl) overlay.style.backgroundImage = `url("${thumbUrl}")`;
  overlay.addEventListener("click", () => overlay.replaceWith(sandboxedGame(entryUrl)));
  frame.append(overlay);
  return frame;
}

// One media output (run.media item). Model-made SVGs may contain scripts, so every image,
// SVG included, is shown through <img> (which never runs them) and never inlined or framed.
// Videos never autoplay: like games, they start on an explicit click.
export function mediaElement(item, base) {
  if (item.type === "video") {
    return el("video", {
      attrs: { src: base + item.path, poster: item.poster ? base + item.poster : null, controls: "", preload: "none", playsinline: "", loop: "" },
    });
  }
  return el("img", { attrs: { src: base + item.path, alt: "", loading: "lazy" } });
}

// A run's media items as captioned figures (file name, size, duration) with download links.
// Downloads use the `download` attribute so an SVG is saved, never opened as a page here.
export function mediaGallery(items, base) {
  const grid = el("div", { class: "media-grid" });
  for (const item of items || []) {
    const name = item.path.split("/").pop();
    const dims = item.width && item.height ? `${item.width}×${item.height}` : null;
    const dur = item.duration_s != null ? `${Number(item.duration_s).toFixed(1)}s` : null;
    const caption = el("figcaption", {}, [
      el("span", { text: [name, dims, dur, fmtBytes(item.bytes)].filter(Boolean).join(" · ") }),
      el("a", { text: "download", attrs: { href: base + item.path, download: name } }),
    ]);
    grid.append(el("figure", { class: "media-item" }, [el("div", { class: "media-box" }, [mediaElement(item, base)]), caption]));
  }
  return grid;
}

// A run's output wherever it is shown, as an array of nodes: the kind step's own error (if any), then
// the media gallery, the game or page in the sandbox, or the "no output" message.
// Games and pages start on a click (a thumbnail with a play button) unless `autoplay` (the click was
// opening the row or the window); `frameClass` is the wrapper of an autoplaying frame.
export function renderOutput(run, base, { autoplay = false, frameClass = "game-frame" } = {}) {
  const out = run.output;
  const nodes = out?.error ? [el("p", { class: "run-error", text: out.error })] : [];
  if (!out?.ok) return [...nodes, el("p", { class: "msg", text: kindUi(run.kind).none })];
  if (out.kind === "media") return [...nodes, mediaGallery(out.items, base)];
  const entry = base + out.entry;
  return [...nodes, autoplay ? el("div", { class: frameClass }, [sandboxedGame(entry)]) : buildGameFrame(entry, run.thumb ? base + run.thumb : null)];
}

// Whether a run's output is a game or page that has its own full-screen window (play.html).
export function isPlayable(run) {
  return outputOk(run) && run.output.kind !== "media";
}
