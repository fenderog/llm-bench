"""bench.toml, parsed once, plus `RunRequest`: everything one `bench run` needs to know.

`Config.load(root)` reads the file once in `cli.main` and is passed to the importer and runner,
so `[clean]`, `[run]` and `[sets]` share one parser. `RunRequest` is the run's inputs, built by the
CLI from argparse (and, later, by the website); it round-trips through JSON, so a run started
somewhere else carries exactly the same fields."""

import json
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .util import KINDS, BenchError, parse_duration

DEFAULT_TOOLS = ["python3", "node", "ffmpeg", "ffprobe"]


@dataclass
class RunSettings:
    """`[run]`: where batches go, how many agents at once, and the per-agent timeout/tool list."""

    dir: Path = field(default_factory=lambda: Path.home() / "dev" / "bench-runs")
    parallel: int = 8
    timeout: str = "30m"
    tools: list[str] = field(default_factory=lambda: list(DEFAULT_TOOLS))


@dataclass
class Config:
    """The parsed bench.toml. Missing file -> defaults (no rewrites, no sets)."""

    root: Path  # repo root: the site is <root>/docs
    rewrites: list[tuple[str, str]]  # [clean].rewrite + home dir, longest prefix first
    run: RunSettings = field(default_factory=RunSettings)
    sets: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, root):
        root = Path(root)
        path = root / "bench.toml"
        try:
            data = tomllib.loads(path.read_text()) if path.is_file() else {}
        except tomllib.TOMLDecodeError as e:
            raise BenchError(f"{path}: {e}")

        rewrites = [(str(Path.home()), "~"), *data.get("clean", {}).get("rewrite", {}).items()]
        rewrites.sort(key=lambda kv: -len(kv[0]))

        run_cfg = data.get("run", {})
        run = RunSettings(
            dir=Path(run_cfg.get("dir", "~/dev/bench-runs")).expanduser(),
            parallel=run_cfg.get("parallel", 8),
            timeout=run_cfg.get("timeout", "30m"),
            tools=list(run_cfg.get("tools", DEFAULT_TOOLS)),
        )
        _check_parallel(run.parallel, "bench.toml [run].parallel")
        parse_duration(run.timeout)

        sets = data.get("sets", {})
        for name, specs in sets.items():
            if not isinstance(specs, list) or not all(isinstance(s, str) for s in specs):
                raise BenchError(f"bench.toml [sets].{name} must be a list of \"model[:levels]\" strings")

        return cls(root=root, rewrites=rewrites, run=run, sets=sets)


def _check_parallel(value, what):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise BenchError(f"{what} must be a whole number of at least 1, got {value!r}")


@dataclass
class RunRequest:
    """One `bench run` request: the prompt and how to run it. JSON-serialisable (`to_dict`) so a
    batch.json can carry it and a run started elsewhere (website, script) can be replayed."""

    prompt: str
    kind: str | None = None
    page: str | None = None
    title: str | None = None
    model_specs: list[str] = field(default_factory=list)
    model_sets: list[str] = field(default_factory=list)
    effort: str | None = None
    brief: str | None = None  # brief template text; None = the built-in brief for the kind
    parallel: int | None = None
    timeout: str | None = None
    publish: bool = False
    change_prompt: bool = False

    def __post_init__(self):
        """Validated where it's built, before any batch dir exists (from argparse or from JSON)."""
        if self.kind is not None and self.kind not in KINDS:
            raise BenchError(f"unknown kind {self.kind!r} (expected one of: {', '.join(KINDS)})")
        if self.parallel is not None:
            _check_parallel(self.parallel, "parallel")
        if self.timeout is not None:
            parse_duration(self.timeout)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Unknown keys are ignored, so a batch.json written by another bench version still loads."""
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(json.loads(text))
