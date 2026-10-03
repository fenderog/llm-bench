"""bench import: publishing run directories: ids/slugs, Godot engine dedupe + html rewrite, cleaning,
secrets, dry-run, idempotency. Uses the synthetic batch_dir fixture from conftest.py."""

import json
from pathlib import Path

from datetime import datetime

from bench import clean
from bench.cli import main
from bench.util import make_run_id, title_from_slug


def run_data_json(root, slug):
    return json.loads((root / "docs/data" / slug / "page.json").read_text())["runs"]


def run_dir(root, slug, run_id):
    return root / "docs/data" / slug / "runs" / run_id


# --- run id derivation (pure functions) ----------------------------------------------------


def test_make_run_id_matches_spec_example():
    run_id = make_run_id("openai-codex/gpt-6-sol", "high", datetime(2026, 9, 26, 0, 11, 58))
    assert run_id == "gpt-6-sol-high-20260926-001158"


def test_title_from_slug():
    assert title_from_slug("voxel-horse") == "Voxel horse"


# --- import end to end -----------------------------------------------------------------------


def test_import_creates_a_run_per_level(bench_root, batch_dir, capsys):
    rc = main(["import", str(batch_dir), "--root", str(bench_root)])
    assert rc == 0
    runs = run_data_json(bench_root, "voxel-horse")
    assert sorted(r["effort"] for r in runs) == ["high", "low"]
    ids = {r["id"] for r in runs}
    assert ids == {"gpt-6-sol-low-20260926-001158", "gpt-6-sol-high-20260926-001158"}
    out = capsys.readouterr().out
    assert "gpt-6-sol-low-20260926-001158" in out and "bytes" in out


def test_page_override(bench_root, batch_dir):
    rc = main(["import", str(batch_dir), "--page", "custom-slug", "--root", str(bench_root)])
    assert rc == 0
    runs = run_data_json(bench_root, "custom-slug")
    assert len(runs) == 2
    assert all(r["page"] == "custom-slug" for r in runs)


def test_engine_dedupe_one_dir_for_two_levels(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    engines = list((bench_root / "docs/engines").iterdir())
    assert len(engines) == 1
    runs = run_data_json(bench_root, "voxel-horse")
    assert len({r["output"]["engine"] for r in runs}) == 1
    assert runs[0]["output"]["engine"] == engines[0].name
    # engine files never end up inside a run's own directory
    for r in runs:
        rd = run_dir(bench_root, "voxel-horse", r["id"])
        assert not list(rd.rglob("*.wasm"))
        assert not (rd / "game" / "index.js").exists()


def test_html_rewrite_sets_executable_mainpack_filesizes_and_script_src(bench_root, batch_dir):
    import os
    import re
    from pathlib import Path

    main(["import", str(batch_dir), "--root", str(bench_root)])
    runs = run_data_json(bench_root, "voxel-horse")
    sha12 = runs[0]["output"]["engine"]
    r = run_dir(bench_root, "voxel-horse", runs[0]["id"])
    html = (r / "game" / "index.html").read_text()
    final_game_dir = Path("data") / "voxel-horse" / "runs" / runs[0]["id"] / "game"
    rel = os.path.relpath(Path("engines") / sha12 / "godot", final_game_dir)
    assert f'<script src="{rel}.js"></script>' in html

    cfg = json.loads(re.search(r"const GODOT_CONFIG = (\{.*?\});", html).group(1))
    assert cfg["executable"] == rel
    assert cfg["mainPack"] == "index.pck"
    assert f"{rel}.wasm" in cfg["fileSizes"]
    assert "index.wasm" not in cfg["fileSizes"]
    # and it actually resolves to the stored engine file from the run's game dir
    resolved = (r / "game" / f"{rel}.wasm").resolve()
    assert resolved == (bench_root / "docs/engines" / sha12 / "godot.wasm").resolve()


def test_threads_refused_without_flag_and_allowed_with_it(bench_root, batch_factory):
    run = batch_factory(slug="thready", levels=["high"], threads=True)
    rc = main(["import", str(run), "--root", str(bench_root)])
    assert rc != 0
    assert not (bench_root / "docs/data/thready").exists()

    rc = main(["import", str(run), "--allow-threads", "--root", str(bench_root)])
    assert rc == 0
    runs = run_data_json(bench_root, "thready")
    assert runs[0]["output"]["threads"] is True


def test_output_record_carries_ok_verified_and_error(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    for r in run_data_json(bench_root, "voxel-horse"):
        assert r["output"]["kind"] == "godot" and r["output"]["entry"] == "game/index.html"
        assert (r["output"]["ok"], r["output"]["verified"], r["output"]["error"]) == (True, True, None)
        assert r["thumb"] == "thumb.png" and "game" not in r and "verified" not in r


def test_source_files_exclude_session_and_editor_cache(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    runs = run_data_json(bench_root, "voxel-horse")
    r = run_dir(bench_root, "voxel-horse", runs[0]["id"])
    files = runs[0]["source"]["files"]
    assert "project.godot" in files
    assert "scenes/main.tscn" in files
    assert "scripts/main.gd" in files
    assert "export_presets.cfg" in files  # one of the project's own files
    assert ".DS_Store" not in files
    assert not list((r / "source").rglob(".godot"))
    assert not (r / "source" / ".godot").exists()


# --- cleaning ---------------------------------------------------------------------------------


def test_cleaning_strips_keys_and_rewrites_home(bench_root, batch_dir):
    from pathlib import Path

    main(["import", str(batch_dir), "--root", str(bench_root)])
    runs = run_data_json(bench_root, "voxel-horse")
    r = run_dir(bench_root, "voxel-horse", runs[0]["id"])
    convo = (r / "session/conversation.json").read_text()
    assert "thinkingSignature" not in convo
    assert "encrypted_content" not in convo
    assert '"pid"' not in convo
    assert '"sessionId"' not in convo
    assert str(Path.home()) not in convo
    assert "~" in convo

    # only the transcript is published from harness/ (the raw stdout, the brief and the like stay local)
    assert sorted(p.name for p in (r / "session").iterdir()) == ["conversation.json"]
    assert runs[0]["session"] == {"conversation": "session/conversation.json"}


def test_bench_toml_extra_rewrite(bench_root, batch_dir):
    (bench_root / "bench.toml").write_text('[clean]\nrewrite = { "/Volumes/M2SSD" = "<vol>" }\n')
    convo_path = batch_dir / "gpt-6-sol-low-20260926-001158" / "harness" / "conversation.json"
    convo_path.write_text(convo_path.read_text().replace("effort-runs/x", "/Volumes/M2SSD/effort-runs/x"))

    main(["import", str(batch_dir), "--root", str(bench_root)])
    runs = run_data_json(bench_root, "voxel-horse")
    low_id = next(r["id"] for r in runs if r["effort"] == "low")
    convo = (run_dir(bench_root, "voxel-horse", low_id) / "session/conversation.json").read_text()
    assert "/Volumes/M2SSD" not in convo
    assert "<vol>" in convo


# --- secrets ------------------------------------------------------------------------------------


def test_secret_hit_aborts_before_writing_anything(bench_root, batch_factory, capsys):
    run = batch_factory(slug="secretrun", secret="sk-" + "A" * 24)
    rc = main(["import", str(run), "--root", str(bench_root)])
    assert rc != 0
    assert not (bench_root / "docs/data/secretrun").exists()
    err = capsys.readouterr().err
    assert "secret" in err.lower()
    assert "sk-A" in err or "sk-A…"[:5] in err  # masked prefix printed, not the full secret
    assert "A" * 24 not in err


def test_secret_redact_continues_and_scrubs(bench_root, batch_factory):
    run = batch_factory(slug="redactrun", secret="sk-" + "B" * 24)
    rc = main(["import", str(run), "--redact", "--root", str(bench_root)])
    assert rc == 0
    runs = run_data_json(bench_root, "redactrun")
    low_id = next(r["id"] for r in runs if r["effort"] == "low")
    convo = (run_dir(bench_root, "redactrun", low_id) / "session/conversation.json").read_text()
    assert "B" * 24 not in convo
    assert "[REDACTED]" in convo


def test_image_data_skips_rewrites_and_secret_scan_but_text_does_not():
    home = str(Path.home())
    lucky = "AKIA" + "Q" * 16 + "/" + home.replace("/", "+") + "=="  # base64 that looks like an AWS key
    convo = [{"type": "message", "message": {"role": "toolResult", "content": [
        {"type": "text", "text": f"opened {home}/shot.png"},
        {"type": "image", "mimeType": "image/jpeg", "data": lucky},
        {"type": "image", "mimeType": "image/jpeg", "data": "not base64: AKIA" + "Z" * 16},
    ]}}]
    images = []
    text, _ = clean.clean_json(json.dumps(convo), [(home, "~")], images)
    hits = clean.scan_secrets(text)
    assert [h[1] for h in hits] == ["AKIA" + "Z" * 16]  # only the data that isn't base64 is still scanned
    content = json.loads(clean.restore_images(text, images))[0]["message"]["content"]
    assert content[0]["text"] == "opened ~/shot.png" and content[1]["data"] == lucky


# --- dry-run / idempotency ------------------------------------------------------------------


def test_dry_run_writes_nothing(bench_root, batch_dir, capsys):
    rc = main(["import", str(batch_dir), "--dry-run", "--root", str(bench_root)])
    assert rc == 0
    assert not (bench_root / "docs/data").exists() or not list((bench_root / "docs/data").iterdir())
    out = capsys.readouterr().out
    assert "dry-run" in out


def test_a_single_run_directory_can_be_imported(bench_root, batch_dir):
    assert main(["import", str(batch_dir / "gpt-6-sol-high-20260926-001158"), "--root", str(bench_root)]) == 0
    assert [r["effort"] for r in run_data_json(bench_root, "voxel-horse")] == ["high"]


def test_import_needs_a_run_or_batch_directory(bench_root, tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    assert main(["import", str(tmp_path / "empty"), "--root", str(bench_root)]) == 1
    assert "no run.json" in capsys.readouterr().err


def test_a_failed_agent_run_is_published_without_output(bench_root, batch_dir):
    import json as _json

    path = batch_dir / "gpt-6-sol-low-20260926-001158"
    record = _json.loads((path / "run.json").read_text())
    record.update(state="failed", error="harness exited 1", output=None)
    (path / "run.json").write_text(_json.dumps(record))
    main(["import", str(path), "--root", str(bench_root)])
    [run] = run_data_json(bench_root, "voxel-horse")
    assert (run["state"], run["error"], run["output"], run["thumb"]) == ("failed", "harness exited 1", None, None)
    assert not list((bench_root / "docs/engines").iterdir())  # nothing was exported, so no engine is stored


def test_reimport_is_idempotent(bench_root, batch_dir):
    main(["import", str(batch_dir), "--root", str(bench_root)])
    runs_before = run_data_json(bench_root, "voxel-horse")
    main(["import", str(batch_dir), "--root", str(bench_root)])
    runs_after = run_data_json(bench_root, "voxel-horse")
    assert len(runs_after) == len(runs_before) == 2
    assert {r["id"] for r in runs_after} == {r["id"] for r in runs_before}
    # engine still deduped to one dir after re-import
    assert len(list((bench_root / "docs/engines").iterdir())) == 1
