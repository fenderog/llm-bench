"""`bench run`: plan, launch, collect, export, verify and import a batch of agent runs.
See SPEC.md "Running benchmarks (bench run)". A fresh batch and a `--resume`d one both end in
`execute()`: for each run, either run its agent (if unfinished) or reuse its entry, then
export+verify if needed, then import."""

import importlib.resources
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import build
from .harness import Pi, parse_session
from .importer import cmd_import
from .util import LEVEL_INDEX, LEVEL_ORDER, BenchError, title_from_slug

# batch.json run states that mean "this agent hasn't produced a finished result yet".
UNFINISHED = ("queued", "running")


def default_brief_text():
    return importlib.resources.files("bench").joinpath("briefs/godot.md").read_text()


def load_run_config(root):
    cfg = {"dir": Path.home() / "dev" / "bench-runs", "parallel": 8, "timeout": "30m"}
    cfg_path = root / "bench.toml"
    if cfg_path.is_file():
        run_cfg = tomllib.loads(cfg_path.read_text()).get("run", {})
        if "dir" in run_cfg:
            cfg["dir"] = Path(run_cfg["dir"]).expanduser()
        cfg["parallel"] = run_cfg.get("parallel", cfg["parallel"])
        cfg["timeout"] = run_cfg.get("timeout", cfg["timeout"])
    return cfg


def parse_duration(text):
    """'30m' / '90s' / '1h' -> seconds."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([smh])", text.strip())
    if not m:
        raise BenchError(f"bad duration: {text!r} (expected e.g. 30m, 90s, 1h)")
    n, unit = float(m.group(1)), m.group(2)
    return n * {"s": 1, "m": 60, "h": 3600}[unit]


def model_tag(model):
    return re.sub(r"[^a-z0-9]", "", model.rsplit("/", 1)[-1].lower())


def slug_from_prompt(prompt):
    words = prompt.strip().split()[:6]
    slug = re.sub(r"[^a-z0-9]+", "-", " ".join(words).lower()).strip("-")
    return slug[:40].rstrip("-") or "run"


def parse_model_spec(spec):
    """'model[:levels]' -> (model, levels_text_or_None)."""
    if ":" in spec:
        model, levels = spec.split(":", 1)
        return model, levels
    return spec, None


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


def plan_runs(harness, model_specs, effort_default):
    """Resolve every -m MODEL[:LEVELS] against the harness before anything starts. Returns
    [(model, level), ...]. The same model given twice has its levels merged; two models that
    resolve to the same model-dir tag are an error."""
    levels_by_model = {}
    for spec in model_specs:
        model, levels_text = parse_model_spec(spec)
        supported = harness.levels(model)
        levels = expand_levels(levels_text or effort_default or "all", supported, model)
        levels_by_model.setdefault(model, dict.fromkeys(()))
        levels_by_model[model].update(dict.fromkeys(levels))

    tag_owner = {}
    for model in levels_by_model:
        tag = model_tag(model)
        if tag in tag_owner:
            raise BenchError(f"{tag_owner[tag]!r} and {model!r} both resolve to the model dir tag {tag!r}; rename one or use --page")
        tag_owner[tag] = model

    return [(model, level) for model, levels in levels_by_model.items() for level in levels]


def render_brief(brief_file, prompt):
    template = Path(brief_file).read_text() if brief_file else default_brief_text()
    return template.format(prompt=prompt)


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

    def __init__(self, harness, runs):
        self.harness = harness
        self.rows = {}
        for r in runs:
            state = "done" if r["state"] == "complete" else r["state"]
            self.rows[(r["model"], r["level"])] = {
                "model": r["model"], "level": r["level"], "state": state,
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

    def track(self, model, level, harness_dir):
        """Point a row at its harness scratch dir, so the tty loop can find the growing session file."""
        with self.lock:
            self.rows[(model, level)]["harness_dir"] = harness_dir

    def update(self, model, level, **fields):
        with self.lock:
            row = self.rows[(model, level)]
            if fields.get("state") == "running" and row["started"] is None:
                row["started"] = time.monotonic()
            row.update(fields)
            if fields.get("state") in ("done", "failed", "timeout") and row["started"] is not None:
                row["elapsed"] = time.monotonic() - row["started"]
            state = fields.get("state")
        if not self.tty and state:
            print(f"{model} {level}: {state}")

    def _loop(self):
        while not self._stop.wait(2):
            self._refresh_running()
            self._render()

    def _refresh_running(self):
        with self.lock:
            running = [r for r in self.rows.values() if r["state"] == "running" and r["harness_dir"]]
        for row in running:
            session_path = self.harness.session_file(row["harness_dir"])
            if not session_path or not session_path.is_file():
                continue
            try:
                metrics = parse_session(session_path)
            except OSError:
                continue
            with self.lock:
                row["turns"] = metrics["turns"]
                row["tokens"] = metrics["tokens"]["total"]
                row["cost"] = metrics["cost_usd"]

    def _render(self):
        with self.lock:
            rows = list(self.rows.values())
        header = f"{'model':<30} {'effort':<8} {'state':<10} {'elapsed':>7} {'turns':>6} {'tokens':>8} {'cost':>8}"
        lines = [header]
        for r in rows:
            elapsed = r["elapsed"] if r["elapsed"] is not None else (time.monotonic() - r["started"] if r["started"] else None)
            lines.append(
                f"{r['model']:<30} {r['level']:<8} {r['state']:<10} {fmt_elapsed(elapsed):>7} "
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


def run_agent(harness, run, version, brief, timeout_s, progress, live, live_lock, interrupted):
    """Run one agent to completion (or until killed by a timeout or Ctrl-C). Returns the run
    entry, or None if it was killed for a Ctrl-C (the caller leaves its batch.json state as
    "queued" so --resume reruns it; nothing is collected for a run that never really finished)."""
    model, level, model_dir = run["model"], run["level"], run["model_dir"]
    level_dir = model_dir / level
    if level_dir.exists():
        shutil.rmtree(level_dir)
    level_dir.mkdir(parents=True)
    harness_dir = model_dir / ".harness" / level
    if harness_dir.exists():
        shutil.rmtree(harness_dir)
    harness_dir.mkdir(parents=True)
    (harness_dir / "brief.md").write_text(brief)  # kept out of level_dir: never seen/edited by the agent

    cmd = harness.command(model, level, brief, harness_dir)
    stdout_path, stderr_path = harness_dir / "events.jsonl", harness_dir / "stderr.txt"
    started = datetime.now(timezone.utc)
    progress.track(model, level, harness_dir)
    progress.update(model, level, state="running")

    exit_code, timed_out = None, False
    try:
        with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
            proc = subprocess.Popen(cmd, cwd=level_dir, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
            with live_lock:
                live[(model, level)] = proc
                if interrupted.is_set():  # Ctrl-C landed between Popen and registering: kill it here
                    _kill_group(proc)
            try:
                exit_code = proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_group(proc)
                exit_code = proc.wait()
    except OSError as e:
        ended = datetime.now(timezone.utc)
        return collect(level_dir, harness_dir, None, cmd, harness, version, started, ended, None, "failed", f"cannot run harness: {e}", model, None)
    finally:
        with live_lock:
            live.pop((model, level), None)

    if interrupted.is_set():
        return None

    ended = datetime.now(timezone.utc)
    session_path = harness.session_file(harness_dir)
    metrics = parse_session(session_path) if session_path and session_path.is_file() else None

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

    entry = collect(level_dir, harness_dir, session_path, cmd, harness, version, started, ended, exit_code, state, error, model, metrics)
    progress.update(model, level, state=state, turns=entry["turns"], tokens=entry["tokens"]["total"], cost=entry["costUsd"])
    return entry


def collect(level_dir, harness_dir, session_path, cmd, harness, version, started, ended, exit_code, state, error, model, metrics):
    """Write <level>/session.jsonl, conversation.json, events.jsonl, status.json, stderr.txt,
    data.json. Returns the run entry (also used for the model dir's data.json)."""
    if session_path and session_path.is_file():
        text = session_path.read_text(encoding="utf-8")
        shutil.copy(session_path, level_dir / "session.jsonl")
        entries = [json.loads(line) for line in text.splitlines() if line.strip()]
        (level_dir / "conversation.json").write_text(json.dumps(entries, indent=2) + "\n")
    events_src = harness_dir / "events.jsonl"
    if events_src.is_file() and events_src.stat().st_size:
        # Drop streaming snapshots (each repeats the whole partial message; the session has the final one).
        # The raw file stays in .harness/.
        lines = events_src.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        (level_dir / "events.jsonl").write_text("".join(line for line in lines if not _is_stream_update(line)))
    stderr_src = harness_dir / "stderr.txt"
    if stderr_src.is_file() and stderr_src.stat().st_size:
        shutil.copy(stderr_src, level_dir / "stderr.txt")

    duration_ms = int((ended - started).total_seconds() * 1000)
    status = {
        "state": state, "error": error, "exit_code": exit_code, "argv": cmd,
        "harness": {"name": harness.name, "version": version},
        "startedAt": started.strftime("%Y-%m-%dT%H:%M:%SZ"), "endedAt": ended.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "durationMs": duration_ms,
    }
    (level_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n")

    tokens = (metrics or {}).get("tokens") or {"input": 0, "output": 0, "total": 0, "reasoning": 0, "cacheRead": 0, "cacheWrite": 0}
    entry = {
        "model": model,
        "thinkingLevel": (metrics or {}).get("thinking_level"),
        "startedAt": int(started.timestamp() * 1000),
        "endedAt": int(ended.timestamp() * 1000),
        "durationMs": duration_ms,
        "costUsd": (metrics or {}).get("cost_usd", 0.0),
        "toolCalls": (metrics or {}).get("tool_calls", 0),
        "turns": (metrics or {}).get("turns", 0),
        "tokens": tokens,
        "state": state,
        "error": error,
    }
    (level_dir / "data.json").write_text(json.dumps(entry, indent=2) + "\n")
    return entry


def _is_stream_update(line):
    try:
        return json.loads(line).get("type") == "message_update"
    except (ValueError, AttributeError):
        return False


def write_model_data_json(model_dir, harness, version, entries):
    data = {"schema": "bench-run/1", "harness": {"name": harness.name, "version": version}, "runs": entries}
    (model_dir / "data.json").write_text(json.dumps(data, indent=2) + "\n")


def export_and_verify(run, entry, export_lock, godot_bin, do_verify, progress):
    """Export (if wasm/<level> is missing) and verify (if its report is missing). A run whose
    agent completed but whose export fails keeps entry["state"] == "complete" (SPEC step 6: the
    agent did finish); only entry["error"] is set, so the viewer shows the error without a
    failed/timeout badge."""
    if entry["state"] != "complete":
        return
    model, level, model_dir = run["model"], run["level"], run["model_dir"]
    level_dir = model_dir / level
    wasm_dir = model_dir / "wasm" / level
    if not (wasm_dir / "index.html").is_file():
        progress.update(model, level, state="exporting")
        with export_lock:
            ok, _manifest, error = build.export_project(godot_bin, level_dir, wasm_dir)
        if not ok:
            entry["error"] = error
            progress.update(model, level, state="failed")
            return
    if do_verify and not (wasm_dir / "verification" / "verify-report.json").is_file():
        progress.update(model, level, state="verifying")
        try:
            build.verify_build(wasm_dir)
        except Exception as e:  # verification must never fail the run
            print(f"note: verification of {model}/{level} failed to run: {e}", file=sys.stderr)
    progress.update(model, level, state="done")


def write_batch_json(batch_dir, batch):
    serializable = {**batch, "runs": [{**r, "model_dir": str(r["model_dir"])} for r in batch["runs"]]}
    (batch_dir / "batch.json").write_text(json.dumps(serializable, indent=2) + "\n")
    return serializable


def execute(root, batch_dir, batch, harness, version, parallel, timeout_s, godot_bin, verify, publish):
    """Run every unfinished agent, export+verify everything that needs it, then import.
    Drives both a fresh batch and a `--resume`d one (see module docstring)."""
    runs = batch["runs"]
    slug, title = batch["page"], batch["title"]
    title_is_explicit = batch.get("title_is_explicit", False)
    brief = batch["brief"]

    entries_by_model = {}
    for model_dir in {r["model_dir"] for r in runs}:
        data_path = model_dir / "data.json"
        entries_by_model[model_dir] = json.loads(data_path.read_text())["runs"] if data_path.is_file() else {}

    progress = Progress(harness, runs)
    progress.start()
    export_lock = threading.Lock()
    live, live_lock, interrupted = {}, threading.Lock(), threading.Event()

    def save():
        write_batch_json(batch_dir, batch)

    def work(run):
        if interrupted.is_set():
            return
        model_dir = run["model_dir"]
        if run["state"] in UNFINISHED:
            run["state"] = "running"
            save()
            entry = run_agent(harness, run, version, brief, timeout_s, progress, live, live_lock, interrupted)
            if entry is None:
                return  # Ctrl-C: left "running" here; the handler below resets it to "queued"
            entries_by_model[model_dir][run["level"]] = entry
            write_model_data_json(model_dir, harness, version, entries_by_model[model_dir])
            run["state"] = entry["state"]
            save()
        else:
            entry = entries_by_model[model_dir].get(run["level"])
            if entry is None:
                return
        if interrupted.is_set():
            return
        export_and_verify(run, entry, export_lock, godot_bin, verify, progress)
        write_model_data_json(model_dir, harness, version, entries_by_model[model_dir])
        save()

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

    model_dirs = sorted({r["model_dir"] for r in runs})
    page_exists = (root / "docs" / "data" / slug / "page.json").is_file()
    import_title = title if (title_is_explicit or not page_exists) else None
    return _import_and_publish(root, model_dirs, slug, import_title, publish)


def cmd_run(
    root, prompt=None, prompt_file=None, model_specs=(), effort=None, page=None, title=None,
    brief_file=None, parallel=None, timeout=None, yes=False, dry_run=False, publish=False,
    resume=None, godot_bin="godot", verify=True,
):
    harness = Pi()
    cfg = load_run_config(root)
    version = harness.version()

    if resume:
        batch_dir = Path(resume)
        batch = json.loads((batch_dir / "batch.json").read_text())
        for r in batch["runs"]:
            r["model_dir"] = Path(r["model_dir"])
        parallel = parallel or cfg["parallel"]
        timeout_s = parse_duration(timeout or cfg["timeout"])
        return execute(root, batch_dir, batch, harness, version, parallel, timeout_s, godot_bin, verify, publish)

    if prompt_file:
        prompt = Path(prompt_file).read_text().strip()
    if not prompt:
        raise BenchError("PROMPT or --prompt-file is required")
    if not model_specs:
        raise BenchError("at least one -m MODEL is required")

    plan = plan_runs(harness, model_specs, effort)
    slug = page or slug_from_prompt(prompt)
    page_json_path = root / "docs" / "data" / slug / "page.json"
    page_exists = page_json_path.is_file()
    title_is_explicit = bool(title)
    if not title:
        title = json.loads(page_json_path.read_text()).get("title") or title_from_slug(slug) if page_exists else title_from_slug(slug)
    parallel = parallel or cfg["parallel"]
    timeout_s = parse_duration(timeout or cfg["timeout"])

    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    batch_dir = cfg["dir"] / f"{ts}-{slug}"

    print(f"harness: {harness.name} {version}")
    print(f"page: {slug} ({'existing' if page_exists else 'new'}, title: {title!r})")
    print(f"prompt: {prompt}")
    for i, (model, level) in enumerate(plan, 1):
        print(f"  {i}. {model}:{level}")
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
    brief = render_brief(brief_file, prompt)

    model_dirs = {}
    for model, _ in plan:
        if model not in model_dirs:
            model_dirs[model] = batch_dir / f"{ts}-{model_tag(model)}-{slug}"
            model_dirs[model].mkdir(parents=True)
            (model_dirs[model] / "prompt.md").write_text(prompt)  # import reads the page prompt from here

    runs = [{"model": m, "level": l, "model_dir": model_dirs[m], "state": "queued"} for m, l in plan]
    batch = {
        "prompt": prompt, "page": slug, "title": title, "title_is_explicit": title_is_explicit,
        "harness": {"name": harness.name, "version": version}, "brief": brief,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs": runs,
    }
    write_batch_json(batch_dir, batch)

    return execute(root, batch_dir, batch, harness, version, parallel, timeout_s, godot_bin, verify, publish)


def _import_and_publish(root, model_dirs, slug, title, publish):
    for model_dir in model_dirs:
        cmd_import(root, model_dir, page=slug, title=title)
    print(f"imported into page {slug!r}. Preview with: bench serve")
    if publish:
        from .cli import cmd_publish

        return cmd_publish(root, f"bench run: {slug}")
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
