"""Playwright tests for the static viewer in docs/, against the hand-made fixture
site data in tests/fixtures/site/data/ (page "demo" with 3 runs: low/medium/high).

Serves a temp copy of docs/*.html + docs/assets + the fixture data via a plain
ThreadingHTTPServer (no dependency on the CLI's own serve command).
"""

import functools
import http.server
import shutil
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[1]
FIXTURE_DATA = REPO / "tests/fixtures/site/data"


@pytest.fixture(scope="session")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("site")
    for f in REPO.glob("docs/*.html"):
        shutil.copy(f, root / f.name)
    shutil.copytree(REPO / "docs/assets", root / "assets")
    shutil.copytree(FIXTURE_DATA, root / "data")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        httpd.shutdown()
        thread.join()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


@pytest.fixture
def page(browser):
    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    console_errors = []
    page_errors = []
    pg.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: page_errors.append(str(e)))
    pg._console_errors = console_errors
    pg._page_errors = page_errors
    yield pg
    pg.close()


def assert_no_errors(pg):
    """No uncaught exceptions, and no console errors other than resource 404s
    that a test deliberately provoked (those are checked separately)."""
    assert not pg._page_errors, f"page errors: {pg._page_errors}"
    real_errors = [m for m in pg._console_errors if "404" not in m and "Failed to load resource" not in m]
    assert not real_errors, f"console errors: {real_errors}"


LOW_ID = "model-x-low-20260101-000000"
MEDIUM_ID = "model-x-medium-20260101-000500"
HIGH_ID = "model-x-high-20260101-001000"


# ---------------------------------------------------------------- home page
def test_home_lists_page(site, page):
    page.goto(site)
    page.wait_for_selector(".card")
    cards = page.locator(".card")
    assert cards.count() == 1
    assert "Demo" in cards.first.inner_text()
    assert page.locator(".card .thumb").count() == 1  # high run's thumb, no games loaded
    assert page.locator("iframe").count() == 0
    assert_no_errors(page)


# ---------------------------------------------------------------- page.html
def test_page_table_and_sorting(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    rows = page.locator("table.runs tbody tr")
    assert rows.count() == 3

    # sort by duration ascending then descending and check row order flips
    page.locator('th[data-key="duration_ms"]').click()
    first_asc = rows.nth(0).inner_text()
    page.locator('th[data-key="duration_ms"]').click()
    first_desc = rows.nth(0).inner_text()
    assert first_asc != first_desc

    assert page.locator("iframe").count() == 0
    assert_no_errors(page)


def test_page_shows_labeled_prompt(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("#prompt-box:not([hidden])")
    assert page.locator(".prompt-label").inner_text().strip().lower() == "prompt"
    assert page.locator("#prompt").inner_text().startswith("build a tiny demo project")
    assert_no_errors(page)


def test_every_column_header_has_hover_help(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    headers = page.locator("table.runs thead th")
    assert headers.count() == 12
    titles = {headers.nth(i).inner_text().strip(" ▲▼"): headers.nth(i).get_attribute("title") for i in range(12)}
    assert all(t and len(t) > 20 for t in titles.values()), titles
    assert "reasoning" in titles["Reasoning tok"].lower()
    assert_no_errors(page)


def test_runs_table_shows_each_runs_image(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    assert page.locator("#gallery").count() == 0  # images live in the table, no separate gallery
    thumbs = page.locator("table.runs img.row-thumb")
    assert thumbs.count() == 2  # medium + high have a thumb, low doesn't
    page.wait_for_function("[...document.querySelectorAll('img.row-thumb')].every(i => i.complete && i.naturalWidth > 0)")
    for i in range(2):
        href = thumbs.nth(i).locator("xpath=..").get_attribute("href")
        assert href.startswith("run.html?p=demo&r=model-x-")
    # thumbs stay with their row when sorting
    page.locator('th[data-key="effort"]').click()
    efforts = page.locator("table.runs tbody tr td:nth-child(4)").all_inner_texts()
    has_img = [page.locator("table.runs tbody tr").nth(i).locator("img.row-thumb").count() for i in range(3)]
    assert dict(zip(efforts, has_img)) == {"low": 0, "medium": 1, "high": 1}
    assert page.locator("iframe").count() == 0
    assert_no_errors(page)


def test_compare_button_builds_url(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    checkboxes = page.locator('table.runs tbody input[type="checkbox"]')
    for i in range(checkboxes.count()):
        checkboxes.nth(i).check()
    btn = page.locator("#compare-btn")
    assert not btn.is_disabled()
    with page.expect_navigation():
        btn.click()
    url = page.url
    assert "compare.html?p=demo&r=" in url
    ids = url.split("r=", 1)[1].split(",")
    assert sorted(ids) == sorted([LOW_ID, MEDIUM_ID, HIGH_ID])
    assert_no_errors(page)


def test_page_missing_param_shows_message(site, page):
    page.goto(f"{site}page.html")
    page.wait_for_selector(".msg")
    assert "p=" in page.locator(".msg").inner_text() or "slug" in page.locator(".msg").inner_text().lower()


def test_page_invalid_slug_shows_message(site, page):
    page.goto(f"{site}page.html?p=does-not-exist")
    page.wait_for_selector(".msg-error")
    assert not page.locator("table.runs tbody tr").count()
    assert not page._page_errors


# ---------------------------------------------------------------- run.html
def test_run_game_tab_click_to_play(site, page):
    page.goto(f"{site}run.html?p=demo&r={HIGH_ID}")
    page.wait_for_selector("[data-play]")
    assert page.locator("iframe").count() == 0

    overlay = page.locator("[data-play]")
    assert overlay.count() == 1
    overlay.click()

    frame = page.locator("iframe")
    assert frame.count() == 1
    sandbox = frame.get_attribute("sandbox")
    assert "allow-scripts" in sandbox
    assert "allow-same-origin" not in sandbox
    assert page.locator("[data-play]").count() == 0  # overlay replaced, not just hidden

    assert page.locator('a:has-text("Open full screen")').count() == 1
    assert_no_errors(page)


def test_run_game_tab_null_game(site, page):
    page.goto(f"{site}run.html?p=demo&r={MEDIUM_ID}")
    page.wait_for_selector("#panel-game")
    assert "No game" in page.locator("#panel-game").inner_text()
    assert page.locator("[data-play]").count() == 0
    assert_no_errors(page)


def test_run_transcript_tool_calls_and_filters(site, page):
    page.goto(f"{site}run.html?p=demo&r={HIGH_ID}")
    page.locator('#tabs button[data-tab="transcript"]').click()
    page.wait_for_selector(".transcript .turn")

    assert page.locator(".tool-block").count() == 5  # bash, ls, write, edit, read
    assert page.locator(".badge-error").count() == 1  # the bash call errors

    # thinking hidden by default, shown after toggle
    thinking = page.locator(".thinking-block").first
    assert not thinking.is_visible()
    page.locator('button:has-text("Show thinking")').click()
    assert thinking.is_visible()

    total_turns = page.locator(".transcript .turn").count()
    page.locator('[data-filter-btn="errors"]').click()
    visible_after_errors = page.locator(".transcript .turn:visible").count()
    assert 0 < visible_after_errors < total_turns

    page.locator('[data-filter-btn="tools"]').click()
    visible_tools = page.locator(".transcript .turn:visible").count()
    assert visible_tools >= visible_after_errors

    page.locator('[data-filter-btn="all"]').click()
    assert page.locator(".transcript .turn:visible").count() == total_turns

    # XSS: literal <script> in assistant text must render as visible text, not execute
    assert "<script>" in page.locator(".transcript").inner_text()
    # code blocks keep literal < > & (no double escaping); javascript: links are neutralized
    assert "if x < 5 && y > 2:" in page.locator(".transcript").inner_text()
    assert page.locator(".transcript a[href^='javascript']").count() == 0
    assert page.locator(".transcript a[href='https://example.com']").count() == 1
    assert_no_errors(page)


def test_run_transcript_null_session(site, page):
    page.goto(f"{site}run.html?p=demo&r={LOW_ID}")
    page.locator('#tabs button[data-tab="transcript"]').click()
    page.wait_for_selector("#panel-transcript .msg")
    assert "No transcript" in page.locator("#panel-transcript").inner_text()
    assert_no_errors(page)


def test_run_source_tab_shows_file_content(site, page):
    page.goto(f"{site}run.html?p=demo&r={HIGH_ID}")
    page.locator('#tabs button[data-tab="source"]').click()
    page.wait_for_selector(".source-files button")
    assert page.locator(".source-files button").count() == 2
    page.locator('.source-files button:has-text("README.md")').click()
    page.wait_for_function("document.querySelector('.source-view pre').textContent.includes('Demo')")
    assert "Demo" in page.locator(".source-view pre").inner_text()
    assert_no_errors(page)


def test_run_invalid_run_id_shows_message(site, page):
    page.goto(f"{site}run.html?p=demo&r=does-not-exist")
    page.wait_for_selector(".msg-error")
    assert not page._page_errors


# ---------------------------------------------------------------- compare.html
def test_compare_three_runs_no_iframes_until_clicked(site, page):
    ids = ",".join([LOW_ID, MEDIUM_ID, HIGH_ID])
    page.goto(f"{site}compare.html?p=demo&r={ids}")
    page.wait_for_selector(".compare-col")
    assert page.locator(".compare-col").count() == 3
    assert page.locator("iframe").count() == 0

    # only medium + high have a game (2 overlays); low has none
    overlays = page.locator("[data-play]")
    assert overlays.count() >= 1
    n = overlays.count()
    for _ in range(n):
        page.locator("[data-play]").first.click()
    assert page.locator("iframe").count() == n
    for i in range(n):
        sandbox = page.locator("iframe").nth(i).get_attribute("sandbox")
        assert "allow-same-origin" not in sandbox

    assert_no_errors(page)


def test_compare_source_file_picker_syncs_columns(site, page):
    ids = ",".join([LOW_ID, MEDIUM_ID, HIGH_ID])
    page.goto(f"{site}compare.html?p=demo&r={ids}")
    page.wait_for_selector("#file-picker button")
    page.locator('#file-picker button:has-text("main.py")').click()
    page.wait_for_function(
        "[...document.querySelectorAll('.compare-col pre')].some(p => p.textContent.includes('hello'))"
    )
    views = page.locator(".compare-col pre")
    texts = [views.nth(i).inner_text() for i in range(views.count())]
    assert any("not present" in t for t in texts)  # low has no source
    assert any("hello" in t for t in texts)  # medium/high do
    assert_no_errors(page)


def test_compare_tool_call_summary_has_error_badge(site, page):
    ids = ",".join([MEDIUM_ID, HIGH_ID])
    page.goto(f"{site}compare.html?p=demo&r={ids}")
    page.wait_for_selector(".tool-summary-list li")
    assert page.locator(".badge-bad").count() >= 1
    assert_no_errors(page)
