"""The headless-Chrome check the Godot and web kinds share. See SPEC.md "art-crit run" step 7 (Verify)."""

import json
import shutil

# The sandboxed check shows the page the way the site does: in an iframe sandboxed like sandboxedGame()
# in docs/assets/output.js (opaque origin, so storage APIs throw), with every request but the page blocked.
SANDBOX_FRAME = """<!doctype html><html><body style="margin:0">
<iframe src="../index.html" sandbox="allow-scripts allow-pointer-lock" style="border:0;width:100vw;height:100vh;display:block"></iframe>
</body></html>
"""


def verify_page(out_dir, ready_js, judge, *, sandboxed=False, wait_s=30, settle_s=1.2):
    """Serve out_dir, open its index.html in headless Chrome and wait for `ready_js` (evaluated in the
    page) to be true, then take two screenshots. Returns the report dict, or None (with a printed note) if
    Playwright isn't installed. Writes verification/frame-1.png, frame-2.png and verify-report.json under out_dir.

    The report: {ok, booted, framesDiffer, consoleErrors, pageErrors}, plus blockedRequests when
    sandboxed (the page runs in the site's sandbox with the network blocked). `judge(report)` decides `ok`."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("note: playwright not installed (pip install art-crit[verify]); skipping verification")
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
            if sandboxed:
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
            else:
                page.goto(f"{origin}/index.html")
                target = page.main_frame
            booted = False
            waited = 0
            step = 500
            while waited < wait_s * 1000:
                if target.evaluate(ready_js):
                    booted = True
                    break
                page.wait_for_timeout(step)
                waited += step
            if sandboxed:
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

    report = {
        "booted": booted,
        "framesDiffer": frame1.read_bytes() != frame2.read_bytes(),
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
    }
    if sandboxed:
        report["blockedRequests"] = blocked
    report = {"ok": judge(report), **report}
    (verify_dir / "verify-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def copy_thumb(out_dir, run_dir):
    """The verification screenshot as the run's thumbnail, or None."""
    frame = out_dir / "verification" / "frame-1.png"
    if not frame.is_file():
        return None
    shutil.copy(frame, run_dir / "thumb.png")
    return "thumb.png"
