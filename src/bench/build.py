"""Godot web export + verify, ported from fe-godot-web-export.mjs / fe-verify-web-build.mjs.
See SPEC.md "bench run" steps 6 (Export) and 7 (Verify)."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PRESET_TEMPLATE = """[preset.0]

name="Web"
platform="Web"
runnable=true
advanced_options=false
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter="{exclude_filter}"
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
# The session files a run's level dir may contain: never part of the exported package.
SESSION_EXCLUDES = ["conversation.json", "data.json", "status.json", "session.jsonl", "output.md", "stderr.txt"]


def export_project(godot_bin, project_dir, out_dir, timeout=600):
    """Export project_dir to a Godot Web build at out_dir/index.html.

    Returns (ok, manifest_or_None, error_or_None). Never raises for an ordinary export
    failure (Godot can exit 0 while producing nothing usable); only writes export_presets.cfg
    and the manifest on success.
    """
    exclude_filter = ",".join(SESSION_EXCLUDES)
    (project_dir / "export_presets.cfg").write_text(PRESET_TEMPLATE.format(exclude_filter=exclude_filter))
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


# Boot signals: Godot removes #status once the engine is up; a web page just has to finish loading.
GODOT_READY = "!document.getElementById('status')"
# The web kind is checked the way the site shows it: in an iframe sandboxed like sandboxedGame() in
# docs/assets/common.js (opaque origin, so storage APIs throw), with every request but the page blocked.
SANDBOX_FRAME = """<!doctype html><html><body style="margin:0">
<iframe src="../index.html" sandbox="allow-scripts allow-pointer-lock" style="border:0;width:100vw;height:100vh;display:block"></iframe>
</body></html>
"""


def verify_build(out_dir, wait_s=30, settle_s=1.2, web=False):
    """Serve out_dir, open it in headless Chrome, and check it boots. Returns the report dict,
    or None (with a printed note) if Playwright isn't installed. Writes verification/*.png and
    verify-report.json under out_dir.

    web=True (the web kind): load index.html inside a sandboxed iframe with the network blocked
    (only the page itself is served); ok = it loaded with no page errors and no blocked requests.
    Otherwise (Godot): ok = the engine booted, two screenshots differ and there were no page errors.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("note: playwright not installed (pip install bench[verify]); skipping verification")
        return None

    from .serve import serve_in_thread

    verify_dir = out_dir / "verification"
    verify_dir.mkdir(parents=True, exist_ok=True)
    server = serve_in_thread(out_dir)
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    console_errors = []
    page_errors = []
    blocked = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader"])
            page = browser.new_page()
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: page_errors.append(str(e)))
            if web:
                (verify_dir / "frame.html").write_text(SANDBOX_FRAME)
                allowed = {f"{origin}/verification/frame.html", f"{origin}/index.html"}

                def route(r):
                    if r.request.url in allowed:
                        r.continue_()
                    else:
                        blocked.append(r.request.url[:200])
                        r.abort()

                page.route("**/*", route)
                page.goto(f"{origin}/verification/frame.html")
                target = page.frames[1] if len(page.frames) > 1 else page.main_frame
                ready_js = "document.readyState === 'complete'"
            else:
                page.goto(f"{origin}/index.html")
                target, ready_js = page.main_frame, GODOT_READY
            booted = False
            waited = 0
            step = 500
            while waited < wait_s * 1000:
                if target.evaluate(ready_js):
                    booted = True
                    break
                page.wait_for_timeout(step)
                waited += step
            if web:
                page.wait_for_timeout(int(settle_s * 1000))  # let the first frames render
            frame1 = verify_dir / "frame-1.png"
            page.screenshot(path=str(frame1))
            page.wait_for_timeout(int(settle_s * 1000))
            frame2 = verify_dir / "frame-2.png"
            page.screenshot(path=str(frame2))
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    frames_differ = frame1.read_bytes() != frame2.read_bytes()
    if web:
        ok = booted and not page_errors and not blocked
    else:
        ok = booted and frames_differ and not page_errors
    report = {
        "ok": ok,
        "booted": booted,
        "framesDiffer": frames_differ,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
    }
    if web:
        report["blockedRequests"] = blocked
    (verify_dir / "verify-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
