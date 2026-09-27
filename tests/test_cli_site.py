"""bench rm / rebuild / list, and the shape of pages.json / results.json / page.json."""

import json

from bench.cli import main


def test_pages_and_results_json_shapes(bench_root, effort_run):
    main(["import", str(effort_run), "--root", str(bench_root)])

    pages = json.loads((bench_root / "docs/data/pages.json").read_text())
    assert len(pages) == 1
    p = pages[0]
    for key in ("slug", "title", "n_runs", "models", "updated", "thumb"):
        assert key in p
    assert p["slug"] == "voxel-horse"
    assert p["n_runs"] == 2
    assert p["models"] == ["openai-codex/gpt-6-sol"]
    assert p["thumb"] == f"data/voxel-horse/runs/{_high_id(bench_root)}/thumb.png"

    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    for key in ("slug", "title", "prompt", "created", "updated"):
        assert key in page
    assert page["prompt"] == "draw a running horse"
    assert page["title"] == "Voxel horse"

    results = json.loads((bench_root / "docs/data/voxel-horse/results.json").read_text())
    assert [r["effort"] for r in results] == ["low", "high"]  # sorted by started_at then effort order
    run = results[0]
    for key in (
        "id", "page", "model", "effort", "started_at", "source_dir", "verified",
        "metrics", "thumb", "game", "session", "source",
    ):
        assert key in run
    for key in (
        "duration_ms", "cost_usd", "tool_calls", "turns", "tokens_total",
        "tokens_input", "tokens_output", "tokens_reasoning", "tokens_cache_read",
    ):
        assert key in run["metrics"]


def _high_id(bench_root):
    results = json.loads((bench_root / "docs/data/voxel-horse/results.json").read_text())
    return next(r["id"] for r in results if r["effort"] == "high")


def test_final_prompt_is_the_subagent_brief(bench_root, effort_run):
    main(["import", str(effort_run), "--root", str(bench_root)])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    # first user message of the cleaned session, with the per-effort output dir normalized
    assert page["final_prompt"] == "Task: draw a running horse in ~/effort-runs/x. Output directory: ./<effort>/."
    main(["rebuild", "--root", str(bench_root)])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    assert page["final_prompt"].startswith("Task: draw a running horse")


def test_prompt_md_is_cleaned_and_secret_scanned(bench_root, effort_run):
    from pathlib import Path

    (effort_run / "prompt.md").write_text(f"draw a horse in {Path.home()}/x with key sk-abcdefghijklmnopqrstuvwxyz123456")
    rc = main(["import", str(effort_run), "--root", str(bench_root)])
    assert rc != 0 and not (bench_root / "docs/data/voxel-horse").exists()  # aborted before writing
    main(["import", str(effort_run), "--root", str(bench_root), "--redact"])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    assert page["prompt"] == "draw a horse in ~/x with key [REDACTED]"


def test_prompt_is_the_originating_prompt_md_and_refreshes(bench_root, effort_run):
    # the page shows prompt.md (the originating prompt), not the subagent brief in the transcript
    main(["import", str(effort_run), "--root", str(bench_root)])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    assert page["prompt"] == "draw a running horse"
    (effort_run / "prompt.md").write_text("draw a galloping horse\n")
    main(["import", str(effort_run), "--root", str(bench_root)])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    assert page["prompt"] == "draw a galloping horse"


def test_rm_run_then_rm_page(bench_root, effort_run):
    main(["import", str(effort_run), "--root", str(bench_root)])
    high_id = _high_id(bench_root)

    rc = main(["rm", "voxel-horse", high_id, "--root", str(bench_root)])
    assert rc == 0
    results = json.loads((bench_root / "docs/data/voxel-horse/results.json").read_text())
    assert len(results) == 1
    assert results[0]["effort"] == "low"
    assert not (bench_root / "docs/data/voxel-horse/runs" / high_id).exists()

    low_id = results[0]["id"]
    rc = main(["rm", "voxel-horse", low_id, "--root", str(bench_root)])
    assert rc == 0
    # removing the last run removes the whole page
    assert not (bench_root / "docs/data/voxel-horse").exists()
    pages = json.loads((bench_root / "docs/data/pages.json").read_text())
    assert pages == []


def test_rm_whole_page(bench_root, effort_run):
    main(["import", str(effort_run), "--root", str(bench_root)])
    rc = main(["rm", "voxel-horse", "--root", str(bench_root)])
    assert rc == 0
    assert not (bench_root / "docs/data/voxel-horse").exists()


def test_rm_unknown_page_is_an_error(bench_root, effort_run, capsys):
    main(["import", str(effort_run), "--root", str(bench_root)])
    rc = main(["rm", "no-such-page", "--root", str(bench_root)])
    assert rc != 0
    assert "no such page" in capsys.readouterr().err


def test_rebuild_gcs_unreferenced_engines(bench_root, effort_run_factory):
    run_a = effort_run_factory(folder_name="2026-09-26-001500-gpt6sol-page-a", levels=["low"])
    run_b = effort_run_factory(folder_name="2026-09-26-001600-gpt6sol-page-b", levels=["low"])
    # give page-b a different (larger) fake engine so it dedupes into a second engine dir
    (run_b / "wasm/low/index.wasm").write_bytes(b"DIFFERENT-WASM-BYTES")

    main(["import", str(run_a), "--root", str(bench_root)])
    main(["import", str(run_b), "--root", str(bench_root)])
    assert len(list((bench_root / "docs/engines").iterdir())) == 2

    main(["rm", "page-a", "--root", str(bench_root)])
    remaining = list((bench_root / "docs/engines").iterdir())
    assert len(remaining) == 1

    results_b = json.loads((bench_root / "docs/data/page-b/results.json").read_text())
    assert remaining[0].name == results_b[0]["game"]["engine"]


def test_list_runs_without_error(bench_root, effort_run, capsys):
    main(["import", str(effort_run), "--root", str(bench_root)])
    rc = main(["list", "--root", str(bench_root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "voxel-horse" in out
    assert "gpt-6-sol" in out


def test_list_on_empty_site(bench_root, capsys):
    rc = main(["list", "--root", str(bench_root)])
    assert rc == 0
    assert "no pages" in capsys.readouterr().out
