"""The web kind: packaging a page into one file with the real esbuild, and verifying it offline in a
sandboxed iframe with the real headless Chrome. Skipped when esbuild (or Playwright) is missing."""

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from bench.kinds import web
from bench.kinds.web import Web

pytestmark = pytest.mark.skipif(shutil.which("esbuild") is None, reason="esbuild not on PATH")


def in_thread(fn, *args, **kwargs):
    """Sync Playwright can't start in a thread that already runs one (test_web.py keeps a session-wide
    browser open), so browser work here runs in a thread of its own."""
    with ThreadPoolExecutor(1) as pool:
        return pool.submit(fn, *args, **kwargs).result()


@pytest.fixture
def project(tmp_path):
    d = tmp_path / "project"
    (d / "node_modules/lib").mkdir(parents=True)
    (d / "node_modules/lib/package.json").write_text('{"name": "lib", "main": "index.js"}')
    (d / "node_modules/lib/index.js").write_text(
        'export const tag = "</script><b>not markup</b>";\nexport const link = \'<link rel="stylesheet" href="style.css">\';\n'
    )
    (d / "js").mkdir()
    (d / "js/app.js").write_text('import { tag, link } from "lib";\nimport pic from "../dot.svg";\nwindow.out = [tag, link, pic];\n')
    (d / "dot.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    (d / "old.js").write_text("var classic = 1;\n")
    (d / "style.css").write_text("body { color: red; }\n")
    return d


def write_page(project, body):
    (project / "index.html").write_text(f"<!doctype html><html><head></head><body>{body}</body></html>")


def test_bundles_scripts_stylesheets_and_packages_into_one_page(project, tmp_path):
    write_page(project, (
        '<link rel="stylesheet" href="./style.css">'
        '<script type="module" src="js/app.js?v=1"></script>'
        '<script type="module">import { tag } from "lib"; console.log(tag);</script>'
        '<script src="old.js" defer></script>'
        '<script>var inline = 1;</script>'
        '<script src="https://cdn.example/x.js"></script>'
        '<script type="importmap">{"imports": {}}</script>'
    ))
    ok, manifest, error = web.package(project, tmp_path / "out")
    assert ok, error
    html = (tmp_path / "out/index.html").read_text()
    assert manifest["esbuild"] and manifest["bytes"] == len(html.encode())
    assert "color:red" in html and '<link rel="stylesheet" href="./style.css">' not in html
    assert 'src="js/app.js' not in html and 'from"lib"' not in html and "data:image/svg+xml" in html
    assert "<\\/script><b>" in html  # a string can't close the inlined script
    assert '<link rel="stylesheet" href="style.css">' in html  # a string in the bundle isn't treated as markup
    assert '<script src="data:text/javascript;base64,dmFyIGNsYXNzaWMgPSAxOwo=" defer></script>' in html  # kept verbatim
    assert "<script>var inline = 1;</script>" in html  # classic inline scripts are left alone
    assert '<script src="https://cdn.example/x.js"></script>' in html  # remote: left for verify to catch
    assert '<script type="importmap">' in html


def test_missing_import_or_file_outside_project_fails(project, tmp_path):
    write_page(project, '<script type="module">import "./nope.js";</script>')
    ok, _, error = web.package(project, tmp_path / "out")
    assert not ok and error.startswith("packaging failed: esbuild:") and not (tmp_path / "out").exists()

    (tmp_path / "secret.js").write_text("var s = 1;")
    write_page(project, '<script src="../secret.js"></script>')
    ok, _, error = web.package(project, tmp_path / "out")
    assert not ok and "not a file inside the project" in error

    (project / "index.html").unlink()
    assert web.package(project, tmp_path / "out")[2] == "packaging failed: no index.html in the project"


def test_verify_runs_the_page_offline_in_a_sandbox(tmp_path):
    pytest.importorskip("playwright")
    good = tmp_path / "good"
    good.mkdir()
    (good / "index.html").write_text(
        "<canvas id=c width=64 height=64></canvas><script type=module>"
        "const g = c.getContext('2d'); let n = 0;"
        "(function f() { g.fillStyle = `hsl(${n++ * 7} 80% 50%)`; g.fillRect(0, 0, 64, 64); requestAnimationFrame(f); })();"
        "</script>"
    )
    report = in_thread(Web().verify, good)
    assert report["ok"] and report["booted"] and report["framesDiffer"] and report["blockedRequests"] == []
    assert (good / "verification/frame-1.png").is_file()

    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "index.html").write_text(
        '<script type=module>fetch("https://cdn.example/three.js").catch(() => {}); localStorage.x = 1;</script>'
    )
    report = in_thread(Web().verify, bad)
    assert not report["ok"]
    assert report["blockedRequests"] == ["https://cdn.example/three.js"]
    assert any("sandboxed" in e for e in report["pageErrors"])  # storage throws in the site's sandbox


def test_web_run_end_to_end_in_the_viewer(tmp_path, monkeypatch):
    """Fake agent -> real esbuild -> real offline verify -> import -> the viewer plays it sandboxed."""
    sync_api = pytest.importorskip("playwright.sync_api")
    from bench.cli import main
    from bench.serve import serve_in_thread

    repo = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PATH", f"{repo / 'tests/fixtures/fake_pi'}{os.pathsep}{os.environ['PATH']}")
    root = tmp_path / "site"
    (root / "docs").mkdir(parents=True)
    for f in repo.glob("docs/*.html"):
        shutil.copy(f, root / "docs")
    shutil.copytree(repo / "docs/assets", root / "docs/assets")
    (root / "bench.toml").write_text(f'[run]\ndir = "{tmp_path / "runs"}"\n')
    assert in_thread(main, ["run", "--yes", "--kind", "web", "a spinning horse", "-m", "openai-codex/gpt-6-sol:low", "--root", str(root)]) == 0
    [run] = json.loads((root / "docs/data/a-spinning-horse/page.json").read_text())["runs"]
    assert run["output"]["verified"] is True and run["thumb"] == "thumb.png"

    server = serve_in_thread(root / "docs")
    try:
        in_thread(check_viewer, sync_api, f"http://127.0.0.1:{server.server_address[1]}/", run["id"])
    finally:
        server.shutdown()
        server.server_close()


def check_viewer(sync_api, base, run_id):
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        pg = browser.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"{base}page.html?p=a-spinning-horse")
        pg.wait_for_selector("table.runs tbody tr.run-row")
        assert pg.locator(".page-meta .kind-chip").text_content() == "Web"
        pg.locator("tr.run-row").click()
        frame = pg.locator("tr.run-detail iframe")
        assert frame.get_attribute("sandbox") == "allow-scripts allow-pointer-lock"
        pg.goto(f"{base}run.html?p=a-spinning-horse&r={run_id}")
        assert pg.locator('#tabs button[data-tab="game"]').inner_text() == "Page"
        pg.locator("[data-play]").click()
        pg.wait_for_timeout(500)
        game = next(f for f in pg.frames if f.url.endswith("/game/index.html"))
        assert game.evaluate("document.title") == "spinning horse"  # the bundled npm package ran
        pg.goto(base)
        assert "Web" in pg.locator(".kind-chip").all_text_contents()
        assert not errors
        browser.close()
