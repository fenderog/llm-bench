"""art-crit rm / rebuild / list, and the shape of pages.json / page.json."""

import json

from art_crit.cli import main


def test_pages_and_page_json_shapes(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])

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

    results = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())["runs"]
    assert [r["effort"] for r in results] == ["low", "high"]  # sorted by started_at then effort order
    assert not (bench_root / "docs/data/voxel-horse/results.json").exists()
    run = results[0]
    original = json.loads((bench_root / "docs/data/voxel-horse/runs" / run["id"] / "run.json").read_text())
    assert "rank" not in original
    for key in (
        "id", "page", "model", "effort", "kind", "started_at", "batch", "harness", "state", "error", "route",
        "metrics", "thumb", "output", "session", "source",
    ):
        assert key in run
    for key in (
        "duration_ms", "cost_usd", "tool_calls", "turns", "tokens_total",
        "tokens_input", "tokens_output", "tokens_reasoning", "tokens_cache_read",
    ):
        assert key in run["metrics"]


def _high_id(bench_root):
    results = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())["runs"]
    return next(r["id"] for r in results if r["effort"] == "high")


def test_final_prompt_is_the_agents_brief(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    # first user message of the cleaned transcript
    assert page["final_prompt"] == "Task: draw a running horse in ~/effort-runs/x."
    main(["rebuild", "--root", str(bench_root)])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    assert page["final_prompt"].startswith("Task: draw a running horse")


def test_prompt_md_is_cleaned_and_secret_scanned(bench_root, batch_dir):
    from pathlib import Path

    (batch_dir / "prompt.md").write_text(f"draw a horse in {Path.home()}/x with key sk-abcdefghijklmnopqrstuvwxyz123456")
    rc = main(["import", str(batch_dir), "--root", str(bench_root)])
    assert rc != 0 and not (bench_root / "docs/data/voxel-horse").exists()  # aborted before writing
    main(["import", str(batch_dir), "--root", str(bench_root), "--redact"])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    assert page["prompt"] == "draw a horse in ~/x with key [REDACTED]"


def test_prompt_is_the_originating_prompt_md_and_refreshes(bench_root, batch_dir):
    # the page shows prompt.md (the originating prompt), not the agent's brief in the transcript
    main(["import", str(batch_dir), "--root", str(bench_root)])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    assert page["prompt"] == "draw a running horse"
    (batch_dir / "prompt.md").write_text("draw a galloping horse\n")
    main(["import", str(batch_dir), "--root", str(bench_root)])
    page = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())
    assert page["prompt"] == "draw a galloping horse"


def test_rm_run_then_rm_page(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    high_id = _high_id(bench_root)

    rc = main(["rm", "voxel-horse", high_id, "--root", str(bench_root)])
    assert rc == 0
    results = json.loads((bench_root / "docs/data/voxel-horse/page.json").read_text())["runs"]
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


def test_rm_whole_page(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    rc = main(["rm", "voxel-horse", "--root", str(bench_root)])
    assert rc == 0
    assert not (bench_root / "docs/data/voxel-horse").exists()


def test_rm_unknown_page_is_an_error(bench_root, batch_dir, capsys):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    rc = main(["rm", "no-such-page", "--root", str(bench_root)])
    assert rc != 0
    assert "no such page" in capsys.readouterr().err


def test_rebuild_gcs_unreferenced_engines(bench_root, batch_factory):
    run_a = batch_factory(slug="page-a", levels=["low"])
    run_b = batch_factory(slug="page-b", levels=["low"])
    # give page-b a different (larger) fake engine so it dedupes into a second engine dir
    (run_b / "gpt-6-sol-low-20260926-001158/output/index.wasm").write_bytes(b"DIFFERENT-WASM-BYTES")

    main(["import", str(run_a), "--root", str(bench_root)])
    main(["import", str(run_b), "--root", str(bench_root)])
    assert len(list((bench_root / "docs/engines").iterdir())) == 2

    main(["rm", "page-a", "--root", str(bench_root)])
    remaining = list((bench_root / "docs/engines").iterdir())
    assert len(remaining) == 1

    results_b = json.loads((bench_root / "docs/data/page-b/page.json").read_text())["runs"]
    assert remaining[0].name == results_b[0]["output"]["engine"]


def test_list_runs_without_error(bench_root, batch_dir, capsys):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    rc = main(["list", "--root", str(bench_root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "voxel-horse" in out
    assert "gpt-6-sol" in out


def test_list_on_empty_site(bench_root, capsys):
    rc = main(["list", "--root", str(bench_root)])
    assert rc == 0
    assert "no pages" in capsys.readouterr().out


def test_rebuild_removes_legacy_results(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    legacy = bench_root / "docs/data/voxel-horse/results.json"
    legacy.write_text("[]")
    main(["rebuild", "--root", str(bench_root)])
    assert not legacy.exists()
    assert len(json.loads(legacy.with_name("page.json").read_text())["runs"]) == 2


def test_rename_moves_page_and_rewrites_slug(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    rc = main(["rename", "voxel-horse", "horse", "--root", str(bench_root)])
    assert rc == 0
    data = bench_root / "docs/data"
    assert not (data / "voxel-horse").exists()
    page = json.loads((data / "horse/page.json").read_text())
    assert page["slug"] == "horse"
    assert page["title"] == "Horse"  # a title derived from the old slug follows it
    assert all(r["page"] == "horse" for r in page["runs"])
    pages = json.loads((data / "pages.json").read_text())
    assert [p["slug"] for p in pages] == ["horse"]
    assert pages[0]["thumb"].startswith("data/horse/runs/")

    main(["rename", "horse", "stallion", "-t", "Big Stallion", "--root", str(bench_root)])
    assert json.loads((data / "stallion/page.json").read_text())["title"] == "Big Stallion"

    main(["rename", "stallion", "pony", "--root", str(bench_root)])
    assert json.loads((data / "pony/page.json").read_text())["title"] == "Big Stallion"  # a custom title stays


def test_rename_refuses_bad_targets(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    root = str(bench_root)
    assert main(["rename", "nope", "x", "--root", root]) != 0
    assert main(["rename", "voxel-horse", "Bad Slug", "--root", root]) != 0
    assert main(["rename", "voxel-horse", "voxel-horse", "--root", root]) != 0
    assert (bench_root / "docs/data/voxel-horse").is_dir()
