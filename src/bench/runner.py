"""`bench run`: plan, launch, collect, finalize, verify and import a batch of agent runs.
See SPEC.md "Running benchmarks (bench run)". A fresh batch and a `--resume`d one both end in
`execute()`: for each run, either run its agent (if unfinished) or reuse its run.json, then the kind's
output step if it hasn't succeeded yet, then import.

A run's state (batch.json and run.json) says only what the agent did: queued | running | complete | failed
| timeout. What the kind made of its work is `output` in run.json: {kind, ok, error, verified}. The progress
table's other labels (exporting, verifying...) are transient and never written."""

import contextlib
import difflib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import clean
from .config import RunRequest
from .harness import HARNESSES, add_tool_durations, split_harness
from .importer import cmd_import
from .kinds import KINDS
from .util import LEVEL_INDEX, LEVEL_ORDER, BenchError, iso_from_ms, make_run_id, parse_duration, title_from_slug

# batch.json run states that mean "this agent hasn't produced a finished result yet".
UNFINISHED = ("queued", "running")


def tool_version(name):
    """First version-looking token of `name --version` (or `-version`, for ffmpeg), or None."""
    for flag in ("--version", "-version"):
        try:
            r = subprocess.run([name, flag], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return None
        m = re.search(r"v?(\d+(?:\.\d+)+)", r.stdout + r.stderr) if r.returncode == 0 else None
        if m:
            return m.group(1)
    return None


def describe_tools(entries):
    """bench.toml [run].tools entries ("python3 (standard library only)") -> the text listed in the
    brief, e.g. "python3 3.14.7 (standard library only), ffmpeg 9.0.2". Tools not on PATH are left
    out (with a note), so the brief never promises something the agent can't run."""
    listed = []
    for entry in entries:
        name, _, note = entry.partition(" ")
        if not shutil.which(name):
            print(f"note: tool {name!r} from [run].tools is not on PATH; leaving it out of the brief")
            continue
        version = tool_version(name)
        listed.append(" ".join(part for part in (name, version, note.strip()) if part))
    return ", ".join(listed) or "none beyond the shell"


def expand_sets(config, set_args):
    """--set NAME (from bench.toml [sets]) or --set FILE (one model[:levels] per line, # comments)
    -> the model specs, in order, exactly as if each had been given with -m."""
    sets = config.sets if set_args else {}
    specs = []
    for arg in set_args:
        if arg in sets:
            specs += sets[arg]
        elif Path(arg).is_file():
            lines = (line.split("#", 1)[0].strip() for line in Path(arg).read_text().splitlines())
            specs += [line for line in lines if line]
        else:
            known = ", ".join(sorted(sets)) or "none defined"
            raise BenchError(f"unknown model set {arg!r}: not in bench.toml [sets] ({known}) and not a file")
    return specs


def slug_from_prompt(prompt):
    words = prompt.strip().split()[:6]
    slug = re.sub(r"[^a-z0-9]+", "-", " ".join(words).lower()).strip("-")
    return slug[:40].rstrip("-") or "run"


def parse_model_spec(spec, known):
    """'model[:levels]' -> (model, levels_text_or_None), resolved against the harness's model list.
    Model ids can contain ':' themselves (e.g. 'openrouter/x/y:batch'), so a full-spec match wins;
    otherwise the levels are what follows the last ':'. Unknown models are an error with suggestions."""
    if spec in known:
        return spec, None
    model, sep, levels = spec.rpartition(":")
    if sep and model in known:
        return model, levels
    name = spec if spec in known or not sep else model
    close = difflib.get_close_matches(name, known, n=3, cutoff=0.6)
    hint = f" (did you mean: {', '.join(close)}?)" if close else ""
    raise BenchError(f"unknown model {name!r}{hint}; see `bench models`")


def expand_levels(spec, supported, model):
    """spec: 'all' | 'off' | 'a..b' | 'a,b,c'. supported: this model's levels, in LEVEL_ORDER.
    Raises BenchError naming the supported levels when a requested one isn't supported."""
    if spec == "all":
        return [level for level in supported if level != "off"]
    if spec == "off":
        if "off" not in supported:
            raise BenchError(f"{model}: level 'off' not supported (supported: {', '.join(supported)})")
        return ["off"]
    if ".." in spec:
        a, b = spec.split("..", 1)
        for level in (a, b):
            if level not in LEVEL_INDEX:
                raise BenchError(f"{model}: unknown level {level!r} (LEVEL_ORDER: {', '.join(LEVEL_ORDER)})")
        lo, hi = LEVEL_INDEX[a], LEVEL_INDEX[b]
        wanted = list(LEVEL_ORDER[min(lo, hi) : max(lo, hi) + 1])
    else:
        wanted = [s.strip() for s in spec.split(",") if s.strip()]
    unsupported = [level for level in wanted if level not in supported]
    if unsupported:
        raise BenchError(
            f"{model}: level(s) {', '.join(unsupported)} not supported (supported: {', '.join(supported)})"
        )
    return [level for level in wanted if level != "off" or spec == "off"]


class Harnesses(dict):
    """Harness instances by name, created on first use (so pi isn't needed for a Claude-Code-only
    batch). Tests pass pre-built ones."""

    def __missing__(self, name):
        if name not in HARNESSES:
            raise BenchError(f"unknown harness {name!r} (known: {', '.join(HARNESSES)})")
        self[name] = HARNESSES[name]()
        return self[name]


def plan_runs(config, request, harnesses=None):
    """Resolve every -m [HARNESS:]MODEL[@UPSTREAMS][:LEVELS] (and --set entry) against its harness
    (pi when there's no prefix) before anything starts. Returns [(harness name, model_arg, level), ...]
    with the harness's own model id (`model_arg` keeps the `@slugs` suffix; the base id is what pi gets).
    The same model+upstream given twice has its levels merged."""
    harnesses = harnesses if harnesses is not None else Harnesses()
    model_specs = [*expand_sets(config, request.model_sets), *request.model_specs]
    if not model_specs:
        raise BenchError("at least one -m MODEL or --set is required")
    effort_default = request.effort
    known, levels_by_model = {}, {}
    for spec in model_specs:
        name, rest = split_harness(spec)
        harness = harnesses[name]
        rest, upstreams = harness.split_spec(rest)
        if name not in known:
            known[name] = set(harness.models())
        model, levels_text = parse_model_spec(rest, known[name])
        model = harness.resolve(model)
        supported = harness.levels(model)
        levels = expand_levels(levels_text or effort_default or "all", supported, model)
        model_arg = harness.pinned(model, upstreams)
        levels_by_model.setdefault((name, model_arg), {}).update(dict.fromkeys(levels))

    return [(name, model, level) for (name, model), levels in levels_by_model.items() for level in levels]


def assign_run_ids(plan, harnesses, started):
    """The plan -> batch.json's runs, each with its id (the run directory's name, which is also its
    id on the site). Two runs that resolve to one id (models whose names differ only before the last
    "/") are an error before anything starts."""
    runs, owner = [], {}
    for name, model_arg, level in plan:
        harness = harnesses[name]
        display = harness.display_model(model_arg)
        run_id = make_run_id(display, level, started, harness.tag)
        if run_id in owner:
            raise BenchError(f"{owner[run_id]!r} and {model_arg!r} both resolve to the run id {run_id!r}; run them in separate batches")
        owner[run_id] = model_arg
        runs.append({"id": run_id, "harness": name, "model": display, "model_arg": model_arg, "level": level, "state": "queued"})
    return runs


def run_label(run):
    return run["model"] if run["harness"] == "pi" else f"{run['model']} [{run['harness']}]"


def page_json(root, slug):
    path = root / "docs" / "data" / slug / "page.json"
    return json.loads(path.read_text()) if path.is_file() else None


def clean_prompt(config, prompt):
    """The prompt as import stores it on the page (path rewrites applied), for comparing."""
    return clean.rewrite_text(prompt.strip(), config.rewrites)[0]


def render_brief(brief_text, prompt, kind="godot", tool_entries=()):
    template = brief_text if brief_text else KINDS[kind]().brief()
    tools = describe_tools(tool_entries) if "{tools}" in template else ""
    return template.format(prompt=prompt, tools=tools)


def last_line(path):
    if not path.is_file():
        return None
    lines = [line for line in path.read_text(errors="replace").splitlines() if line.strip()]
    return lines[-1][:200] if lines else None


def fmt_elapsed(seconds):
    if seconds is None:
        return "-"
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


class Progress:
    """tty: a table redrawn every 2s, re-parsing each running row's growing session file for
    live turns/tokens/cost. non-tty: one line per state change."""

    def __init__(self, harnesses, runs):
        self.harnesses = harnesses
        self.rows = {}
        for r in runs:
            state = "done" if r["state"] == "complete" else r["state"]
            self.rows[r["id"]] = {
                "model": run_label(r), "harness": r["harness"], "level": r["level"], "state": state,
                "turns": 0, "tokens": 0, "cost": 0.0, "started": None, "elapsed": None, "harness_dir": None,
            }
        self.lock = threading.Lock()
        self.tty = sys.stdout.isatty()
        self._stop = threading.Event()
        self._printed_lines = 0
        self._thread = threading.Thread(target=self._loop, daemon=True) if self.tty else None

    def start(self):
        if self._thread:
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self.tty:
            self._render()

    def track(self, key, harness_dir):
        """Point a row at its harness dir, so the tty loop can find the growing session file."""
        with self.lock:
            self.rows[key]["harness_dir"] = harness_dir

    def update(self, key, **fields):
        with self.lock:
            row = self.rows[key]
            if fields.get("state") == "running" and row["started"] is None:
                row["started"] = time.monotonic()
            row.update(fields)
            if fields.get("state") in ("done", "no output", "failed", "timeout") and row["started"] is not None:
                row["elapsed"] = time.monotonic() - row["started"]
            state = fields.get("state")
        if not self.tty and state:
            print(f"{row['model']} {row['level']}: {state}")

    def _loop(self):
        while not self._stop.wait(2):
            self._refresh_running()
            self._render()

    def _refresh_running(self):
        with self.lock:
            running = [r for r in self.rows.values() if r["state"] == "running" and r["harness_dir"]]
        for row in running:
            try:
                metrics = self.harnesses[row["harness"]].metrics(row["harness_dir"], row["level"])
            except OSError:
                continue
            if not metrics:
                continue
            with self.lock:
                row["turns"] = metrics["turns"]
                row["tokens"] = metrics["tokens"]["total"]
                row["cost"] = metrics["cost_usd"]

    def _render(self):
        with self.lock:
            rows = list(self.rows.values())
        header = f"{'model':<44} {'effort':<8} {'state':<10} {'elapsed':>7} {'turns':>6} {'tokens':>8} {'cost':>8}"
        lines = [header]
        for r in rows:
            elapsed = r["elapsed"] if r["elapsed"] is not None else (time.monotonic() - r["started"] if r["started"] else None)
            lines.append(
                f"{r['model']:<44} {r['level']:<8} {r['state']:<10} {fmt_elapsed(elapsed):>7} "
                f"{r['turns']:>6} {r['tokens']:>8} {r['cost']:>8.3f}"
            )
        if self._printed_lines:
            sys.stdout.write(f"\x1b[{self._printed_lines}A")
        for line in lines:
            sys.stdout.write("\x1b[2K" + line + "\n")
        sys.stdout.flush()
        self._printed_lines = len(lines)


def _kill_group(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass




class RunDir:
    """<batch>/<run id>/: run.json (the run's record), work/ (the agent's working dir, nothing else is
    written there), harness/ (the agent's session, stdout, stderr, brief, route log), output/ (what the kind made)."""

    def __init__(self, batch_dir, run_id):
        self.path = Path(batch_dir) / run_id
        self.work, self.harness, self.output = (self.path / name for name in ("work", "harness", "output"))
        self.record_path = self.path / "run.json"

    def reset(self):
        """Empty directories for a (re)run."""
        shutil.rmtree(self.path, ignore_errors=True)
        for d in (self.work, self.harness):
            d.mkdir(parents=True)

    def read(self):
        return json.loads(self.record_path.read_text()) if self.record_path.is_file() else None

    def write(self, record):
        self.record_path.write_text(json.dumps(record, indent=2) + "\n")


def run_agent(harness, run, rd, batch, version, timeout_s, progress, live, live_lock, interrupted):
    """Run one agent to completion (or until killed by a timeout or Ctrl-C). Returns the run's record
    (written to its run.json), or None if it was killed for a Ctrl-C (the caller leaves its batch.json
    state as "queued" so --resume reruns it; nothing is collected for a run that never really finished)."""
    rd.reset()
    brief = batch["brief"]
    (rd.harness / "brief.md").write_text(brief)  # kept out of work/: never seen/edited by the agent

    cmd = harness.command(run["model_arg"], run["level"], brief, rd.harness)
    stdout_path, stderr_path = rd.harness / "events.jsonl", rd.harness / "stderr.txt"
    started = datetime.now(timezone.utc)
    key = run["id"]
    progress.track(key, rd.harness)
    progress.update(key, state="running")

    exit_code, timed_out = None, False
    try:
        with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
            proc = subprocess.Popen(cmd, cwd=rd.work, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True, env=harness.env(run["model_arg"], rd.harness))
            with live_lock:
                live[key] = proc
                if interrupted.is_set():  # Ctrl-C landed between Popen and registering: kill it here
                    _kill_group(proc)
            try:
                exit_code = proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_group(proc)
                exit_code = proc.wait()
    except OSError as e:
        return collect(rd, batch, run, harness, version, started, datetime.now(timezone.utc), "failed", f"cannot run harness: {e}", None)
    finally:
        with live_lock:
            live.pop(key, None)

    if interrupted.is_set():
        return None

    ended = datetime.now(timezone.utc)
    session_path = harness.session_file(rd.harness)
    metrics = harness.metrics(rd.harness, run["level"]) if session_path else None

    if timed_out:
        state, error = "timeout", f"timed out after {int(timeout_s)}s"
    elif exit_code != 0:
        state, error = "failed", last_line(stderr_path) or f"harness exited {exit_code}"
    elif session_path is None:
        state, error = "failed", "no session file written"
    elif metrics["ended_in_error"]:
        state, error = "failed", (metrics["error_message"] or last_line(stderr_path) or "assistant ended in error")[:200]
    else:
        state, error = "complete", None

    record = collect(rd, batch, run, harness, version, started, ended, state, error, metrics)
    progress.update(key, state=state, turns=record["metrics"]["turns"], tokens=record["metrics"]["tokens_total"], cost=record["metrics"]["cost_usd"])
    return record


def collect(rd, batch, run, harness, version, started, ended, state, error, metrics):
    """Write harness/conversation.json (the session in pi's format, which the viewer renders, with
    each tool's duration) and run.json (the run's record, `output` still null). Returns the record."""
    if harness.session_file(rd.harness):
        entries = add_tool_durations(harness.session_entries(rd.harness, batch["brief"], run["level"]))
        (rd.harness / "conversation.json").write_text(json.dumps(entries, indent=2) + "\n")

    metrics = harness.finish(rd.harness, run["model"], dict(metrics or {}))
    for note in metrics.get("notes", ()):
        error = f"{error}; {note}" if error else note
    tokens = metrics.get("tokens") or {}
    record = {
        "id": run["id"],
        "page": batch["page"],
        "model": run["model"],
        "effort": run["level"],
        "kind": batch["kind"],
        "started_at": iso_from_ms(int(started.timestamp() * 1000)),
        "batch": rd.path.parent.name,
        "harness": {"name": harness.name, "version": version},
        "state": state,
        "error": error,
        "route": None,
        **metrics.get("extra", {}),  # whatever the harness adds to the run (pi: the OpenRouter route)
        "metrics": {
            "duration_ms": int((ended - started).total_seconds() * 1000),
            "cost_usd": metrics.get("cost_usd", 0.0),
            "tool_calls": metrics.get("tool_calls", 0),
            "turns": metrics.get("turns", 0),
            "tokens_total": tokens.get("total", 0),
            "tokens_input": tokens.get("input", 0),
            "tokens_output": tokens.get("output", 0),
            "tokens_reasoning": tokens.get("reasoning", 0),
            "tokens_cache_read": tokens.get("cacheRead", 0),
        },
        "output": None,
    }
    rd.write(record)
    return record


def finish_output(kind, rd, record, lock, verify, progress):
    """The kind's step on a completed run: finalize its work into output/, then verify it. Sets
    record["output"] = {kind, ok, error, verified}; a step that fails leaves the agent's state alone."""
    key = record["id"]
    progress.update(key, state=kind.activity)
    shutil.rmtree(rd.output, ignore_errors=True)
    with lock if kind.serial else contextlib.nullcontext():
        ok, error = kind.finalize(rd.work, rd.output)
    output = {"kind": kind.name, "ok": ok, "error": error, "verified": None}
    if ok and verify:
        progress.update(key, state="verifying")
        try:
            report = kind.verify(rd.output)
            output["verified"] = report["ok"] if report else None
        except Exception as e:  # verification must never fail the run
            print(f"note: verification of {record['id']} failed to run: {e}", file=sys.stderr)
    record["output"] = output
    rd.write(record)
    progress.update(key, state="done" if ok else "no output")


def write_batch_json(batch_dir, batch):
    (batch_dir / "batch.json").write_text(json.dumps(batch, indent=2) + "\n")


def batch_versions(batch):
    """{harness name: version} from batch.json."""
    return batch["harnesses"]


def read_batch(batch_dir):
    batch = json.loads((Path(batch_dir) / "batch.json").read_text())
    if any("id" not in r for r in batch["runs"]):
        raise BenchError(f"{batch_dir} was made by an older bench (one directory per model); it can't be resumed")
    return batch


def execute(config, request, batch_dir, harnesses, verify=True):
    """Run every unfinished agent, finalize + verify what needs it, then import.
    Drives both a fresh batch and a `--resume`d one (see module docstring)."""
    batch = read_batch(batch_dir)
    parallel = request.parallel or config.run.parallel
    timeout_s = parse_duration(request.timeout or config.run.timeout)
    runs = batch["runs"]
    versions = batch_versions(batch)
    kind = KINDS[batch["kind"]]()
    slug, title = batch["page"], batch["title"]

    progress = Progress(harnesses, runs)
    progress.start()
    finalize_lock = threading.Lock()
    live, live_lock, interrupted = {}, threading.Lock(), threading.Event()

    def save():
        write_batch_json(batch_dir, batch)

    def work(run):
        if interrupted.is_set():
            return
        rd = RunDir(batch_dir, run["id"])
        harness = harnesses[run["harness"]]
        if run["state"] in UNFINISHED:
            run["state"] = "running"
            save()
            record = run_agent(harness, run, rd, batch, versions.get(run["harness"]), timeout_s, progress, live, live_lock, interrupted)
            if record is None:
                return  # Ctrl-C: left "running" here; the handler below resets it to "queued"
            run["state"] = record["state"]
            save()
        else:
            record = rd.read()
            if record is None:
                return
        if interrupted.is_set():
            return
        if record["state"] == "complete" and not (record["output"] and record["output"]["ok"]):
            finish_output(kind, rd, record, finalize_lock, verify, progress)

    pool = ThreadPoolExecutor(max_workers=parallel)
    futures = [pool.submit(work, r) for r in runs]
    try:
        for f in futures:
            f.result()
    except KeyboardInterrupt:
        with live_lock:  # set under the lock so run_agent can't register a process we then miss
            interrupted.set()
            for proc in live.values():
                _kill_group(proc)
        pool.shutdown(wait=True, cancel_futures=True)
        for r in runs:
            if r["state"] == "running":
                r["state"] = "queued"
        save()
        progress.stop()
        print(f"interrupted; resume with: bench run --resume {batch_dir}")
        sys.exit(130)
    pool.shutdown(wait=True)
    progress.stop()

    page_exists = (config.root / "docs" / "data" / slug / "page.json").is_file()
    import_title = title if (batch["title_is_explicit"] or not page_exists) else None
    return _import_and_publish(config, batch_dir, slug, import_title, request.publish)


def cmd_run(config, request, *, yes=False, dry_run=False, resume=None, verify=True, harnesses=None):
    harnesses = harnesses if harnesses is not None else Harnesses()
    root = config.root

    if resume:
        batch_dir = Path(resume)
        stored = read_batch(batch_dir).get("request")
        if stored:  # replay what the batch recorded; explicit CLI flags override it
            merged = RunRequest.from_dict(stored)
            merged.parallel = request.parallel or merged.parallel
            merged.timeout = request.timeout or merged.timeout
            merged.publish = request.publish or merged.publish
            request = merged
        return execute(config, request, batch_dir, harnesses, verify)

    prompt, kind, page, title = request.prompt, request.kind, request.page, request.title
    # Adding runs to an existing page: --page alone reuses its prompt and kind.
    existing = page_json(root, page) if page else None
    if not prompt and existing:
        prompt = existing.get("prompt") or ""
    if not prompt:
        raise BenchError("PROMPT or --prompt-file is required (or --page with an existing page, to reuse its prompt)")
    if not request.model_specs and not request.model_sets:
        raise BenchError("at least one -m MODEL or --set is required")
    slug = page or slug_from_prompt(prompt)
    existing = page_json(root, slug)
    page_exists = existing is not None
    page_kind = existing.get("kind", "godot") if page_exists else None
    kind = kind or page_kind or "godot"
    if page_exists and page_kind != kind:
        raise BenchError(f"page {slug!r} holds {page_kind} runs; use --kind {page_kind} or another --page")
    # Every import replaces the page's prompt, so a different one would silently relabel the existing runs.
    if page_exists and not request.change_prompt and existing.get("prompt") and clean_prompt(config, prompt) != existing["prompt"]:
        raise BenchError(
            f"page {slug!r} was run with a different prompt:\n  {existing['prompt']}\n"
            "Leave the prompt out to reuse it, use another --page, or pass --change-prompt to replace it for the whole page."
        )
    if kind not in KINDS:
        raise BenchError(f"unknown kind {kind!r} (expected one of: {', '.join(KINDS)})")
    missing = KINDS[kind]().missing_tools()
    if missing:
        hint = KINDS[kind].tools_hint
        raise BenchError(f"--kind {kind} needs {' and '.join(missing)} on PATH" + (f" ({hint})" if hint else ""))

    plan = plan_runs(config, request, harnesses)
    versions = {name: harnesses[name].version() for name in dict.fromkeys(name for name, _, _ in plan)}
    title_is_explicit = bool(title)
    if not title:
        title = (existing.get("title") if page_exists else None) or title_from_slug(slug)

    started = datetime.now()
    while (config.run.dir / f"{started:%Y-%m-%d-%H%M%S}-{slug}").exists():  # two batches for one page in the same second
        time.sleep(0.2)
        started = datetime.now()
    batch_dir = config.run.dir / f"{started:%Y-%m-%d-%H%M%S}-{slug}"
    runs = assign_run_ids(plan, harnesses, started)

    print("harness: " + ", ".join(f"{name} {version}" for name, version in versions.items()))
    print(f"kind: {kind}")
    print(f"page: {slug} ({'existing' if page_exists else 'new'}, title: {title!r})")
    print(f"prompt: {prompt}")
    for i, (name, model, level) in enumerate(plan, 1):
        print(f"  {i}. {'' if name == 'pi' else name + ':'}{model}:{level}")
    print(f"batch dir: {batch_dir}")

    if dry_run:
        return 0

    if not yes:
        if not sys.stdin.isatty():
            raise BenchError("refusing to prompt for confirmation on a non-tty stdin; pass --yes")
        answer = input("Start? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("aborted")
            return 1

    batch_dir.mkdir(parents=True)
    (batch_dir / "prompt.md").write_text(prompt)
    batch = {
        "prompt": prompt, "kind": kind, "page": slug, "title": title, "title_is_explicit": title_is_explicit,
        "harnesses": versions, "brief": render_brief(request.brief, prompt, kind, config.run.tools),
        "request": request.to_dict(), "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs": runs,
    }
    write_batch_json(batch_dir, batch)

    return execute(config, request, batch_dir, harnesses, verify)


def _import_and_publish(config, batch_dir, slug, title, publish):
    cmd_import(config, batch_dir, page=slug, title=title)
    print(f"imported into page {slug!r}. Preview with: bench serve")
    if publish:
        from .cli import cmd_publish

        return cmd_publish(config.root, f"bench run: {slug}")
    print("publish with: bench publish")
    return 0


def cmd_models(harness, search=None):
    models = harness.models()
    if search:
        models = [m for m in models if search.lower() in m.lower()]
    for model in sorted(models):
        if search:
            try:
                levels = harness.levels(model)
            except BenchError as e:
                print(f"{model}: {e}")
                continue
            print(f"{model}: {', '.join(levels)}")
        else:
            print(model)
    return 0
