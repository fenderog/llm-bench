"""bench run: level parsing, plan/confirmation, parallelism, timeout, failed runs still being
imported, metrics, and --resume. Uses a fake `pi` (tests/fixtures/fake_pi/pi) on PATH so no
real model, Godot or Playwright is needed; Godot export/verify are monkeypatched to fast fakes.
"""

import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from bench.cli import main
from bench.config import Config, RunRequest
from bench.harness import Pi, convert_claude_stream
from bench.runner import expand_levels, parse_duration, plan_runs
from bench.util import BenchError

FAKE_PI = Path(__file__).parent / "fixtures" / "fake_pi"


def plan_for(specs, effort=None):
    """plan_runs for a request with no bench.toml (no model sets)."""
    return plan_runs(Config.load(Path("/nonexistent")), RunRequest(prompt="p", model_specs=specs, effort=effort))


def fake_export_project(godot_bin, project_dir, out_dir, timeout=600):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(
        '<html><script src="index.js"></script><script>const GODOT_CONFIG = {"executable":"index",'
        '"mainPack":"index.pck","fileSizes":{"index.wasm":1}};</script></html>'
    )
    (out_dir / "index.js").write_bytes(b"js")
    (out_dir / "index.wasm").write_bytes(b"wasm")
    (out_dir / "index.pck").write_bytes(b"pck")
    (out_dir / "index.audio.worklet.js").write_bytes(b"worklet")
    (out_dir / "index.audio.position.worklet.js").write_bytes(b"pos-worklet")
    manifest = {"godot": "4.7.2.fake", "threads": False, "template": "web_nothreads_release.zip", "exportedAt": "2026-09-27T00:00:00Z"}
    (out_dir / "export-manifest.json").write_text(json.dumps(manifest) + "\n")
    return True, manifest, None


@pytest.fixture(autouse=True)
def fake_pi_on_path(monkeypatch):
    monkeypatch.setenv("PATH", f"{FAKE_PI}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.delenv("FAKE_PI_EXIT_CODE", raising=False)
    monkeypatch.delenv("FAKE_PI_HANG", raising=False)
    monkeypatch.delenv("FAKE_PI_ERROR_STOP", raising=False)
    for var in ("FAKE_CLAUDE_ERROR", "FAKE_CLAUDE_HANG", "FAKE_CLAUDE_ARGV"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def fake_build(monkeypatch):
    monkeypatch.setattr("bench.runner.build.export_project", fake_export_project)
    monkeypatch.setattr("bench.runner.build.verify_build", lambda out_dir, **kw: None)


@pytest.fixture
def run_root(bench_root, tmp_path):
    runs_dir = tmp_path / "bench-runs"
    (bench_root / "bench.toml").write_text(f'[run]\ndir = "{runs_dir}"\nparallel = 8\ntimeout = "30m"\n')
    return bench_root


def harness():
    return Pi("pi")


# --- level parsing (pure) ----------------------------------------------------------------------


def test_expand_levels_all_excludes_off():
    supported = ["off", "minimal", "low", "medium", "high", "xhigh", "max"]
    assert expand_levels("all", supported, "m") == ["minimal", "low", "medium", "high", "xhigh", "max"]


def test_expand_levels_range():
    supported = ["off", "minimal", "low", "medium", "high", "xhigh", "max"]
    assert expand_levels("low..high", supported, "m") == ["low", "medium", "high"]


def test_expand_levels_explicit_list():
    supported = ["low", "medium", "high"]
    assert expand_levels("low,high", supported, "m") == ["low", "high"]


def test_expand_levels_explicit_off():
    assert expand_levels("off", ["off", "low"], "m") == ["off"]


def test_expand_levels_unsupported_raises_naming_supported():
    with pytest.raises(BenchError, match="low.*not supported.*low, medium, high|not supported"):
        expand_levels("xhigh", ["low", "medium", "high"], "m")


def test_plan_runs_checks_before_anything_starts():
    plan = plan_for(["openai-codex/gpt-6-sol", "test/limited:low..high"], None)
    assert ("pi", "openai-codex/gpt-6-sol", "low") in plan
    assert ("pi", "test/limited", "high") in plan
    assert ("pi", "test/limited", "off") not in plan


def test_plan_runs_unsupported_level_errors_for_whole_batch():
    with pytest.raises(BenchError):
        plan_for(["test/limited:xhigh"], None)


def test_plan_runs_dedupes_same_model_merging_levels():
    plan = plan_for(["openai-codex/gpt-6-sol:low", "openai-codex/gpt-6-sol:high"], None)
    assert sorted(l for _, m, l in plan) == ["high", "low"]
    assert len(plan) == 2


def test_plan_runs_rejects_unknown_model_with_suggestions():
    with pytest.raises(BenchError, match=r"unknown model 'openai-codex/gpt-6-sool'.*gpt-6-sol"):
        plan_for(["openai-codex/gpt-6-sool:low"], None)
    with pytest.raises(BenchError, match="unknown model 'nope/nothing'"):
        plan_for(["nope/nothing"], None)


def test_plan_runs_handles_colons_inside_model_ids():
    model = "openrouter/openai/gpt-6-sol:batch"
    assert plan_for([model], None) == [("pi", model, l) for l in ["low", "medium", "high", "xhigh", "max"]]
    assert plan_for([model + ":high"], None) == [("pi", model, "high")]


def test_plan_runs_rejects_model_tag_collision(monkeypatch):
    # Two distinct model ids that both reduce to the tag "limited".
    monkeypatch.setattr(
        "bench.runner.model_tag",
        lambda model: "limited",
    )
    with pytest.raises(BenchError, match="limited"):
        plan_for(["test/limited:low", "openai-codex/gpt-6-sol:low"], None)


def test_parse_duration():
    assert parse_duration("30m") == 1800
    assert parse_duration("90s") == 90
    assert parse_duration("1h") == 3600
    with pytest.raises(BenchError):
        parse_duration("bad")


# --- plan / confirmation ------------------------------------------------------------------------


def test_dry_run_prints_plan_and_writes_nothing(run_root, capsys):
    rc = main(["run", "--dry-run", "a spinning cube", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "openai-codex/gpt-6-sol:low" in out
    assert not (run_root / "docs" / "data").exists() or not list((run_root / "docs" / "data").iterdir())


def test_missing_confirmation_on_nontty_is_an_error(run_root, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rc = main(["run", "a spinning cube", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 1


def test_yes_skips_confirmation_and_runs(run_root):
    rc = main(["run", "--yes", "a spinning cube", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    results = json.loads((run_root / "docs/data/a-spinning-cube/page.json").read_text())["runs"]
    assert len(results) == 1
    assert results[0]["effort"] == "low"
    assert results[0]["state"] == "complete"
    assert results[0]["harness"]["name"] == "pi"
    assert results[0]["game"]["entry"] == "game/index.html"
    page = json.loads((run_root / "docs/data/a-spinning-cube/page.json").read_text())
    assert page["prompt"] == "a spinning cube"
    assert page["final_prompt"].startswith("a spinning cube\n\nBuild this as a complete, playable Godot")


# --- failures --------------------------------------------------------------------------------


def test_failed_run_is_still_imported(run_root, monkeypatch):
    monkeypatch.setenv("FAKE_PI_EXIT_CODE", "1")
    rc = main(["run", "--yes", "broken run", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    results = json.loads((run_root / "docs/data/broken-run/page.json").read_text())["runs"]
    assert results[0]["state"] == "failed"
    assert results[0]["error"]


def test_error_stop_produces_failed_state(run_root, monkeypatch):
    monkeypatch.setenv("FAKE_PI_ERROR_STOP", "1")
    rc = main(["run", "--yes", "error stop run", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    results = json.loads((run_root / "docs/data/error-stop-run/page.json").read_text())["runs"]
    assert results[0]["state"] == "failed"
    assert "fake induced error" in results[0]["error"]


def test_timeout_kills_hung_agent(run_root, monkeypatch):
    monkeypatch.setenv("FAKE_PI_HANG", "1")
    rc = main(["run", "--yes", "--timeout", "1s", "hung run", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    results = json.loads((run_root / "docs/data/hung-run/page.json").read_text())["runs"]
    assert results[0]["state"] == "timeout"


def test_status_json_records_the_real_exit_code(run_root, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_PI_EXIT_CODE", "1")
    rc = main(["run", "--yes", "exit code run", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    batches = list((tmp_path / "bench-runs").glob("*-exit-code-run"))
    assert batches, "expected a batch dir for this run"
    status_files = list(batches[0].rglob("status.json"))
    assert status_files
    status = json.loads(status_files[0].read_text())
    assert status["exit_code"] == 1


def test_brief_is_not_written_into_the_agents_working_dir(run_root):
    rc = main(["run", "--yes", "brief location run", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    results = json.loads((run_root / "docs/data/brief-location-run/page.json").read_text())["runs"]
    files = results[0]["source"]["files"]
    assert "brief.md" not in files


def test_tool_durations_are_stored_and_the_event_stream_is_not_published(run_root):
    rc = main(["run", "--yes", "events run", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    run = json.loads((run_root / "docs/data/events-run/page.json").read_text())["runs"][0]
    run_dir = run_root / f"docs/data/events-run/runs/{run['id']}"
    assert "events" not in run["session"] and not (run_dir / "session/events.jsonl").exists()
    convo = json.loads((run_dir / "session/conversation.json").read_text())
    [result] = [e["message"] for e in convo if e.get("message", {}).get("role") == "toolResult"]
    assert result["durationMs"] == 2500  # from the assistant entry that called it to the result entry


def test_export_failure_keeps_state_complete_and_only_sets_error(run_root, monkeypatch):
    def failing_export(godot_bin, project_dir, out_dir, timeout=600):
        return False, None, "Godot export failed: boom"

    monkeypatch.setattr("bench.runner.build.export_project", failing_export)
    rc = main(["run", "--yes", "export fails run", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    results = json.loads((run_root / "docs/data/export-fails-run/page.json").read_text())["runs"]
    assert results[0]["state"] == "complete"
    assert "boom" in results[0]["error"]
    assert results[0]["game"] is None


# --- parallelism -------------------------------------------------------------------------------


def test_multiple_models_and_levels_all_run(run_root):
    rc = main([
        "run", "--yes", "-j", "4", "many runs",
        "-m", "openai-codex/gpt-6-sol:low,high",
        "-m", "openai-codex/gpt-6-luna:medium",
        "--root", str(run_root),
    ])
    assert rc == 0
    results = json.loads((run_root / "docs/data/many-runs/page.json").read_text())["runs"]
    assert len(results) == 3
    assert {r["effort"] for r in results} == {"low", "medium", "high"}
    assert {r["model"] for r in results} == {"openai-codex/gpt-6-sol", "openai-codex/gpt-6-luna"}


# --- resume --------------------------------------------------------------------------------------


def test_resume_does_not_rerun_finished_agents(run_root, monkeypatch, tmp_path):
    # Build a batch by hand: one run already "complete" (with its own session/project already
    # on disk), one still "queued". Resume must only (re)run the queued one.
    from bench.runner import write_batch_json

    runs_dir = tmp_path / "bench-runs"
    batch_dir = runs_dir / "2026-09-27-000000-resume-me"
    model_dir = batch_dir / "2026-09-27-000000-gpt6sol-resume-me"
    (model_dir / "low").mkdir(parents=True)
    (model_dir / "low" / "project.godot").write_text("config_version=5\n")
    (model_dir / "wasm" / "low").mkdir(parents=True)
    for name in ("index.html", "index.js", "index.wasm", "index.pck", "index.audio.worklet.js", "index.audio.position.worklet.js"):
        (model_dir / "wasm" / "low" / name).write_bytes(b"x")
    (model_dir / "wasm" / "low" / "index.html").write_text(
        '<html><script src="index.js"></script><script>const GODOT_CONFIG = {"executable":"index",'
        '"mainPack":"index.pck","fileSizes":{"index.wasm":1}};</script></html>'
    )
    (model_dir / "low" / "data.json").write_text(json.dumps({
        "model": "openai-codex/gpt-6-sol", "thinkingLevel": "low", "startedAt": 1, "endedAt": 2, "durationMs": 1,
        "costUsd": 0.01, "toolCalls": 1, "turns": 1, "tokens": {"input": 1, "output": 1, "total": 2, "reasoning": 0, "cacheRead": 0, "cacheWrite": 0},
        "state": "complete", "error": None,
    }))
    (model_dir / "data.json").write_text(json.dumps({
        "schema": "bench-run/1", "harness": {"name": "pi", "version": "0.1.0-fake"},
        "runs": {"low": json.loads((model_dir / "low" / "data.json").read_text())},
    }))

    runs = [
        {"model": "openai-codex/gpt-6-sol", "level": "low", "model_dir": model_dir, "state": "complete"},
        {"model": "openai-codex/gpt-6-sol", "level": "medium", "model_dir": model_dir, "state": "queued"},
    ]
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch = {
        "prompt": "resume me", "page": "resume-me", "title": "Resume me", "title_is_explicit": False,
        "harness": {"name": "pi", "version": "0.1.0-fake"}, "brief": "do the thing",
        "created": "2026-09-27T00:00:00Z", "runs": runs,
    }
    write_batch_json(batch_dir, batch)

    marker = tmp_path / "ran.txt"
    real_export = fake_export_project

    def counting_export(godot_bin, project_dir, out_dir, timeout=600):
        with open(marker, "a") as f:
            f.write(str(project_dir) + "\n")
        return real_export(godot_bin, project_dir, out_dir, timeout)

    monkeypatch.setattr("bench.runner.build.export_project", counting_export)

    rc = main(["run", "--resume", str(batch_dir), "--root", str(run_root)])
    assert rc == 0

    # The already-complete "low" level must not have been re-run (its hand-written project file
    # is untouched: the fake pi always overwrites project.godot with its own fixed content).
    assert (model_dir / "low" / "project.godot").read_text() == "config_version=5\n"
    # The queued "medium" level must have been run.
    assert (model_dir / "medium" / "data.json").is_file()
    medium_entry = json.loads((model_dir / "medium" / "data.json").read_text())
    assert medium_entry["state"] == "complete"

    results = json.loads((run_root / "docs/data/resume-me/page.json").read_text())["runs"]
    assert sorted(r["effort"] for r in results) == ["low", "medium"]


# --- Ctrl-C -----------------------------------------------------------------------------------


def test_ctrl_c_kills_the_agent_and_marks_it_queued_for_resume(run_root, monkeypatch):
    """A hung fake pi + a real SIGINT delivered to this process shortly after it starts (mirroring
    a real Ctrl-C) must: kill the fake pi's process group (so it stops "billing"), leave the run
    "queued" in batch.json (so --resume reruns it), and exit 130. This exercises the real
    interrupt path end to end rather than calling internal cleanup helpers directly.

    A real `os.kill(os.getpid(), SIGINT)` is used rather than `_thread.interrupt_main()`: the
    latter only sets a flag that the main thread notices between bytecode instructions, which
    never happens while it's blocked inside a C-level `Future.result()` lock wait, so it would
    never actually interrupt this test (and did, in fact, hang indefinitely when tried).
    """
    import signal
    import threading

    monkeypatch.setenv("FAKE_PI_HANG", "1")

    def interrupt_once_agent_started():  # Ctrl-C only after the fake pi is really running
        deadline = time.time() + 10
        while time.time() < deadline and not list(run_root.parent.glob("bench-runs/*-interrupt-me/*/low/fake_pi.pid")):
            time.sleep(0.05)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=interrupt_once_agent_started, daemon=True).start()

    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--yes", "interrupt me", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert exc_info.value.code == 130

    assert not (run_root / "docs" / "data").exists() or not list((run_root / "docs" / "data").iterdir())

    from bench.config import Config

    cfg = Config.load(run_root)
    batches = list(cfg.run.dir.glob("*-interrupt-me"))
    assert len(batches) == 1
    batch = json.loads((batches[0] / "batch.json").read_text())
    assert batch["runs"][0]["state"] == "queued"

    # The fake pi's process (and its process group) must actually be gone, not just abandoned.
    pid = int(next(batches[0].glob("*/low/fake_pi.pid")).read_text())
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail(f"fake pi (pid {pid}) still alive after Ctrl-C")


# --- metrics against the real voxel-horse session (when present) --------------------------------

REAL_RUN = Path.home() / "dev/effort-runs/2026-09-26-001158-gpt6sol-voxel-horse"


@pytest.mark.skipif(not REAL_RUN.is_dir(), reason="real effort run not on this machine")
def test_metrics_match_real_session_numbers():
    from bench.harness import parse_session

    expected = {
        "low": (10692, 3553, 14245, 62, 38016, 0.0645172, 10, 11),
        "medium": (11271, 4906, 16177, 985, 41216, 0.079845, 9, 9),
        "high": (25280, 7452, 32732, 3073, 105984, 0.1462768, 16, 17),
    }
    for level, (inp, out, total, reasoning, cache_read, cost, tool_calls, turns) in expected.items():
        m = parse_session(REAL_RUN / level / "session.jsonl")
        assert m["tokens"]["input"] == inp
        assert m["tokens"]["output"] == out
        assert m["tokens"]["total"] == total
        assert m["tokens"]["reasoning"] == reasoning
        assert m["tokens"]["cacheRead"] == cache_read
        assert round(m["cost_usd"], 4) == round(cost, 4)
        assert m["tool_calls"] == tool_calls
        assert m["turns"] == turns


# --- web kind ------------------------------------------------------------------------------------
needs_esbuild = pytest.mark.skipif(shutil.which("esbuild") is None, reason="esbuild not on PATH")


@needs_esbuild
def test_web_run_publishes_one_packaged_page(run_root):
    rc = main(["run", "--yes", "--kind", "web", "a spinning horse", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    assert json.loads((run_root / "docs/data/a-spinning-horse/page.json").read_text())["kind"] == "web"
    [run] = json.loads((run_root / "docs/data/a-spinning-horse/page.json").read_text())["runs"]
    assert run["kind"] == "web" and run["state"] == "complete" and run["error"] is None
    assert run["game"]["kind"] == "web" and run["game"]["entry"] == "game/index.html" and run["game"]["esbuild"]
    run_dir = run_root / "docs/data/a-spinning-horse/runs" / run["id"]
    assert [p.name for p in (run_dir / "game").iterdir()] == ["index.html"]  # one file
    html = (run_dir / "game/index.html").read_text()
    assert "spinning " in html and "#123" in html  # the npm package and the stylesheet are inlined
    assert 'src="main.js"' not in html and "fakepkg" not in html and "style.css" not in html
    assert str(Path.home()) not in html  # cleaned like source
    assert run["source"]["files"] == ["index.html", "main.js", "package.json", "style.css"]  # no node_modules/


@needs_esbuild
def test_web_run_that_fails_to_package_keeps_state_and_sets_error(run_root, monkeypatch):
    monkeypatch.setenv("FAKE_PI_BAD_WEB", "1")
    rc = main(["run", "--yes", "--kind", "web", "broken page", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    [run] = json.loads((run_root / "docs/data/broken-page/page.json").read_text())["runs"]
    assert run["state"] == "complete" and run["game"] is None
    assert run["error"].startswith("packaging failed: esbuild:") and "missing.js" in run["error"]
    assert "main.js" in run["source"]["files"]  # the source is still published


def test_web_run_needs_esbuild(run_root, monkeypatch):
    monkeypatch.setattr("bench.runner.shutil.which", lambda name: None if name == "esbuild" else "/bin/" + name)
    with pytest.raises(BenchError, match="needs esbuild"):
        from bench.runner import cmd_run

        cmd_run(Config.load(run_root), RunRequest(prompt="x", model_specs=["openai-codex/gpt-6-sol:low"], kind="web"), dry_run=True)


# --- media kind ----------------------------------------------------------------------------------

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="needs ffmpeg")


@needs_ffmpeg
def test_media_run_publishes_output_files(run_root):
    rc = main(["run", "--yes", "--kind", "media", "a red circle", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    page = json.loads((run_root / "docs/data/a-red-circle/page.json").read_text())
    assert page["kind"] == "media"
    assert "./output/" in page["final_prompt"] and "Tools available on this machine: " in page["final_prompt"]
    [run] = json.loads((run_root / "docs/data/a-red-circle/page.json").read_text())["runs"]
    assert run["kind"] == "media" and run["game"] is None
    assert run["verified"] is True and run["error"] is None
    by_path = {m["path"]: m for m in run["media"]}
    assert set(by_path) == {"media/clip.mp4", "media/dot.png", "media/drawing.svg"}
    assert by_path["media/drawing.svg"]["width"] == 120
    assert by_path["media/clip.mp4"]["poster"] == "media/clip.poster.jpg"
    assert run["thumb"] == "media/clip.poster.jpg"  # first item, sorted by name
    run_dir = run_root / "docs/data/a-red-circle/runs" / run["id"]
    for rel in [*by_path, "media/clip.poster.jpg"]:
        assert (run_dir / rel).is_file()
    assert str(Path.home()) not in (run_dir / "media/drawing.svg").read_text()  # SVGs are cleaned
    # Source is the text code only: no ./output/, no leftover binary frames.
    assert run["source"]["files"] == ["make.py"]
    pages = json.loads((run_root / "docs/data/pages.json").read_text())
    assert pages[0]["kind"] == "media"
    assert pages[0]["thumb"] == f"data/a-red-circle/runs/{run['id']}/media/clip.poster.jpg"


@needs_ffmpeg
def test_media_run_with_bad_output_keeps_state_and_sets_error(run_root, monkeypatch):
    monkeypatch.setenv("FAKE_PI_BAD_OUTPUT", "1")
    rc = main(["run", "--yes", "--kind", "media", "bad media", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    [run] = json.loads((run_root / "docs/data/bad-media/page.json").read_text())["runs"]
    assert run["state"] == "complete" and run["verified"] is False
    assert "notes.txt: unsupported file type" in run["error"]
    assert len(run["media"]) == 3  # the good files are still published


def test_kind_must_match_the_existing_page(run_root):
    assert main(["run", "--yes", "mixed page", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)]) == 0
    rc = main(["run", "--yes", "--kind", "media", "mixed page", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 1


# --- model sets ------------------------------------------------------------------------------------


def write_sets(run_root, body):
    cfg = run_root / "bench.toml"
    cfg.write_text(cfg.read_text() + "\n[sets]\n" + body)


def test_set_from_bench_toml_expands_like_m_flags(run_root, capsys):
    write_sets(run_root, 'duo = ["openai-codex/gpt-6-sol:low,high", "test/limited"]\n')
    rc = main(["run", "--dry-run", "cube", "--set", "duo", "-e", "medium", "--root", str(run_root)])
    assert rc == 0
    out = capsys.readouterr().out
    for spec in ("openai-codex/gpt-6-sol:low", "openai-codex/gpt-6-sol:high", "test/limited:medium"):
        assert spec in out
    assert "test/limited:low" not in out  # -e applies to set entries without levels


def test_set_from_a_file_combines_with_m(run_root, tmp_path, capsys):
    f = tmp_path / "mine.txt"
    f.write_text("# my models\nopenai-codex/gpt-6-luna:minimal   # cheapest\n\ntest/limited:high\n")
    rc = main(["run", "--dry-run", "cube", "-s", str(f), "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "1. openai-codex/gpt-6-luna:minimal" in out and "test/limited:high" in out and "openai-codex/gpt-6-sol:low" in out


def test_unknown_set_lists_the_defined_ones(run_root, capsys):
    write_sets(run_root, 'duo = ["test/limited"]\n')
    rc = main(["run", "--dry-run", "cube", "--set", "nope", "--root", str(run_root)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown model set 'nope'" in err and "(duo)" in err


def test_set_entries_are_checked_like_m_flags(run_root, capsys):
    write_sets(run_root, 'bad = ["test/limited:xhigh"]\n')
    assert main(["run", "--dry-run", "cube", "--set", "bad", "--root", str(run_root)]) == 1
    err = capsys.readouterr().err
    assert "xhigh" in err and "not supported" in err


def test_malformed_set_is_an_error(run_root, capsys):
    write_sets(run_root, 'notalist = "test/limited"\n')
    assert main(["run", "--dry-run", "cube", "--set", "notalist", "--root", str(run_root)]) == 1
    assert "[sets].notalist must be a list" in capsys.readouterr().err


# --- adding runs to an existing page --------------------------------------------------------------


@needs_ffmpeg
def test_page_alone_reuses_the_pages_prompt_and_kind(run_root):
    assert main(["run", "--yes", "--kind", "media", "a red circle", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)]) == 0
    rc = main(["run", "--yes", "--page", "a-red-circle", "-m", "openai-codex/gpt-6-luna:minimal", "--root", str(run_root)])
    assert rc == 0
    results = json.loads((run_root / "docs/data/a-red-circle/page.json").read_text())["runs"]
    assert {(r["model"], r["effort"], r["kind"]) for r in results} == {
        ("openai-codex/gpt-6-sol", "low", "media"), ("openai-codex/gpt-6-luna", "minimal", "media")}
    assert json.loads((run_root / "docs/data/a-red-circle/page.json").read_text())["prompt"] == "a red circle"


def test_a_different_prompt_for_an_existing_page_is_refused(run_root, capsys):
    assert main(["run", "--yes", "a spinning cube", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)]) == 0
    rc = main(["run", "--yes", "--page", "a-spinning-cube", "a spinning red cube", "-m", "openai-codex/gpt-6-sol:high", "--root", str(run_root)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "different prompt" in err and "a spinning cube" in err and "--change-prompt" in err
    assert len(json.loads((run_root / "docs/data/a-spinning-cube/page.json").read_text())["runs"]) == 1

    # the same prompt is fine, and --change-prompt replaces it on purpose
    assert main(["run", "--yes", "--page", "a-spinning-cube", "a spinning cube", "-m", "openai-codex/gpt-6-sol:medium", "--root", str(run_root)]) == 0
    rc = main(["run", "--yes", "--change-prompt", "--page", "a-spinning-cube", "a spinning red cube", "-m", "openai-codex/gpt-6-sol:high", "--root", str(run_root)])
    assert rc == 0
    assert json.loads((run_root / "docs/data/a-spinning-cube/page.json").read_text())["prompt"] == "a spinning red cube"
    assert len(json.loads((run_root / "docs/data/a-spinning-cube/page.json").read_text())["runs"]) == 3


def test_page_without_prompt_must_exist(run_root, capsys):
    assert main(["run", "--yes", "--page", "nope", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)]) == 1
    assert "reuse its prompt" in capsys.readouterr().err



# --- Claude Code harness ---------------------------------------------------------------------------


def test_claude_code_prefix_resolves_aliases_and_levels():
    assert plan_for(["claude-code:opus:high"], None) == [("claude-code", "claude-opus-5-5", "high")]
    assert plan_for(["claude-code:sonnet:high"], None) == [("claude-code", "claude-sonnet-5-5", "high")]
    assert [l for _, _, l in plan_for(["claude-code:claude-sonnet-5"], None)] == ["low", "medium", "high", "xhigh", "max"]
    with pytest.raises(BenchError, match="minimal.*not supported"):
        plan_for(["claude-code:claude-opus-5-5:minimal"], None)
    with pytest.raises(BenchError, match="unknown model 'claude-opus-9'.*claude-opus-5-5"):
        plan_for(["claude-code:claude-opus-9:high"], None)


def _claude_image_result(data):
    events = [
        {"type": "assistant", "message": {"id": "m1", "content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "shot.png"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": [
            {"type": "text", "text": "read it"}, {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}]}]}},
    ]
    [result] = [e["message"] for e in convert_claude_stream(events, "brief", "low") if e.get("message", {}).get("role") == "toolResult"]
    return result["content"]


def test_claude_image_tool_results_keep_only_their_size_when_not_an_image():
    text, image = _claude_image_result("A" * 4096)  # decodes, but isn't an image: no thumbnail, never the raw data
    assert text == {"type": "text", "text": "read it"}
    assert image == {"type": "image", "mimeType": "image/jpeg", "sourceMimeType": "image/png", "bytes": 3072}


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_claude_image_tool_results_become_small_jpeg_thumbnails():
    png = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720", "-frames:v", "1",
                          "-f", "image2pipe", "-c:v", "png", "pipe:1"], capture_output=True, check=True).stdout
    _, image = _claude_image_result(base64.b64encode(png).decode())
    thumb = base64.b64decode(image["data"])
    assert image["bytes"] == len(png) and image["sourceMimeType"] == "image/png"
    assert thumb.startswith(b"\xff\xd8") and len(thumb) < 40_000  # a JPEG, much smaller than the original


def test_mixed_harness_batch_records_each_runs_harness_and_session(run_root, monkeypatch, tmp_path):
    argv_file = tmp_path / "claude-argv.json"
    monkeypatch.setenv("FAKE_CLAUDE_ARGV", str(argv_file))
    monkeypatch.setenv("CLAUDECODE", "1")  # as when bench itself runs inside Claude Code
    rc = main(["run", "--yes", "mixed harness", "-m", "claude-code:claude-opus-5-5:high",
               "-m", "anthropic/claude-opus-5-5:high", "--root", str(run_root)])
    assert rc == 0
    results = {r["harness"]["name"]: r for r in json.loads((run_root / "docs/data/mixed-harness/page.json").read_text())["runs"]}
    assert set(results) == {"pi", "claude-code"}
    cc, pi = results["claude-code"], results["pi"]
    assert cc["model"] == pi["model"] == "anthropic/claude-opus-5-5"
    assert cc["id"].startswith("claude-opus-5-5-cc-high-") and pi["id"].startswith("claude-opus-5-5-high-")
    assert cc["harness"]["version"] == "9.9.9-fake"
    assert cc["state"] == "complete"
    m = cc["metrics"]
    assert (m["turns"], m["tool_calls"], m["cost_usd"]) == (3, 2, 0.0123)
    # tokens from the final result (the stream's per-message usage undercounts output)
    assert (m["tokens_input"], m["tokens_output"], m["tokens_total"], m["tokens_cache_read"]) == (16, 180, 196, 3500)
    assert m["tokens_reasoning"] == 40

    # One direct agent, no personal setup, nothing saved to the user's history, not "nested".
    sent = json.loads(argv_file.read_text())
    for flag in ("--safe-mode", "--no-session-persistence", "--tools=Bash,Read,Write,Edit,Glob,Grep",
                 "--disallowed-tools=Agent,Task", "--disable-slash-commands", "--verbose"):
        assert flag in sent["argv"]
    assert sent["argv"][sent["argv"].index("--effort") + 1] == "high"
    assert sent["argv"][sent["argv"].index("--model") + 1] == "claude-opus-5-5"
    assert sent["env_has_claudecode"] is False

    run_dir = run_root / "docs/data/mixed-harness/runs" / cc["id"]
    assert "events" not in cc["session"] and not (run_dir / "session/events.jsonl").exists()
    convo = json.loads((run_dir / "session/conversation.json").read_text())
    assert [e["message"]["durationMs"] for e in convo if e.get("message", {}).get("role") == "toolResult"] == [5000, 5000]  # tool_use event -> tool_result event
    text = json.dumps(convo)
    assert "signature" not in text and "sess-fake" not in text
    msgs = [e["message"] for e in convo if e["type"] == "message"]
    assert msgs[0]["role"] == "user" and msgs[0]["content"][0]["text"].startswith("mixed harness")
    calls = [b for mm in msgs if mm["role"] == "assistant" for b in mm["content"] if b["type"] == "toolCall"]
    assert [(c["name"], c["arguments"].get("path")) for c in calls] == [("write", "project.godot"), ("bash", None)]
    results_by_call = {mm["toolCallId"]: mm for mm in msgs if mm["role"] == "toolResult"}
    assert results_by_call[calls[1]["id"]]["isError"] is True
    assert [mm["content"][0]["type"] for mm in msgs if mm["role"] == "assistant"] == ["thinking", "toolCall", "text"]
    # timestamps come from the stream: a merged message keeps its first event's, the brief gets the first one
    assert [e["timestamp"][-8:-5] for e in convo if e["type"] == "message"] == [":00", ":00", ":10", ":15", ":20", ":25"]
    page =json.loads((run_root / "docs/data/mixed-harness/page.json").read_text())
    assert page["final_prompt"].startswith("mixed harness\n\nBuild this")


def test_claude_code_error_result_is_a_failed_run(run_root, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_ERROR", "1")
    assert main(["run", "--yes", "cc error", "-m", "claude-code:haiku:low", "--root", str(run_root)]) == 0
    [run] = json.loads((run_root / "docs/data/cc-error/page.json").read_text())["runs"]
    assert run["state"] == "failed" and "overloaded" in run["error"]


def test_claude_code_timeout(run_root, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_HANG", "1")
    assert main(["run", "--yes", "--timeout", "1s", "cc hang", "-m", "claude-code:haiku:low", "--root", str(run_root)]) == 0
    [run] = json.loads((run_root / "docs/data/cc-hang/page.json").read_text())["runs"]
    assert run["state"] == "timeout"


def test_claude_code_in_a_model_set_and_models_listing(run_root, capsys):
    write_sets(run_root, 'mix = ["claude-code:sonnet:low", "openai-codex/gpt-6-sol:low"]\n')
    assert main(["run", "--dry-run", "cube", "--set", "mix", "--root", str(run_root)]) == 0
    out = capsys.readouterr().out
    assert "claude-code:claude-sonnet-5-5:low" in out and "openai-codex/gpt-6-sol:low" in out
    assert "harness: claude-code 9.9.9-fake, pi 0.1.0-fake" in out
    assert main(["models", "--harness", "claude-code", "opus"]) == 0
    assert "claude-opus-5-5: low, medium, high, xhigh, max" in capsys.readouterr().out


def test_every_long_option_has_a_short_form():
    import argparse

    from bench.cli import build_parser

    sub = next(a for a in build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    for name, parser in sub.choices.items():
        for action in parser._actions:
            longs = [o for o in action.option_strings if o.startswith("--")]
            shorts = [o for o in action.option_strings if not o.startswith("--")]
            assert not longs or shorts, f"bench {name} {longs[0]} has no short form"
    args = build_parser().parse_args(["run", "-n", "-y", "-k", "web", "-p", "pg", "-t", "T", "-T", "5m", "-b", "b.md", "-c", "-P", "-C", "/tmp", "x"])
    assert (args.dry_run, args.yes, args.kind, args.page, args.title, args.timeout, str(args.brief), args.change_prompt, args.publish) == \
        (True, True, "web", "pg", "T", "5m", "b.md", True, True)


def test_bad_run_inputs_fail_before_a_batch_dir_exists(run_root, tmp_path, capsys):
    runs_dir = Config.load(run_root).run.dir
    assert main(["run", "--yes", "--timeout", "banana", "x", "-m", "openai-codex/gpt-6-sol:low", "--root", str(run_root)]) != 0
    assert "bad duration" in capsys.readouterr().err
    empty_set = tmp_path / "empty.txt"
    empty_set.write_text("# nothing here\n")
    assert main(["run", "--yes", "x", "--set", str(empty_set), "--root", str(run_root)]) != 0
    assert "at least one -m" in capsys.readouterr().err
    assert not runs_dir.exists() or not list(runs_dir.iterdir())
