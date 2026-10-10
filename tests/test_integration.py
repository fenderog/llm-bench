"""End to end: serve the published voxel-horse page (real Godot builds) and check all 3 games boot sandboxed."""

import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(not (REPO / "docs/data/voxel-horse").is_dir(), reason="voxel-horse isn't published here")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("site")
    (root / "docs").mkdir()
    for f in [*REPO.glob("docs/*.html"), REPO / "docs/.nojekyll"]:
        shutil.copy(f, root / "docs")
    shutil.copytree(REPO / "docs/assets", root / "docs/assets")
    shutil.copy(REPO / "art-crit.toml", root)
    shutil.copytree(REPO / "docs/data/voxel-horse", root / "docs/data/voxel-horse")
    shutil.copytree(REPO / "docs/engines", root / "docs/engines")
    (root / "docs/data/pages.json").write_text("[]")
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "art_crit", "serve", "--port", str(port), "--root", str(root)])
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/data/pages.json")
            break
        except OSError:
            time.sleep(0.1)
    yield root, f"http://127.0.0.1:{port}/"
    server.terminate()
    server.wait()


def test_published_output(site):
    root, _ = site
    docs = root / "docs"
    runs = json.loads((docs / "data/voxel-horse/page.json").read_text())["runs"]
    assert sorted(r["effort"] for r in runs) == ["high", "low", "medium"]
    assert len(list((docs / "engines").iterdir())) == 1, "engine should be stored once"
    for r in runs:
        run_dir = docs / "data/voxel-horse/runs" / r["id"]
        assert not list(run_dir.rglob("*.wasm")), "engine must not be copied into runs"
        text = "".join(p.read_text(errors="ignore") for p in (run_dir / "session").iterdir())
        assert "/Users/" not in text and "/Volumes/" not in text and "encrypted_content" not in text
    total = sum(p.stat().st_size for p in (docs / "data").rglob("*") if p.is_file())
    assert total < 5_000_000, f"data dir unexpectedly large: {total} bytes"


def test_all_games_boot_sandboxed_in_compare(site):
    from playwright.sync_api import sync_playwright

    root, base = site
    runs = json.loads((root / "docs/data/voxel-horse/page.json").read_text())["runs"]
    ids = ",".join(r["id"] for r in runs)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 1500, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{base}compare.html?p=voxel-horse&r={ids}")
        assert page.locator("iframe").count() == 0, "games must not boot before a click"
        assert page.locator("[data-play]").count() == 3
        page.locator("#play-all").click()  # starts all three at once
        frames = page.locator("iframe")
        assert frames.count() == 3
        for i in range(3):
            assert "allow-same-origin" not in frames.nth(i).get_attribute("sandbox")
        deadline = time.time() + 60
        while time.time() < deadline:
            game_frames = [f for f in page.frames if "/game/" in f.url]
            booted = [f.evaluate("!document.getElementById('status')") for f in game_frames]
            if len(booted) == 3 and all(booted):
                break
            page.wait_for_timeout(1000)
        assert len(booted) == 3 and all(booted), f"games not booted: {booted}"
        page.screenshot(path=str(root / "compare.png"))
        browser.close()
    assert not errors, errors


def test_game_boots_when_a_row_is_expanded(site):
    from playwright.sync_api import sync_playwright

    _, base = site
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader"])
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{base}page.html?p=voxel-horse&view=table")
        row = page.locator("tr.run-row").filter(has=page.locator("td", has_text="high")).first
        row.locator('td[data-col="effort"]').click()
        deadline = time.time() + 60
        booted = False
        while time.time() < deadline and not booted:
            frames = [f for f in page.frames if "/game/" in f.url]
            booted = bool(frames) and frames[0].evaluate("!document.getElementById('status')")
            page.wait_for_timeout(500)  # not time.sleep: Playwright only sees new frames while it runs
        assert booted, "game did not boot in the expanded row"
        browser.close()
    assert not errors, errors
