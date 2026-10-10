"""OpenRouter upstream routing (`MODEL@slug`): plan parsing, argv/env, route recording, resume."""

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from art_crit.cli import main
from art_crit.config import Config, RunRequest
from art_crit.harness import split_model_route, split_route
from art_crit.runner import plan_runs
from art_crit.util import CritError, make_run_id

STARTED = datetime(2026, 10, 1, 10, 15, 0)
FAKE_PI = Path(__file__).parent / "fixtures" / "fake_pi"


def plan_for(specs, effort=None):
    """plan_runs for a request with no art-crit.toml (no model sets)."""
    return plan_runs(Config.load(Path("/nonexistent")), RunRequest(prompt="p", model_specs=specs, effort=effort))


@pytest.fixture(autouse=True)
def fake_pi_on_path(monkeypatch):
    monkeypatch.setenv("PATH", f"{FAKE_PI}{os.pathsep}{os.environ['PATH']}")
    for var in ("FAKE_PI_EXIT_CODE", "FAKE_PI_HANG", "FAKE_PI_ERROR_STOP",
                "FAKE_CLAUDE_ERROR", "FAKE_CLAUDE_HANG", "FAKE_CLAUDE_ARGV", "FAKE_PI_ARGV", "FAKE_PI_SERVED"):
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

    monkeypatch.setattr("art_crit.kinds.godot.export_project", fake_export_project)
    monkeypatch.setattr("art_crit.kinds.godot.Godot.verify", lambda self, out_dir: None)


@pytest.fixture
def run_root(bench_root, tmp_path):
    runs_dir = tmp_path / "art-crit-runs"
    (bench_root / "art-crit.toml").write_text(f'[run]\ndir = "{runs_dir}"\nparallel = 8\ntimeout = "30m"\n')
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
        with pytest.raises(CritError):
            split_route(bad)


def test_split_model_route():
    assert split_model_route("openrouter/x/y@a,b") == ("openrouter/x/y", ["a", "b"])
    assert split_model_route("openrouter/x/y") == ("openrouter/x/y", None)


def test_plan_routed_model_arg_and_level():
    assert plan_for(["openrouter/test/model@deepinfra:low"], None) == [
        ("pi", "openrouter/test/model@deepinfra", "low")]


def test_plan_two_upstreams_are_separate_models_with_merged_levels():
    plan = plan_for(
        ["openrouter/test/model@deepinfra:low", "openrouter/test/model@fireworks:low",
         "openrouter/test/model@deepinfra:high"], None)
    assert sorted(plan) == [
        ("pi", "openrouter/test/model@deepinfra", "high"),
        ("pi", "openrouter/test/model@deepinfra", "low"),
        ("pi", "openrouter/test/model@fireworks", "low"),
    ]


def test_plan_route_on_non_openrouter_is_an_error():
    with pytest.raises(CritError, match="@UPSTREAM only works for pi openrouter/"):
        plan_for(["openai-codex/gpt-6-sol@deepinfra:low"], None)


def test_plan_route_on_claude_code_is_an_error():
    with pytest.raises(CritError, match="@UPSTREAM only works for pi openrouter/"):
        plan_for(["claude-code:opus@deepinfra:low"], None)


def test_plan_route_levels_checked_against_base_model():
    with pytest.raises(CritError, match="not supported"):
        plan_for(["openrouter/test/model@deepinfra:bogus"], None)


def test_plan_routed_and_unrouted_same_model_share_no_levels():
    plan = plan_for(["openrouter/test/model:low", "openrouter/test/model@deepinfra:high"], None)
    assert sorted(plan) == [
        ("pi", "openrouter/test/model", "low"),
        ("pi", "openrouter/test/model@deepinfra", "high"),
    ]


def test_set_entry_with_route(tmp_path, run_root, capsys):
    (run_root / "art-crit.toml").write_text(
        (run_root / "art-crit.toml").read_text()
        + '\n[sets]\nrouted = ["openrouter/test/model@deepinfra:low"]\n')
    assert main(["run", "--dry-run", "cube", "--set", "routed", "--root", str(run_root)]) == 0
    assert "openrouter/test/model@deepinfra:low" in capsys.readouterr().out


def test_make_run_id_sanitizes_at():
    run_id = make_run_id("openrouter/deepseek/deepseek-v4.1-flash@deepinfra", "low",
                         STARTED)
    assert run_id == "deepseek-v4.1-flash-via-deepinfra-low-20261001-101500"


def test_route_with_a_slash_keeps_the_model_name():
    """Real OpenRouter slugs carry a variant after "/" ("deepinfra/fp8"); it must not be taken
    for the model name in run ids or model dir tags."""
    assert split_route("openrouter/x/y@deepinfra/fp8,atlas-cloud/fp8:low") == ("openrouter/x/y:low", ["deepinfra/fp8", "atlas-cloud/fp8"])
    model = "openrouter/deepseek/deepseek-v4.1-flash@deepinfra/fp8"
    assert make_run_id(model, "low", STARTED) == "deepseek-v4.1-flash-via-deepinfra-fp8-low-20261001-101500"
    other = make_run_id("openrouter/deepseek/deepseek-v4.1-flash@deepinfra/turbo", "low", STARTED)
    assert other != make_run_id(model, "low", STARTED) and other.startswith("deepseek-v4.1-flash-via-deepinfra-turbo-")


def test_upstream_key_matches_slugs_to_display_names():
    from art_crit.harness import upstream_key

    # (slug, what OpenRouter reports) pairs seen on real endpoints
    for slug, name in [("deepinfra/fp8", "DeepInfra"), ("atlas-cloud/fp8", "AtlasCloud"), ("io-net/fp8", "Io Net"),
                       ("sail-research/fp4", "Sail Research"), ("open-inference/fp4", "OpenInference"), ("fireworks/us", "Fireworks")]:
        assert upstream_key(slug) == upstream_key(name)
    assert upstream_key("deepinfra") != upstream_key("Fireworks")


def test_routing_extension_exists():
    from art_crit.harness import ROUTING_EXTENSION

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

    [run] = json.loads((run_root / "docs/data/routed-run/page.json").read_text())["runs"]
    assert run["model"] == "openrouter/test/model@deepinfra"
    assert run["route"] == {"requested": {"only": ["deepinfra"], "allow_fallbacks": False},
                            "served": ["Deepinfra"], "cost_usd": 0.0042, "pi_cost_usd": 0.0025}
    assert run["metrics"]["cost_usd"] == 0.0042  # what OpenRouter charged, not pi's catalog estimate
    assert run["error"] is None  # "Deepinfra" is the requested upstream
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
    [run] = json.loads((run_root / "docs/data/plain-run/page.json").read_text())["runs"]
    assert run.get("route") is None


def test_resume_reruns_routed_with_same_argv_env(run_root, monkeypatch, tmp_path):
    from art_crit.config import Config

    argv_file = tmp_path / "pi-argv.json"
    monkeypatch.setenv("FAKE_PI_ARGV", str(argv_file))
    assert main(["run", "--yes", "resume routed", "-m", "openrouter/test/model@deepinfra:low",
                 "--root", str(run_root)]) == 0
    first = json.loads(argv_file.read_text())

    # interrupt-style: mark the run queued again, then resume
    cfg = Config.load(run_root)
    [batch_dir] = list(cfg.run.dir.glob("*-resume-routed"))
    batch = json.loads((batch_dir / "batch.json").read_text())
    assert batch["runs"][0]["model_arg"] == "openrouter/test/model@deepinfra"
    batch["runs"][0]["state"] = "queued"
    (batch_dir / "batch.json").write_text(json.dumps(batch))

    argv_file.unlink()
    assert main(["run", "--resume", str(batch_dir), "--root", str(run_root)]) == 0
    second = json.loads(argv_file.read_text())
    assert second["argv"] == first["argv"]
    assert second["routing"] == first["routing"]
    [run] = json.loads((run_root / "docs/data/resume-routed/page.json").read_text())["runs"]
    assert run["model"] == "openrouter/test/model@deepinfra"
    assert run["route"]["served"] == ["Deepinfra"]


def test_routed_run_served_elsewhere_sets_error(run_root, monkeypatch):
    monkeypatch.setenv("FAKE_PI_SERVED", "Fireworks")
    assert main(["run", "--yes", "served elsewhere", "-m", "openrouter/test/model@deepinfra/fp8:low", "--root", str(run_root)]) == 0
    [run] = json.loads((run_root / "docs/data/served-elsewhere/page.json").read_text())["runs"]
    assert run["state"] == "complete"
    assert run["error"] == "served upstream outside requested only: Fireworks"


def test_read_route_parses_the_log(tmp_path):
    from art_crit.harness import read_route

    log = tmp_path / "route.jsonl"
    log.write_text('{"id": "g1", "provider": "DeepInfra"}\nnot json\n[1]\n')
    route = read_route(tmp_path, "openrouter/x/y@deepinfra/fp8")
    assert route == {"requested": {"only": ["deepinfra/fp8"], "allow_fallbacks": False}, "served": ["DeepInfra"], "cost_usd": None}
    log.write_text('{"id": "g1", "cost": 0.1}\n{"id": "g1", "cost": 0.2}\n{"id": "g2", "cost": 0.05}\n')
    assert read_route(tmp_path, "openrouter/x/y@a")["cost_usd"] == pytest.approx(0.25)  # last cost per response, summed
    assert read_route(tmp_path, "openrouter/x/y")["requested"] is None  # unpinned: OpenRouter's choice
    assert read_route(tmp_path, "openai-codex/gpt-6-sol") is None  # not an OpenRouter run


def test_unpinned_openrouter_run_records_upstream_and_real_cost(run_root, monkeypatch, tmp_path):
    """Every OpenRouter run loads the extension for the served upstream and the real charge;
    only pinned runs get ART_CRIT_OPENROUTER_ROUTING."""
    argv_file = tmp_path / "pi-argv.json"
    monkeypatch.setenv("FAKE_PI_ARGV", str(argv_file))
    monkeypatch.setenv("ART_CRIT_OPENROUTER_ROUTING", '{"only": ["leaked"]}')  # a stray value from art_crit's own env
    monkeypatch.setenv("FAKE_PI_SERVED", "Fireworks")
    assert main(["run", "--yes", "unpinned run", "-m", "openrouter/test/model:low", "--root", str(run_root)]) == 0
    sent = json.loads(argv_file.read_text())
    assert sent["argv"][sent["argv"].index("--model") + 1] == "openrouter/test/model:low"
    assert sent["argv"][sent["argv"].index("-e") + 1].endswith("openrouter_routing.ts")
    assert sent["routing"] is None and sent["route_log"].endswith("route.jsonl")
    [run] = json.loads((run_root / "docs/data/unpinned-run/page.json").read_text())["runs"]
    assert run["model"] == "openrouter/test/model" and "-via-" not in run["id"]
    assert run["route"] == {"requested": None, "served": ["Fireworks"], "cost_usd": 0.0042, "pi_cost_usd": 0.0025}
    assert run["metrics"]["cost_usd"] == 0.0042 and run["error"] is None


def test_finish_hook_is_identity_except_for_pi_openrouter_runs(tmp_path):
    from art_crit.harness import ClaudeCode, Pi

    metrics = {"cost_usd": 0.5}
    assert ClaudeCode().finish(tmp_path, "anthropic/claude-opus-5-5", metrics) == metrics
    assert Pi().finish(tmp_path, "openai-codex/gpt-6-sol", metrics) == metrics
    (tmp_path / "route.jsonl").write_text('{"id": "g1", "provider": "Fireworks"}\n{"id": "g1", "cost": 0.01}\n')
    done = Pi().finish(tmp_path, "openrouter/x/y@deepinfra", metrics)
    assert done["cost_usd"] == 0.01 and done["extra"]["route"]["pi_cost_usd"] == 0.5
    assert done["notes"] == ["served upstream outside requested only: Fireworks"]
    assert metrics == {"cost_usd": 0.5}  # the input isn't modified
