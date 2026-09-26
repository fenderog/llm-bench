"""Godot web-export engine dedupe and index.html rewrite. See SPEC.md "Godot engine dedupe"
(logic proven in ../spike/build.py)."""

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from .util import BenchError

# Order matters: sha12 is over these four files' bytes concatenated in this order.
ENGINE_SUFFIXES = [".wasm", ".js", ".audio.worklet.js", ".audio.position.worklet.js"]
ENGINE_NAMES = {suf: "godot" + suf for suf in ENGINE_SUFFIXES}

CONFIG_RE = re.compile(r"const GODOT_CONFIG = (\{.*?\});")


def engine_hash(wasm_dir):
    h = hashlib.sha256()
    for suf in ENGINE_SUFFIXES:
        h.update((wasm_dir / f"index{suf}").read_bytes())
    return h.hexdigest()[:12]


def _threads_enabled(wasm_dir, manifest):
    if manifest.get("threads"):
        return True
    html = (wasm_dir / "index.html").read_text(encoding="utf-8")
    return bool(re.search(r"GODOT_THREADS_ENABLED\s*=\s*true", html))


def stage_game(wasm_dir, stage_game_dir, docs_root, slug, run_id, allow_threads, known_engines):
    """Copy the export (minus engine files) into stage_game_dir and rewrite index.html.

    Returns (game_dict, sha12, engine_files_or_None). engine_files is a {name: bytes} dict
    when this sha12 hasn't been seen (on disk or earlier in this import) and so needs storing.
    """
    manifest_path = wasm_dir / "export-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    threads = _threads_enabled(wasm_dir, manifest)
    if threads and not allow_threads:
        raise BenchError(f"{wasm_dir}: export has threads enabled; pass --allow-threads to allow it")

    sha12 = engine_hash(wasm_dir)
    is_new = sha12 not in known_engines and not (docs_root / "engines" / sha12).is_dir()
    engine_files = None
    if is_new:
        engine_files = {ENGINE_NAMES[suf]: (wasm_dir / f"index{suf}").read_bytes() for suf in ENGINE_SUFFIXES}

    skip = {f"index{suf}" for suf in ENGINE_SUFFIXES} | {"export-manifest.json", "verification"}
    stage_game_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(wasm_dir.iterdir()):
        if f.name in skip or not f.is_file():
            continue
        shutil.copy(f, stage_game_dir / f.name)

    final_game_dir = Path("data") / slug / "runs" / run_id / "game"
    rel = os.path.relpath(Path("engines") / sha12 / "godot", final_game_dir)

    html_path = stage_game_dir / "index.html"
    html = html_path.read_text(encoding="utf-8")
    html = html.replace('<script src="index.js"></script>', f'<script src="{rel}.js"></script>')
    m = CONFIG_RE.search(html)
    if not m:
        raise BenchError(f"{html_path}: GODOT_CONFIG not found")
    cfg = json.loads(m.group(1))
    cfg["executable"] = rel
    cfg["mainPack"] = "index.pck"
    cfg["fileSizes"] = {(f"{rel}.wasm" if k == "index.wasm" else k): v for k, v in cfg.get("fileSizes", {}).items()}
    html = html[: m.start(1)] + json.dumps(cfg) + html[m.end(1) :]
    html_path.write_text(html, encoding="utf-8")

    game = {
        "kind": "godot",
        "entry": "game/index.html",
        "engine": sha12,
        "godot": manifest.get("godot"),
        "threads": bool(threads),
    }
    return game, sha12, engine_files


def stage_thumb(wasm_dir, stage_run_dir):
    frame = wasm_dir / "verification" / "frame-1.png"
    if not frame.is_file():
        return None
    shutil.copy(frame, stage_run_dir / "thumb.png")
    return "thumb.png"


def read_verified(wasm_dir):
    report = wasm_dir / "verification" / "verify-report.json"
    if not report.is_file():
        return None
    return json.loads(report.read_text()).get("ok")
