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


def test_clicking_a_row_expands_the_game_inline(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr.run-row")
    assert page.locator("iframe").count() == 0

    rows = page.locator("tr.run-row")
    row = lambda effort: rows.filter(has=page.locator("td", has_text=effort)).first
    high = row("high")
    high.locator("td").nth(3).click()  # click a plain cell
    assert high.get_attribute("aria-expanded") == "true"
    frame = page.locator("tr.run-detail iframe")
    assert frame.count() == 1
    assert "allow-same-origin" not in frame.get_attribute("sandbox")
    assert frame.get_attribute("src").endswith(f"/{HIGH_ID}/game/index.html")

    high.locator("td").nth(3).click()  # collapse removes the game
    assert page.locator("tr.run-detail").count() == 0 and page.locator("iframe").count() == 0

    # keyboard works too; a run without a game says so
    assert page.locator("table.runs input[type=checkbox]").count() == 0
    row("low").focus()
    page.keyboard.press("Enter")
    assert "No playable build" in page.locator("tr.run-detail").inner_text()
    assert page.locator("iframe").count() == 0
    assert_no_errors(page)


def test_page_shows_labeled_prompt(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("#prompt-box:not([hidden])")
    assert page.locator(".prompt-label").inner_text().strip().lower() == "prompt"
    assert page.locator("#prompt").inner_text().startswith("build a tiny demo project")
    # final prompt: present but collapsed to one line until clicked
    final = page.locator("details.final-prompt")
    assert final.is_visible() and final.get_attribute("open") is None
    assert not page.locator("#final-prompt").is_visible()
    final.locator("summary").click()
    assert page.locator("#final-prompt").inner_text().startswith("Task: Goal: build a tiny demo")
    assert_no_errors(page)


def test_every_column_header_has_hover_help(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    headers = page.locator("table.runs thead th")
    assert headers.count() == 12  # caret, thumb, 10 data columns
    helps = {headers.nth(i).inner_text().strip(" ▲▼"): headers.nth(i).get_attribute("data-help") for i in range(12)}
    assert all(t and len(t) > 20 for t in helps.values()), helps
    assert "reasoning" in helps["Reasoning tok"].lower()
    assert headers.nth(0).get_attribute("title") is None  # no slow native tooltip competing

    # custom tooltip: not instant, shown after ~0.5s, stays on screen, hidden on leave
    tip = page.locator(".col-tip")
    page.locator('th[data-key="turns"]').hover()
    page.wait_for_timeout(150)
    assert not tip.is_visible()
    page.wait_for_timeout(600)
    assert tip.is_visible() and "model responses" in tip.inner_text()
    box = tip.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= page.viewport_size["width"]
    page.locator("h1").hover()
    assert not tip.is_visible()
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


def test_compare_all_opens_every_run(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    link = page.locator("#compare-all")
    assert link.inner_text().strip() == "Compare all"
    with page.expect_navigation():
        link.click()
    assert page.url.endswith("compare.html?p=demo")
    page.wait_for_selector(".compare-col")
    assert page.locator(".compare-col").count() == 3
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
def test_compare_shows_metrics_and_games_only(site, page):
    page.goto(f"{site}compare.html?p=demo")
    page.wait_for_selector(".compare-col")
    cols = page.locator(".compare-col")
    assert cols.count() == 3
    text = page.locator("#columns").inner_text()
    assert "Tool calls" not in text and "Source" not in text
    assert page.locator("#file-picker, .tool-summary-list").count() == 0
    for i in range(3):
        metrics = cols.nth(i).locator(".compare-metrics").inner_text()
        assert "tokens" in metrics and "$" in metrics

    # games never boot on their own; in the fixture only the high run has one
    assert page.locator("iframe").count() == 0
    assert page.locator("[data-play]").count() == 1
    page.locator("[data-play]").click()
    assert page.locator("iframe").count() == 1
    assert "allow-same-origin" not in page.locator("iframe").get_attribute("sandbox")
    assert page.locator(".compare-col", has_text="No game recorded").count() == 2
    assert_no_errors(page)


def test_compare_play_all_starts_every_game(site, page):
    page.goto(f"{site}compare.html?p=demo")
    page.wait_for_selector(".compare-col")
    btn = page.locator("#play-all")
    assert btn.is_enabled() and page.locator("iframe").count() == 0
    btn.click()
    assert page.locator("[data-play]").count() == 0
    assert page.locator("iframe").count() == 1
    assert btn.is_disabled()  # nothing left to play

    page.goto(f"{site}compare.html?p=demo&r={LOW_ID}")  # no games at all
    page.wait_for_selector(".compare-col")
    assert page.locator("#play-all").is_disabled()
    assert_no_errors(page)


def test_compare_can_be_limited_to_listed_runs(site, page):
    page.goto(f"{site}compare.html?p=demo&r={MEDIUM_ID},{HIGH_ID}")
    page.wait_for_selector(".compare-col")
    assert page.locator(".compare-col").count() == 2
    assert_no_errors(page)
