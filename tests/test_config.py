"""art-crit.toml is parsed once (`Config.load`), and `RunRequest` round-trips through JSON."""

from pathlib import Path

import pytest

from art_crit.config import Config, RunRequest
from art_crit.util import CritError


def test_config_load_reads_clean_run_and_sets(tmp_path):
    (tmp_path / "art-crit.toml").write_text(
        '[clean]\nrewrite = { "/Volumes/M2SSD" = "<vol>" }\n'
        '[run]\ndir = "~/runs"\nparallel = 3\ntimeout = "5m"\ntools = ["node (no npm)"]\n'
        '[sets]\nduo = ["m:low", "n:high"]\n'
    )
    cfg = Config.load(tmp_path)
    assert cfg.root == tmp_path
    assert dict(cfg.rewrites)["/Volumes/M2SSD"] == "<vol>"
    assert str(Path.home()) in dict(cfg.rewrites)
    assert cfg.run.dir == Path.home() / "runs"
    assert (cfg.run.parallel, cfg.run.timeout, cfg.run.tools) == (3, "5m", ["node (no npm)"])
    assert cfg.sets == {"duo": ["m:low", "n:high"]}


def test_config_defaults_without_bench_toml(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.sets == {} and cfg.run.parallel == 8
    assert [prefix for prefix, _ in cfg.rewrites] == [str(Path.home())]


def test_malformed_set_is_an_error(tmp_path):
    (tmp_path / "art-crit.toml").write_text('[sets]\nbad = "x"\n')
    with pytest.raises(CritError, match=r"\[sets\].bad must be a list"):
        Config.load(tmp_path)


def test_run_request_round_trips_through_json():
    request = RunRequest(
        prompt="a cube", kind="web", page="cube", title="Cube",
        model_specs=["openai-codex/gpt-6-sol:low"], model_sets=["duo"], effort="high",
        brief="the brief", parallel=2, timeout="5m", publish=True, change_prompt=True,
    )
    assert RunRequest.from_json(request.to_json()) == request
    # A batch.json carries it verbatim, so a run started elsewhere replays the same fields.
    assert RunRequest.from_dict(request.to_dict()).prompt == "a cube"


def test_bench_toml_is_parsed_in_one_place():
    src = Path(__file__).resolve().parents[1] / "src" / "art_crit"
    parsers = [p.name for p in src.glob("*.py") if "tomllib" in p.read_text()]
    assert parsers == ["config.py"]


@pytest.mark.parametrize("fields, match", [
    ({"timeout": "banana"}, "bad duration"),
    ({"parallel": 0}, "parallel must be"),
    ({"kind": "pdf"}, "unknown kind"),
])
def test_run_request_is_validated_when_built(fields, match):
    with pytest.raises(CritError, match=match):
        RunRequest(prompt="p", **fields)


def test_run_request_from_dict_ignores_unknown_keys():
    assert RunRequest.from_dict({"prompt": "p", "added_later": 1}) == RunRequest(prompt="p")


def test_bad_bench_toml_is_a_bench_error(tmp_path):
    (tmp_path / "art-crit.toml").write_text("[run\n")
    with pytest.raises(CritError, match="art-crit.toml"):
        Config.load(tmp_path)
    (tmp_path / "art-crit.toml").write_text('[run]\ntimeout = "soon"\n')
    with pytest.raises(CritError, match="bad duration"):
        Config.load(tmp_path)
