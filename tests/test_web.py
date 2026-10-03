"""Playwright tests for the static viewer in docs/, against the hand-made fixture
site data in tests/fixtures/site/data/ (page "demo" with 3 runs: low/medium/high).

Serves a temp copy of docs/*.html + docs/assets + the fixture data via a plain
ThreadingHTTPServer (no dependency on the CLI's own serve command).
"""

import functools
import http.server
import re
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
ART_HIGH_ID = "model-x-high-20260102-000000"


# ---------------------------------------------------------------- home page
def test_home_lists_page(site, page):
    page.goto(site)
    page.wait_for_selector(".card")
    cards = page.locator(".card")
    assert cards.count() == 2
    assert "Demo" in cards.filter(has_text="Demo").inner_text()
    assert page.locator(".card .thumb").count() == 2  # demo: high run's thumb; art: its SVG, no games loaded
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
    high.locator('td[data-col="effort"]').click()  # click a plain cell
    assert high.get_attribute("aria-expanded") == "true"
    frame = page.locator("tr.run-detail iframe")
    assert frame.count() == 1
    assert "allow-same-origin" not in frame.get_attribute("sandbox")
    assert frame.get_attribute("src").endswith(f"/{HIGH_ID}/game/index.html")

    high.locator('td[data-col="effort"]').click()  # collapse removes the game
    assert page.locator("tr.run-detail").count() == 0 and page.locator("iframe").count() == 0

    # keyboard works too; a run without a game says so
    assert page.locator("table.runs input[type=checkbox]").count() == 0
    row("low").focus()
    page.keyboard.press("Enter")
    assert "No playable build" in page.locator("tr.run-detail").inner_text()
    assert page.locator("iframe").count() == 0
    assert_no_errors(page)


def test_page_harness_column_and_failed_badge(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    rows = page.locator("tr.run-row")
    row = lambda effort: rows.filter(has=page.locator("td", has_text=effort)).first

    high_text = row("high").inner_text()
    assert "pi" in high_text and "0.87.1" in high_text
    assert row("medium").locator('td[data-col="harness"] .harness-version').inner_text() == "2.1.284"

    low = row("low")
    assert "failed" in low.locator(".badge-bad").inner_text()

    # expanding the failed row shows its error above the "No playable build" line
    low.locator('td[data-col="effort"]').click()  # plain cell (effort), not a link/button
    detail = page.locator("tr.run-detail")
    assert "pi exited 1: rate limited" in detail.locator(".run-error").inner_text()
    assert "No playable build" in detail.inner_text()
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
    assert headers.count() == 13  # caret, thumb, 11 data columns
    helps = {headers.nth(i).inner_text().strip(" ▲▼"): headers.nth(i).get_attribute("data-help") for i in range(13)}
    assert all(t and len(t) > 20 for t in helps.values()), helps
    assert "reasoning" in helps["Reasoning"].lower()
    assert headers.nth(0).get_attribute("title") is None  # no slow native tooltip competing

    # custom tooltip: not instant, shown after ~0.5s, stays on screen, hidden on leave
    tip = page.locator(".col-tip")
    page.locator('th[data-key="tool_calls"]').hover()
    page.wait_for_timeout(150)
    assert not tip.is_visible()
    page.wait_for_timeout(600)
    assert tip.is_visible() and "tools the agent invoked" in tip.inner_text()
    box = tip.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= page.viewport_size["width"]
    page.locator("h1").hover()
    assert not tip.is_visible()
    assert_no_errors(page)


@pytest.mark.parametrize("width", [1440, 1280, 1100, 900, 721])
def test_runs_table_never_scrolls_horizontally(site, browser, width):
    """Above the phone breakpoint the table fits its wrapper; low-priority columns hide instead of scrolling.
    The fixture has a claude-code harness label, and one run gets a long pinned-upstream model name."""
    ctx = browser.new_context(viewport={"width": width, "height": 900})
    pg = ctx.new_page()
    long_model = "openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8"

    def long_name(route):
        body = route.fetch().json()
        body["runs"][0]["model"] = long_model
        route.fulfill(json=body)

    pg.route("**/data/demo/page.json*", long_name)
    pg.goto(f"{site}page.html?p=demo")
    pg.wait_for_selector("table.runs tbody tr")
    assert pg.locator(".model-via").first.is_visible()
    m = pg.evaluate("""() => { const w = document.querySelector('.table-wrap');
      return { wrap: w.clientWidth, table: w.querySelector('table').scrollWidth }; }""")
    assert m["table"] <= m["wrap"], (width, m)
    for col in ("model", "effort", "verified", "duration_ms", "cost_usd"):
        assert pg.locator(f'tr.run-row:first-child td[data-col="{col}"]').is_visible(), (width, col)
    if width >= 1240:
        assert pg.locator('th[data-key="tokens_reasoning"]').is_visible()
    ctx.close()


def test_runs_table_has_run_time_and_no_output_tokens_column(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    assert page.locator('th[data-key="tokens_output"]').count() == 0
    assert page.locator('td[data-col="tokens_output"]').count() == 0
    cell = page.locator('tr.run-row:first-child td[data-col="started_at"]')
    assert cell.is_visible()
    assert cell.inner_text() != "–"
    assert re.search(r"\d{4}", cell.get_attribute("title"))  # the full date (with year) is on hover


def test_runs_table_shows_each_runs_image(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    assert page.locator("#gallery").count() == 0  # images live in the table, no separate gallery
    thumbs = page.locator("table.runs img.row-thumb")
    assert thumbs.count() == 2  # medium + high have a thumb, low doesn't
    page.wait_for_function("() => [...document.querySelectorAll('img.row-thumb')].every(i => i.complete && i.naturalWidth > 0)")
    for i in range(2):
        href = thumbs.nth(i).locator("xpath=..").get_attribute("href")
        assert href.startswith("run.html?p=demo&r=model-x-")
    # thumbs stay with their row when sorting
    page.locator('th[data-key="effort"]').click()
    efforts = page.locator("table.runs tbody tr td[data-col='effort']").all_inner_texts()
    has_img = [page.locator("table.runs tbody tr").nth(i).locator("img.row-thumb").count() for i in range(3)]
    assert dict(zip(efforts, has_img)) == {"low": 0, "medium": 1, "high": 1}
    assert page.locator("iframe").count() == 0
    assert_no_errors(page)


def test_page_orders_by_effort_and_highlights_best_completed_run(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    efforts = lambda: page.locator("table.runs tbody tr td[data-col='effort']").all_inner_texts()
    assert efforts() == ["low", "medium", "high"]  # default: model, then effort low -> max (not alphabetical)
    page.locator('th[data-key="effort"]').click()
    assert efforts() == ["low", "medium", "high"]
    page.locator('th[data-key="effort"]').click()
    assert efforts() == ["high", "medium", "low"]

    # the failed low run is cheaper but doesn't compete: medium is the cheapest/fastest completed run
    hl = page.locator("#highlights")
    assert hl.is_visible()
    cheapest = hl.locator(".hl", has_text="Cheapest")
    assert "$0.019" in cheapest.inner_text() and "medium" in cheapest.inner_text()
    assert cheapest.get_attribute("href") == f"run.html?p=demo&r={MEDIUM_ID}"
    assert "1 / 3" in hl.locator(".hl", has_text="Verified").inner_text()  # only high is verified
    best = page.locator("td.is-best")
    assert best.count() == 3 and all(
        best.nth(i).locator("xpath=..").locator("td[data-col='effort']").inner_text() == "medium" for i in range(3)
    )
    assert_no_errors(page)


def test_runs_are_tinted_by_vendor(site, page):
    for url, sel in ((f"{site}page.html?p=demo", "table.runs tbody tr.run-row"), (f"{site}compare.html?p=demo", ".compare-col")):
        page.goto(url)
        page.wait_for_selector(sel)
        vendors = page.locator(sel).evaluate_all("els => els.map(e => [e.dataset.vendor, e.style.getPropertyValue('--vh')])")
        assert len(vendors) == 3 and len({tuple(v) for v in vendors}) == 1 and vendors[0][0] and vendors[0][1]
        assert_no_errors(page)


def test_run_switcher_and_ranks(site, page):
    page.goto(f"{site}run.html?p=demo&r={MEDIUM_ID}")
    page.wait_for_selector("#run-switcher a")
    links = page.locator("#run-switcher a")
    assert links.count() == 3
    assert page.locator('#run-switcher a[aria-current="page"]').inner_text().strip() == "medium"
    assert "cheapest of 2" in page.locator("#metric-strip").inner_text()  # the failed run isn't ranked
    page.goto(f"{site}run.html?p=demo&r={HIGH_ID}#source")  # the tab is linkable
    page.wait_for_selector("#panel-source:not([hidden]) .source-view pre")
    assert page.locator(".source-files button.active").count() == 1  # first file opens right away
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


def test_run_whose_export_failed_is_a_finished_agent_run_without_a_build(site, page):
    page.goto(f"{site}run.html?p=demo&r={MEDIUM_ID}")
    page.wait_for_selector("#panel-game")
    panel = page.locator("#panel-game").inner_text()
    assert "no index.html produced" in panel and "No playable build" in panel  # the output step's error, then the message
    assert page.locator("[data-play]").count() == 0 and page.locator(".game-links").count() == 0
    badges = page.locator("#metric-strip .badge-bad").all_inner_texts()
    assert badges == ["export failed"]  # a distinct badge; the agent's state is complete, so no "failed" one
    assert page.locator("#metric-strip .run-error").count() == 0  # and the agent has no error line
    assert "not verified" in page.locator("#metric-strip .run-meta").inner_text()
    page.locator('#tabs button[data-tab="metrics"]').click()
    metrics = page.locator("#panel-metrics").inner_text()
    assert "output.ok" in metrics and "output.error" in metrics
    assert_no_errors(page)


def test_page_shows_export_failed_as_a_badge_and_counts_the_run_as_completed(site, page):
    page.goto(f"{site}page.html?p=demo")
    page.wait_for_selector("table.runs tbody tr")
    row = page.locator("tr.run-row").filter(has=page.locator("td", has_text="medium")).first
    assert row.locator('td[data-col="verified"] .badge-bad').inner_text() == "export failed"
    hl = page.locator("#highlights")
    assert "medium" in hl.locator(".hl", has_text="Fastest").inner_text()  # it still competes: the agent completed
    assert "1 failed" in hl.locator(".hl", has_text="Verified").inner_text()  # only the agent that failed counts as failed
    row.locator('td[data-col="effort"]').click()
    detail = page.locator("tr.run-detail")
    assert "no index.html produced" in detail.locator(".run-error").inner_text()
    assert "No playable build" in detail.inner_text()
    assert_no_errors(page)


def test_run_transcript_tool_calls_and_filters(site, page):
    page.goto(f"{site}run.html?p=demo&r={HIGH_ID}")
    page.locator('#tabs button[data-tab="transcript"]').click()
    page.wait_for_selector(".transcript .turn")

    assert page.locator(".tool-block").count() == 5  # bash, ls, write, edit, read
    assert page.locator(".badge-error").count() == 1  # the bash call errors
    assert page.locator(".tool-duration").first.inner_text() == "480ms"  # durationMs on the toolResult

    # a long write is collapsed behind "File (N lines)" and opens on click
    file_toggle = page.locator("details.out-collapse summary", has_text="File (31 lines)")
    assert file_toggle.count() == 1
    written = page.locator("details.out-collapse:has(summary:has-text('File')) pre.code")
    assert not written.is_visible()
    file_toggle.click()
    assert written.is_visible() and "print('line 30')" in written.inner_text()

    # an image in a tool result is shown as an <img> thumbnail with a caption, never as base64 text
    text = page.locator(".transcript").inner_text()
    assert "[image: image/png, 7 KB]" in text and "iVBORw0KGgo" not in text
    thumb = page.locator("figure.tool-image img")
    assert thumb.count() == 1 and thumb.get_attribute("src").startswith("data:image/png;base64,")
    assert thumb.evaluate("img => img.decode().then(() => img.naturalWidth)") == 48

    # each turn shows +m:ss since the session started, with the clock time on hover
    elapsed = page.locator(".turn-head .elapsed").first
    assert elapsed.inner_text().startswith("+0:") and elapsed.get_attribute("title")

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
    page.wait_for_function("() => document.querySelector('.source-view pre').textContent.includes('Demo')")
    assert "Demo" in page.locator(".source-view pre").inner_text()
    assert_no_errors(page)


def test_run_shows_harness_and_failed_state(site, page):
    page.goto(f"{site}run.html?p=demo&r={LOW_ID}")
    page.wait_for_selector("#metric-strip")
    strip_text = page.locator("#metric-strip").inner_text()
    assert "pi 0.87.1" in strip_text
    assert "failed" in page.locator("#metric-strip .badge-bad").inner_text()
    assert "pi exited 1: rate limited" in page.locator(".run-error").inner_text()

    page.locator('#tabs button[data-tab="metrics"]').click()
    metrics_text = page.locator("#panel-metrics").inner_text()
    assert "harness" in metrics_text.lower() and "pi 0.87.1" in metrics_text
    assert "failed" in metrics_text
    assert "pi exited 1: rate limited" in metrics_text
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
    assert page.locator(".compare-col", has_text="No playable build recorded").count() == 2
    assert page.locator(".compare-col", has_text="export failed").count() == 1
    assert_no_errors(page)


def test_compare_shows_harness_in_metrics_line(site, page):
    page.goto(f"{site}compare.html?p=demo")
    page.wait_for_selector(".compare-col")
    cols = page.locator(".compare-col")
    for i in range(3):
        metrics = cols.nth(i).locator(".compare-metrics").inner_text()
        assert metrics.startswith(("pi", "claude-code"))
    # the failed run's column shows its badge next to the title and its error
    low_col = cols.filter(has_text="low").first
    assert "failed" in low_col.locator("h3 .badge-bad").inner_text()
    assert "pi exited 1: rate limited" in low_col.locator(".run-error").inner_text()
    assert_no_errors(page)


def test_compare_popout_opens_sandboxed_play_window(site, page):
    page.goto(f"{site}compare.html?p=demo")
    page.wait_for_selector(".compare-col")
    # only the run with a game gets the button (the other two have nothing to show)
    assert page.locator(".compare-col a.popout").count() == 1
    pop = page.locator(".compare-col", has=page.locator("a.popout")).locator("a.popout")
    assert pop.get_attribute("href") == f"play.html?p=demo&r={HIGH_ID}"
    assert pop.get_attribute("data-play") is None
    with page.expect_popup() as info:
        pop.click()
    popup = info.value
    popup.on("pageerror", lambda e: page._page_errors.append(str(e)))
    popup.wait_for_selector("#play iframe")
    assert popup.url.endswith(f"play.html?p=demo&r={HIGH_ID}")
    frames = popup.locator("iframe")
    assert frames.count() == 1
    assert frames.get_attribute("sandbox") == "allow-scripts allow-pointer-lock"
    assert frames.get_attribute("src").endswith("game/index.html")
    bar = popup.locator("#play-bar").inner_text()
    assert "model-x" in bar and "high" in bar
    assert popup.locator("#play-bar a").get_attribute("href") == f"run.html?p=demo&r={HIGH_ID}"
    assert_no_errors(page)
    popup.close()


def test_play_media_run_uses_img_only(site, page):
    page.goto(f"{site}play.html?p=art&r={ART_HIGH_ID}")
    page.wait_for_selector(".media-grid")
    page.wait_for_function("() => [...document.querySelectorAll('.media-grid img')].every(i => i.complete && i.naturalWidth > 0)")
    assert page.locator(".media-grid img").count() == 2
    assert page.evaluate("window.svgRan") is None
    assert page.locator("#play svg, #play object, #play embed, #play iframe").count() == 0
    assert_no_errors(page)


def test_play_bad_params_show_messages(site, page):
    page.goto(f"{site}play.html")
    page.wait_for_selector(".msg-error")
    assert "Missing" in page.locator("#play").inner_text()
    page.goto(f"{site}play.html?p=demo&r=nope")
    page.wait_for_selector(".msg-error")
    assert 'No run "nope"' in page.locator("#play").inner_text()
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


# ---------------------------------------------------------------- media pages (kind "media")
def test_media_page_shows_gallery_and_expands_outputs(site, page):
    page.goto(f"{site}page.html?p=art")
    page.wait_for_selector("#gallery .card")
    cards = page.locator("#gallery .card")
    assert cards.count() == 2
    high = cards.filter(has_text="high")
    assert "3 files" in high.inner_text()
    assert high.locator("img.thumb").get_attribute("src").endswith("/media/circle.svg")
    assert "no output" in cards.filter(has_text="low").inner_text()

    rows = page.locator("tr.run-row")
    rows.filter(has=page.locator("td", has_text="high")).first.locator('td[data-col="effort"]').click()
    detail = page.locator("tr.run-detail")
    assert detail.locator(".media-item").count() == 3
    assert detail.locator("video").count() == 1 and detail.locator("iframe").count() == 0
    assert_no_errors(page)


def test_media_run_output_tab_shows_images_and_video(site, page):
    page.goto(f"{site}run.html?p=art&r={ART_HIGH_ID}")
    page.wait_for_selector(".media-grid")
    assert page.locator('#tabs button[data-tab="game"]').inner_text() == "Output"
    imgs = page.locator(".media-grid img")
    assert imgs.count() == 2
    page.wait_for_function("() => [...document.querySelectorAll('.media-grid img')].every(i => i.complete && i.naturalWidth > 0)")
    video = page.locator(".media-grid video")
    assert video.get_attribute("poster").endswith("/media/clip.poster.jpg")
    assert video.get_attribute("autoplay") is None and video.evaluate("v => v.paused")
    # the SVG is only ever an <img>: its embedded <script> must not have run, and there's no
    # inline <svg> or <object>/<embed>/<iframe> carrying model output
    assert page.evaluate("window.svgRan") is None
    assert page.locator("#panel-game svg, #panel-game object, #panel-game embed, #panel-game iframe").count() == 0
    svg_link = page.locator(".media-grid a", has_text="download").first
    assert svg_link.get_attribute("download") == "circle.svg"
    assert "1.0s" in page.locator(".media-grid").inner_text()
    assert_no_errors(page)


def test_media_run_without_output_says_so(site, page):
    page.goto(f"{site}run.html?p=art&r=model-x-low-20260102-000000")
    page.wait_for_selector("#panel-game .msg")
    assert "No output files" in page.locator("#panel-game").inner_text()
    assert "no files in ./output/" in page.locator(".run-error").inner_text()


def test_media_compare_shows_outputs_and_no_play_all(site, page):
    page.goto(f"{site}compare.html?p=art")
    page.wait_for_selector(".compare-col")
    assert page.locator(".compare-col").count() == 2
    assert page.locator(".compare-col .media-item").count() == 3
    assert page.locator(".compare-col", has_text="No output files recorded").count() == 1
    assert not page.locator("#play-all").is_visible()
    assert_no_errors(page)


def test_group_by_vendor_orders_groups_by_best_rank(site, page):
    page.goto(f"{site}compare.html?p=demo")
    page.wait_for_selector(".compare-col")
    res = page.evaluate("""async () => {
      const { groupByVendor } = await import("./assets/common.js");
      const run = (id, model, rank) => ({ id, model, rank });
      const names = (rs) => groupByVendor(rs).map((g) => g.name + ":" + g.runs.map((r) => r.id).join(","));
      const plain = [run("a1", "anthropic/claude-x"), run("o1", "openai-codex/gpt-6"), run("a2", "anthropic/claude-x"), run("d1", "openrouter/deepseek/v4"), run("z1", "zeta/m")];
      const ranked = [run("o1", "openai-codex/gpt-6", 1), run("a1", "anthropic/claude-x", 2), run("a2", "anthropic/claude-x"), run("d1", "openrouter/deepseek/v4")];
      return [names(plain), names(ranked)];
    }""")
    assert res[0] == ["Anthropic:a1,a2", "DeepSeek:d1", "OpenAI:o1", "Zeta:z1"]  # unranked: alphabetical, order inside kept
    assert res[1] == ["OpenAI:o1", "Anthropic:a1,a2", "DeepSeek:d1"]  # best rank first, then unranked
    assert_no_errors(page)


def test_compare_groups_runs_by_vendor(site, page):
    page.goto(f"{site}compare.html?p=demo")
    page.wait_for_selector(".compare-col")
    assert page.locator(".vendor-group").count() == 1
    head = page.locator(".vendor-group .vendor-head").inner_text()
    assert "3 runs" in head and head.split()[0].lower() == page.locator(".vendor-group").get_attribute("data-vendor") or "3 runs" in head
    assert page.locator(".vendor-group .compare-columns > .compare-col").count() == 3
    page.goto(f"{site}compare.html?p=demo&r={HIGH_ID}")
    page.wait_for_selector(".compare-col")
    assert page.locator(".vendor-group").count() == 1
    assert "1 run" in page.locator(".vendor-head").inner_text() and "1 runs" not in page.locator(".vendor-head").inner_text()
    assert_no_errors(page)


def test_compare_lays_runs_out_in_a_wrapping_grid(site, page):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(f"{site}compare.html?p=demo")
    page.wait_for_selector(".compare-col")
    boxes = [page.locator(".compare-col").nth(i).bounding_box() for i in range(3)]
    assert len({round(b["y"]) for b in boxes}) == 1  # wide: 3 side by side, equal widths
    assert len({round(b["width"]) for b in boxes}) == 1
    page.set_viewport_size({"width": 900, "height": 900})
    boxes = [page.locator(".compare-col").nth(i).bounding_box() for i in range(3)]
    assert boxes[0]["y"] == boxes[1]["y"] < boxes[2]["y"]  # narrower: wraps into a second row
    assert boxes[2]["x"] == boxes[0]["x"]
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")  # no sideways scrolling
    page.set_viewport_size({"width": 390, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert_no_errors(page)


# ---------------------------------------------------------------- your ranking
def test_ranking_is_shown_read_only_on_the_published_site(site, page):
    page.goto(f"{site}page.html?p=art")
    page.wait_for_selector("tr.run-row")
    assert page.locator('th[data-key="rank"]').get_attribute("aria-sort") == "ascending"  # ranked: default sort
    first = page.locator("tr.run-row").first
    assert first.locator('td[data-col="rank"]').inner_text() == "🥇" and "high" in first.inner_text()
    assert page.locator(".rank-select").count() == 0 and page.locator("#rank-status").count() == 0
    assert page.locator("#gallery .card").first.locator(".rank-chip").inner_text() == "🥇"
    page.goto(f"{site}compare.html?p=art")
    page.wait_for_selector(".compare-col")
    assert page.locator(".compare-col").first.locator(".rank-chip").inner_text() == "🥇"
    page.goto(f"{site}run.html?p=art&r={ART_HIGH_ID}")
    page.wait_for_selector("#title .rank-chip")
    assert_no_errors(page)


@pytest.fixture
def bench_served(tmp_path):
    """The viewer served by `bench serve` itself (which has the local ranking API) on a copy of the fixture site."""
    from bench.serve import serve_in_thread

    docs = tmp_path / "docs"
    docs.mkdir()
    for f in REPO.glob("docs/*.html"):
        shutil.copy(f, docs / f.name)
    shutil.copytree(REPO / "docs/assets", docs / "assets")
    shutil.copytree(FIXTURE_DATA, docs / "data")
    server = serve_in_thread(docs)
    yield docs, f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()
    server.server_close()


def test_ranking_can_be_edited_through_bench_serve(bench_served, page):
    import json
    import re

    docs, base = bench_served
    page.goto(f"{base}page.html?p=demo")
    page.wait_for_selector(".rank-select")
    assert page.locator(".rank-select").count() == 3
    assert "publish" in page.locator("#rank-status").inner_text()

    row = lambda effort: page.locator("tr.run-row").filter(has=page.locator('td[data-col="effort"]', has_text=re.compile(f"^{effort}$"))).first
    row("medium").locator(".rank-select").select_option("1")
    page.wait_for_function("() => document.getElementById('rank-status').textContent.startsWith('saved')")
    assert page.locator("tr.run-detail").count() == 0  # picking a rank doesn't expand the row
    row("high").locator(".rank-select").select_option("2")
    page.wait_for_function("() => document.getElementById('rank-status').textContent.startsWith('saved')")

    ranking = json.loads((docs / "data/demo/ranking.json").read_text())["ranks"]
    assert ranking == {MEDIUM_ID: 1, HIGH_ID: 2}
    results = {r["id"]: r["rank"] for r in json.loads((docs / "data/demo/page.json").read_text())["runs"]}
    assert results == {MEDIUM_ID: 1, HIGH_ID: 2, LOW_ID: None}

    page.reload()  # sorted by the saved ranking now
    page.wait_for_selector(".rank-select")
    efforts = page.locator("table.runs tbody tr td[data-col='effort']").all_inner_texts()
    assert efforts == ["medium", "high", "low"]
    assert_no_errors(page)


def test_run_title_has_no_stray_text_for_unranked_runs(site, page):
    for slug, run_id in (("demo", HIGH_ID), ("art", "model-x-low-20260102-000000")):  # no rank key / rank null
        page.goto(f"{site}run.html?p={slug}&r={run_id}")
        page.wait_for_selector("#title .effort")
        title = page.locator("#title").inner_text()
        assert "null" not in title and "undefined" not in title, title
    assert_no_errors(page)


def test_model_parts_split_off_a_pinned_openrouter_upstream(site, page):
    page.goto(f"{site}index.html")
    parts = page.evaluate("""async () => {
      const { modelParts, modelLabel } = await import("./assets/common.js");
      const label = modelLabel("openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8");
      return { routed: modelParts("openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8"), plain: modelParts("anthropic/claude-opus-5-5"),
               label: [...label.children].map((c) => c.className + ":" + c.textContent) };
    }""")
    assert parts["routed"] == {"provider": "openrouter/deepseek", "name": "deepseek-v4.1-flash", "via": "deepinfra/fp8",
                               "short": "deepseek-v4.1-flash via deepinfra/fp8"}
    assert parts["plain"] == {"provider": "anthropic", "name": "claude-opus-5-5", "via": "", "short": "claude-opus-5-5"}
    assert parts["label"] == ["model-name:deepseek-v4.1-flash", "model-provider:openrouter/deepseek", "model-via:via deepinfra/fp8"]


@pytest.mark.parametrize("view,selector", [
    ("index.html", ".card"),
    ("page.html?p=demo", "tr.run-row"),
    ("compare.html?p=demo", ".compare-col"),
    (f"run.html?p=demo&r={HIGH_ID}#transcript", ".transcript .content-md"),
    (f"play.html?p=demo&r={HIGH_ID}", "iframe"),
])
def test_viewer_uses_only_local_resources(site, page, view, selector):
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    # Simulate unavailable outside network while recording any attempted request.
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(site) else route.abort())
    page.goto(site + view)
    page.wait_for_selector(selector)
    page.wait_for_load_state("networkidle")
    assert all(url.startswith(site) for url in requests), requests
    if not view.startswith("run.html"):
        assert not any("marked.esm.js" in url for url in requests)
    assert_no_errors(page)


@pytest.mark.parametrize("view", ["page", "run"])
def test_fullscreen_links_use_sandboxed_play(site, page, view):
    page.goto(site + (f"run.html?p=demo&r={HIGH_ID}" if view == "run" else "page.html?p=demo"))
    if view == "page":
        page.locator("tr.run-row").filter(has=page.locator("td[data-col=effort]", has_text="high")).locator("td[data-col=effort]").click()
    link = page.locator(".game-links a", has_text="Open full screen")
    assert link.get_attribute("href") == f"play.html?p=demo&r={HIGH_ID}"
    assert "unsandboxed" not in link.inner_text()
    assert page.locator('a[href*="game/index.html"]').count() == 0
    with page.expect_popup() as popup:
        link.click()
    out = popup.value
    out.wait_for_selector("iframe")
    assert out.locator("iframe").get_attribute("sandbox") == "allow-scripts allow-pointer-lock"
    out.close()
    assert_no_errors(page)


def test_markdown_tokens_render_without_html_or_external_network(site, page):
    page.goto(site)
    page.wait_for_selector(".card")
    source = '''# Heading

**bold** *em* ~~gone~~ `a < b & c` &amp; &#65;

> quote

3. third
4. fourth

- [x] done
- [ ] todo

| A | B |
| :- | -: |
| one | two |

---

```python
if a < b && c > d:
    pass
```

<script>window.markdownRan = true</script>

[bad](javascript:alert%281%29) [encoded](jav&#x61;script:alert%281%29)
[data](data:text/html,evil) [safe](https://example.com) [local](page.html?p=demo)

![remote](https://example.com/tracker.png)
'''
    page.evaluate('''async source => {
      const { renderMarkdown } = await import('./assets/markdown.js');
      const container = document.createElement('div');
      container.id = 'markdown-test';
      document.body.append(container);
      renderMarkdown(container, source);
    }''', source)
    md = page.locator("#markdown-test")
    assert md.locator("h1").inner_text() == "Heading"
    assert md.locator("strong").inner_text() == "bold"
    assert md.locator("em").inner_text() == "em"
    assert md.locator("del").inner_text() == "gone"
    assert md.locator("ol").get_attribute("start") == "3"
    assert md.locator("input[checked][disabled]").count() == 1
    assert md.locator("table th").count() == 2
    assert md.locator("blockquote").inner_text() == "quote"
    assert "a < b & c" in md.inner_text() and "& A" in md.inner_text()
    assert "if a < b && c > d:" in md.locator("pre code").inner_text()
    assert "<script>" in md.inner_text()
    assert md.locator("script, img").count() == 0
    assert md.locator("a[href]").count() == 2
    assert not page.evaluate("window.markdownRan === true")
    assert_no_errors(page)


@pytest.mark.parametrize("view,selector", [
    ("page.html?p=demo", "tr.run-row"),
    ("compare.html?p=demo", ".compare-col"),
    (f"run.html?p=demo&r={HIGH_ID}", "#title .effort"),
    (f"play.html?p=demo&r={HIGH_ID}", "iframe"),
])
def test_page_views_load_one_page_json(site, page, view, selector):
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    page.goto(site + view)
    page.wait_for_selector(selector)
    page.wait_for_load_state("networkidle")
    assert sum(url.endswith("/data/demo/page.json") for url in requests) == 1
    assert not any("results.json" in url or url.endswith("/run.json") for url in requests)
    assert_no_errors(page)
