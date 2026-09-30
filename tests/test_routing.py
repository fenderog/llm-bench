"""OpenRouter upstream routing (`MODEL@slug`): plan parsing, argv/env, route recording, resume."""

import json
import os
from pathlib import Path

import pytest

from bench.cli import main
from bench.harness import split_model_route
from bench.runner import plan_runs, split_route
from bench.util import BenchError, make_run_id

FAKE_PI = Path(__file__).parent / "fixtures" / "fake_pi"


@pytest.fixture(autouse=True)
def fake_pi_on_path(monkeypatch):
    monkeypatch.setenv("PATH", f"{FAKE_PI}{os.pathsep}{os.environ['PATH']}")
    for var in ("FAKE_PI_EXIT_CODE", "FAKE_PI_HANG", "FAKE_PI_ERROR_STOP",
                "FAKE_CLAUDE_ERROR", "FAKE_CLAUDE_HANG", "FAKE_CLAUDE_ARGV", "FAKE_PI_ARGV"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def fake_build(monkeypatch):
    def fake_export_project(godot_bin, project_dir, out_dir, timeout=600):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(
            '<html><script src="index.js"></script><script>const GODOT_CONFIG = {"executable":"index",'
            '"mainPack":"index.pck","fileSizes":{"index.wasm":1}};</script></html>'
        )
        for name in ("index.js", "index.wasm", "index.pck", "index.audio.worklet.js",
                     "index.audio.position.worklet.js"):
            (out_dir / name).write_bytes(b"x")
        manifest = {"godot": "4.7.2.fake", "threads": False,
                    "template": "web_nothreads_release.zip", "exportedAt": "2026-09-27T00:00:00Z"}
        (out_dir / "export-manifest.json").write_text(json.dumps(manifest) + "\n")
        return True, manifest, None

    monkeypatch.setattr("bench.runner.build.export_project", fake_export_project)
    monkeypatch.setattr("bench.runner.build.verify_build", lambda out_dir, **kw: None)


@pytest.fixture
def run_root(bench_root, tmp_path):
    runs_dir = tmp_path / "bench-runs"
    (bench_root / "bench.toml").write_text(f'[run]\ndir = "{runs_dir}"\nparallel = 8\ntimeout = "30m"\n')
    return bench_root


# --- plan parsing (pure) ---


def test_split_route_no_at():
    assert split_route("openrouter/x/y:low") == ("openrouter/x/y:low", None)


def test_split_route_single_slug():
    assert split_route("openrouter/x/y@deepinfra:low") == ("openrouter/x/y:low", ["deepinfra"])


def test_split_route_multiple_slugs_and_no_levels():
    assert split_route("openrouter/x/y@deepinfra,fireworks") == ("openrouter/x/y", ["deepinfra", "fireworks"])


def test_split_route_bad_slugs():
    for bad in ("openrouter/x/y@", "openrouter/x/y@:low", "openrouter/x/y@a b:low", "openrouter/x/y@a!:low"):
        with pytest.raises(BenchError):
            split_route(bad)


def test_split_model_route():
    assert split_model_route("openrouter/x/y@a,b") == ("openrouter/x/y", ["a", "b"])
    assert split_model_route("openrouter/x/y") == ("openrouter/x/y", None)


def test_plan_routed_model_arg_and_level():
    assert plan_runs(["openrouter/test/model@deepinfra:low"], None) == [
        ("pi", "openrouter/test/model@deepinfra", "low")]


def test_plan_two_upstreams_are_separate_models_with_merged_levels():
    plan = plan_runs(
        ["openrouter/test/model@deepinfra:low", "openrouter/test/model@fireworks:low",
         "openrouter/test/model@deepinfra:high"], None)
    assert sorted(plan) == [
        ("pi", "openrouter/test/model@deepinfra", "high"),
        ("pi", "openrouter/test/model@deepinfra", "low"),
        ("pi", "openrouter/test/model@fireworks", "low"),
    ]


def test_plan_route_on_non_openrouter_is_an_error():
    with pytest.raises(BenchError, match="@UPSTREAM only works for pi openrouter/"):
        plan_runs(["openai-codex/gpt-6-sol@deepinfra:low"], None)


def test_plan_route_on_claude_code_is_an_error():
    with pytest.raises(BenchError, match="@UPSTREAM only works for pi openrouter/"):
        plan_runs(["claude-code:opus@deepinfra:low"], None)


def test_plan_route_levels_checked_against_base_model():
    with pytest.raises(BenchError, match="not supported"):
        plan_runs(["openrouter/test/model@deepinfra:bogus"], None)


def test_plan_routed_and_unrouted_same_model_share_no_levels():
    plan = plan_runs(["openrouter/test/model:low", "openrouter/test/model@deepinfra:high"], None)
    assert sorted(plan) == [
        ("pi", "openrouter/test/model", "low"),
        ("pi", "openrouter/test/model@deepinfra", "high"),
    ]


def test_set_entry_with_route(tmp_path, run_root, capsys):
    (run_root / "bench.toml").write_text(
        (run_root / "bench.toml").read_text()
        + '\n[sets]\nrouted = ["openrouter/test/model@deepinfra:low"]\n')
    assert main(["run", "--dry-run", "cube", "--set", "routed", "--root", str(run_root)]) == 0
    assert "openrouter/test/model@deepinfra:low" in capsys.readouterr().out


def test_make_run_id_sanitizes_at():
    run_id = make_run_id("openrouter/deepseek/deepseek-v4.1-flash@deepinfra", "low",
                         "2026-10-01-101500-gpt6sol-x")
    assert run_id == "deepseek-v4.1-flash-via-deepinfra-low-20261001-101500"


def test_routing_extension_exists():
    from bench.harness import ROUTING_EXTENSION

    assert ROUTING_EXTENSION.name == "openrouter_routing.ts"
    assert ROUTING_EXTENSION.is_file()


# --- end to end with the fake pi ---


def test_routed_run_pins_upstream_and_records_route(run_root, monkeypatch, tmp_path):
    argv_file = tmp_path / "pi-argv.json"
    monkeypatch.setenv("FAKE_PI_ARGV", str(argv_file))
    rc = main(["run", "--yes", "routed run", "-m", "openrouter/test/model@deepinfra:low",
               "--root", str(run_root)])
    assert rc == 0
    sent = json.loads(argv_file.read_text())
    model_flag = sent["argv"][sent["argv"].index("--model") + 1]
    assert model_flag == "openrouter/test/model:low"
    assert "@" not in model_flag
    assert "-e" in sent["argv"]
    ext = sent["argv"][sent["argv"].index("-e") + 1]
    assert ext.endswith("openrouter_routing.ts")
    assert json.loads(sent["routing"]) == {"only": ["deepinfra"], "allow_fallbacks": False}

    [run] = json.loads((run_root / "docs/data/routed-run/results.json").read_text())
    assert run["model"] == "openrouter/test/model@deepinfra"
    assert run["route"] == {"requested": {"only": ["deepinfra"], "allow_fallbacks": False},
                            "served": ["FakeUpstream"]}
    assert "-via-deepinfra-" in run["id"]
    run_dir = run_root / "docs/data/routed-run/runs" / run["id"]
    assert (run_dir / "run.json").exists()
    assert json.loads((run_dir / "run.json").read_text())["route"] == run["route"]


def test_unrouted_run_passes_no_extension_or_env(run_root, monkeypatch, tmp_path):
    argv_file = tmp_path / "pi-argv.json"
    monkeypatch.setenv("FAKE_PI_ARGV", str(argv_file))
    rc = main(["run", "--yes", "plain run", "-m", "openai-codex/gpt-6-sol:low",
               "--root", str(run_root)])
    assert rc == 0
    sent = json.loads(argv_file.read_text())
    assert "-e" not in sent["argv"]
    assert sent["routing"] is None
    [run] = json.loads((run_root / "docs/data/plain-run/results.json").read_text())
    assert run.get("route") is None


def test_resume_reruns_routed_with_same_argv_env(run_root, monkeypatch, tmp_path):
    from bench.runner import load_run_config

    argv_file = tmp_path / "pi-argv.json"
    monkeypatch.setenv("FAKE_PI_ARGV", str(argv_file))
    assert main(["run", "--yes", "resume routed", "-m", "openrouter/test/model@deepinfra:low",
                 "--root", str(run_root)]) == 0
    first = json.loads(argv_file.read_text())

    # interrupt-style: mark the run queued again, then resume
    cfg = load_run_config(run_root)
    [batch_dir] = list(cfg["dir"].glob("*-resume-routed"))
    batch = json.loads((batch_dir / "batch.json").read_text())
    assert batch["runs"][0]["model_arg"] == "openrouter/test/model@deepinfra"
    batch["runs"][0]["state"] = "queued"
    (batch_dir / "batch.json").write_text(json.dumps(batch))

    argv_file.unlink()
    assert main(["run", "--resume", str(batch_dir), "--root", str(run_root)]) == 0
    second = json.loads(argv_file.read_text())
    assert second["argv"] == first["argv"]
    assert second["routing"] == first["routing"]
    [run] = json.loads((run_root / "docs/data/resume-routed/results.json").read_text())
    assert run["model"] == "openrouter/test/model@deepinfra"
    assert run["route"]["served"] == ["FakeUpstream"]
