"""The `godot` kind: export the project the agent wrote to a Godot web build, boot-check it, and
stage it with the engine stored once. See SPEC.md "bench run" steps 6 and 7 and "Godot engine dedupe"."""

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..browser import copy_thumb, verify_page
from ..util import BenchError
from . import Kind, Staged

PRESET_TEMPLATE = """[preset.0]

name="Web"
platform="Web"
runnable=true
advanced_options=false
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path=""
patches=PackedStringArray()
encryption_include_filters=""
encryption_exclude_filters=""
seed=0
encrypt_pck=false
encrypt_directory=false
script_export_mode=2

[preset.0.options]

custom_template/debug=""
custom_template/release=""
variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=false
html/export_icon=true
html/custom_html_shell=""
html/head_include=""
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/experimental_virtual_keyboard=false
progressive_web_app/enabled=false
progressive_web_app/ensure_cross_origin_isolation_headers=false
progressive_web_app/offline_page=""
progressive_web_app/display=1
progressive_web_app/orientation=0
progressive_web_app/icon_144x144=""
progressive_web_app/icon_180x180=""
progressive_web_app/icon_512x512=""
progressive_web_app/background_color=Color(0, 0, 0, 1)
"""

EXPORT_FILES = ["index.html", "index.js", "index.wasm", "index.pck"]


def export_project(godot_bin, project_dir, out_dir, timeout=600):
    """Export project_dir to a Godot Web build at out_dir/index.html.

    Returns (ok, manifest_or_None, error_or_None). Never raises for an ordinary export
    failure (Godot can exit 0 while producing nothing usable); only writes export_presets.cfg
    and the manifest on success.
    """
    (project_dir / "export_presets.cfg").write_text(PRESET_TEMPLATE)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_html = out_dir / "index.html"
    cmd = [godot_bin, "--headless", "--path", str(project_dir), "--export-release", "Web", str(out_html)]
    try:
        result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, timeout=timeout)
        log = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        return False, None, "Godot export failed: timed out"
    except OSError as e:
        return False, None, f"Godot export failed: {e}"

    missing = [name for name in EXPORT_FILES if not (out_dir / name).is_file() or (out_dir / name).stat().st_size == 0]
    if missing:
        last_line = next((line.strip() for line in reversed(log.splitlines()) if line.strip()), f"exit {result.returncode}")
        return False, None, f"Godot export failed: {last_line}"

    version_r = subprocess.run([godot_bin, "--version"], capture_output=True, text=True, timeout=15)
    version = version_r.stdout.strip().splitlines()[0].strip() if version_r.returncode == 0 else None
    manifest = {
        "godot": version,
        "threads": False,
        "template": "web_nothreads_release.zip",
        "exportedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (out_dir / "export-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return True, manifest, None


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

    Returns (game fields, sha12, engine_files_or_None). engine_files is a {name: bytes} dict
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
        "entry": "game/index.html",
        "engine": sha12,
        "godot": manifest.get("godot"),
        "threads": bool(threads),
    }
    return game, sha12, engine_files


# Godot removes #status once the engine is up.
GODOT_READY = "!document.getElementById('status')"


class Godot(Kind):
    name = "godot"
    activity = "exporting"
    serial = True  # one headless export at a time
    binary = "godot"

    def finalize(self, work_dir, out_dir):
        ok, _manifest, error = export_project(self.binary, work_dir, out_dir)
        return ok, error

    def verify(self, out_dir):
        """The engine booted, two screenshots differ and there were no page errors."""
        return verify_page(out_dir, GODOT_READY, lambda r: r["booted"] and r["framesDiffer"] and not r["pageErrors"])

    def stage(self, out_dir, run_dir, ctx):
        game, sha12, engine_files = stage_game(
            out_dir, run_dir / "game", ctx.docs_root, ctx.slug, ctx.run_id, ctx.allow_threads, ctx.known_engines
        )
        return Staged({k: v for k, v in game.items() if k != "kind"}, copy_thumb(out_dir, run_dir), (sha12, engine_files))
