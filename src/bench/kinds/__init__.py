"""A kind is what a page's runs produce: `godot` (a project, exported to a web build), `media`
(image/video files) or `web` (a page packaged into one file). Each kind is one class here with the
same surface, registered in `KINDS` like `HARNESSES`; the runner and the importer never branch on
the kind's name. See SPEC.md "Kinds" and ADR-0017."""

import importlib.resources
import shutil
from dataclasses import dataclass, field


@dataclass
class Staged:
    """What `Kind.stage` produced for one run: the kind's part of the run's `output` record, its
    thumbnail (a path under the run dir), and for Godot the engine to store once (sha12, files or None)."""

    fields: dict
    thumb: str | None = None
    engine: tuple | None = None


@dataclass
class StageContext:
    """What a kind may use while staging a run for the site (the importer fills it in)."""

    docs_root: object
    slug: str
    run_id: str
    allow_threads: bool
    known_engines: set = field(default_factory=set)
    write_text: object = None  # (src, dest): copy a text file cleaned and secret-scanned like source


class Kind:
    name = "kind"
    tools = ()  # programs that must be on PATH before a batch starts
    tools_hint = ""  # how to install them
    activity = "processing"  # the progress table's label while `finalize` runs
    serial = False  # whether `finalize` must not run for two runs at once

    def brief(self):
        """The brief template ({prompt} and {tools} are substituted)."""
        return importlib.resources.files("bench.kinds").joinpath(f"{self.name}.md").read_text()

    def missing_tools(self):
        return [tool for tool in self.tools if not shutil.which(tool)]

    def finalize(self, work_dir, out_dir):
        """Turn the agent's work into the publishable output in out_dir (export, package, normalize).
        Returns (ok, error). Never raises for an agent's bad output: that is `ok=False` and an error."""
        raise NotImplementedError

    def verify(self, out_dir):
        """Check the output the way the site shows it; returns {ok, ...} or None when it can't be checked here."""
        return None

    def stage(self, out_dir, run_dir, ctx):
        """Copy the output into run_dir (cleaned) for the site. Returns a Staged."""
        raise NotImplementedError

    def keep_source(self, rel, path):
        """Whether a file of the agent's work dir is published as source."""
        return True


from .godot import Godot  # noqa: E402
from .media import Media  # noqa: E402
from .web import Web  # noqa: E402

KINDS = {kind.name: kind for kind in (Godot, Media, Web)}
