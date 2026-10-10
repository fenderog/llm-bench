"""The agent-program interface (`art-crit run` drives one of these): Pi and ClaudeCode. Also the
pure session parsers: metrics + state (see SPEC.md "Metrics" and "Harness interface").

Every harness hands the runner the same things: a command line, a session in pi's format
(`session_entries`, published as conversation.json, which the viewer renders) and metrics.
"""

import base64
import binascii
import json
import os
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from .kinds.media import thumbnail
from .util import LEVEL_INDEX, LEVEL_ORDER, CritError

# art-crit-shipped pi extension for OpenRouter runs (see pi_ext/openrouter_routing.ts): it records
# which upstream served each response and what OpenRouter charged, and pins the upstream for
# `MODEL@slug` runs. Passed with an explicit `-e` (which still loads under `-ne`).
ROUTING_EXTENSION = Path(__file__).parent / "pi_ext" / "openrouter_routing.ts"


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")


def split_route(rest):
    """'openrouter/x/y@a,b:low' -> ('openrouter/x/y:low', ['a', 'b']); no '@' -> (rest, None).
    The part after '@' is SLUGS[:LEVELS], so the levels suffix stays attached to the spec."""
    base, sep, tail = rest.partition("@")
    if not sep:
        return rest, None
    upstreams, _, levels = tail.partition(":")
    slugs = [s.strip().lower() for s in upstreams.split(",") if s.strip()]
    if not slugs or any(not SLUG_RE.match(s) for s in slugs):
        raise CritError(f"bad @UPSTREAM in {rest!r}: expected @slug[,slug...] (each matching {SLUG_RE.pattern!r})")
    return base + (f":{levels}" if levels else ""), slugs


def split_model_route(model_arg):
    """'openrouter/x/y@a,b' -> ('openrouter/x/y', ['a', 'b']); no '@' -> (model_arg, None)."""
    base, sep, tail = model_arg.partition("@")
    if not sep:
        return model_arg, None
    slugs = [s.strip().lower() for s in tail.split(",") if s.strip()]
    return base, slugs


def upstream_key(name):
    """An OpenRouter upstream as a comparable key: slug "atlas-cloud/fp8" and the display name
    "AtlasCloud" (what responses report) both -> "atlascloud". The "/variant" can't be checked."""
    return re.sub(r"[^a-z0-9]", "", name.split("/", 1)[0].lower())


def read_route(harness_dir, model):
    """The OpenRouter route for a run: {requested, served: [...], cost_usd}. requested =
    {only, allow_fallbacks} for a pinned run (`MODEL@slug`), None when OpenRouter picked the upstream.
    From route.jsonl, written by the pi routing extension: `{id, provider}` and `{id, cost}` lines
    per response. served = the distinct upstream names; cost_usd = what OpenRouter charged, summed
    over responses (the last cost per id), or None when no response reported one. None for runs
    that aren't OpenRouter runs."""
    base, slugs = split_model_route(model)
    if not base.startswith("openrouter/"):
        return None
    path = Path(harness_dir) / "route.jsonl"
    served, costs = [], {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            if rec.get("provider") and rec["provider"] not in served:
                served.append(rec["provider"])
            if isinstance(rec.get("cost"), (int, float)):
                costs[rec.get("id")] = rec["cost"]
    requested = {"only": slugs, "allow_fallbacks": False} if slugs else None
    return {"requested": requested, "served": served,
            "cost_usd": sum(costs.values()) if costs else None}


class Harness:
    """One per agent program. `tag` marks its runs' ids and folders ("" for pi, the default)."""

    name = "harness"
    tag = ""

    def version(self):
        raise NotImplementedError

    def models(self):
        raise NotImplementedError

    def levels(self, model):
        raise NotImplementedError

    def resolve(self, model):
        """An alias -> the model id it stands for (identity by default)."""
        return model

    def display_model(self, model):
        """The model name recorded for a run (what the site shows)."""
        return model

    def split_spec(self, rest):
        """'MODEL[@UPSTREAMS][:LEVELS]' -> ('MODEL[:LEVELS]', upstreams or None). Only pi runs can
        pin an OpenRouter upstream (see `pinned`)."""
        return split_route(rest)

    def pinned(self, model, upstreams):
        """The model argument for a run: `model`, or `model@a,b` when upstreams are pinned."""
        if upstreams:
            raise CritError(f"{model}: @UPSTREAM only works for pi openrouter/ models")
        return model

    def command(self, model, level, brief, session_dir):
        raise NotImplementedError

    def env(self, model=None, harness_dir=None):
        """The agent's environment (None = inherit art-crit's). Routed pi runs pass their
        model_arg + harness dir so per-run routing env can be set."""
        return None

    def session_file(self, session_dir):
        raise NotImplementedError

    def session_entries(self, session_dir, brief, level):
        """The session as pi-format entries (published as conversation.json), or None."""
        path = self.session_file(session_dir)
        if not path or not path.is_file():
            return None
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def metrics(self, session_dir, level=None):
        """parse_session()-shaped metrics, or None when there's no session yet. Tolerates a
        session that's still being written (live progress)."""
        path = self.session_file(session_dir)
        return parse_session(path) if path and path.is_file() else None

    def finish(self, harness_dir, model, metrics):
        """Final touches on a finished run's metrics (a dict, empty when the agent never wrote a
        session) from what the harness left in its scratch dir. `metrics["notes"]` are appended
        to the run's error and `metrics["extra"]` fields are added to the run. Identity by default."""
        return metrics


class Pi(Harness):
    """The `pi` CLI harness. See SPEC.md "Harness interface"."""

    name = "pi"

    def __init__(self, binary="pi"):
        self.binary = binary

    def version(self):
        try:
            r = subprocess.run([self.binary, "--version"], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise CritError(f"cannot run {self.binary} --version: {e}")
        if r.returncode != 0:
            raise CritError(f"{self.binary} --version failed: {r.stderr.strip()}")
        return r.stdout.strip().splitlines()[0].strip()

    def models(self):
        r = subprocess.run([self.binary, "--list-models"], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise CritError(f"{self.binary} --list-models failed: {r.stderr.strip()}")
        lines = r.stdout.splitlines()
        models = []
        for line in lines[1:]:  # skip the header row
            parts = line.split()
            if len(parts) >= 2:
                models.append(f"{parts[0]}/{parts[1]}")
        return models

    def levels(self, model):
        """Ask pi over RPC which thinking levels `model` supports, in LEVEL_ORDER.

        `proc.stdout.readline()` blocks, so a 30s wall-clock deadline computed from
        `time.time()` never fires if pi hangs without answering; a `threading.Timer` that
        kills the process is used instead, so the blocking readline() always unblocks.
        """
        cmd = [self.binary, "--mode", "rpc", "--no-session", "--model", model, "-ne", "-ns", "-np", "-nc"]
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except OSError as e:
            raise CritError(f"cannot run {self.binary}: {e}")
        timer = threading.Timer(30, proc.kill)
        timer.start()
        try:
            proc.stdin.write('{"type":"get_available_thinking_levels"}\n')
            proc.stdin.flush()
            while True:
                line = proc.stdout.readline()
                if not line:
                    raise CritError(f"{model}: {self.binary} closed its output before answering get_available_thinking_levels (timed out?)")
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "response" and data.get("command") == "get_available_thinking_levels":
                    if not data.get("success"):
                        raise CritError(f"{model}: could not get thinking levels: {data}")
                    levels = data.get("data", {}).get("levels", [])
                    return [level for level in LEVEL_ORDER if level in levels]
        finally:
            timer.cancel()
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def pinned(self, model, upstreams):
        if upstreams and not model.startswith("openrouter/"):
            raise CritError(f"{model}: @UPSTREAM only works for pi openrouter/ models")
        return f"{model}@{','.join(upstreams)}" if upstreams else model

    def finish(self, harness_dir, model, metrics):
        """An OpenRouter run: record the route (`metrics["extra"]["route"]`) and swap pi's catalog-price
        cost for what OpenRouter charged (pi's figure stays as `route.pi_cost_usd`; pi prices the
        calls at one rate whatever upstream served them). A pinned run served outside its `only`
        list gets a note."""
        route = read_route(harness_dir, model)
        if not route:
            return metrics
        only = {upstream_key(s) for s in route["requested"]["only"]} if route["requested"] else None
        outside = [s for s in route["served"] if upstream_key(s) not in only] if only else []
        notes = [f"served upstream outside requested only: {', '.join(outside)}"] if outside else []
        route["pi_cost_usd"] = metrics.get("cost_usd", 0.0)
        cost = route["cost_usd"] if route["cost_usd"] is not None else route["pi_cost_usd"]
        return {**metrics, "extra": {"route": route}, "cost_usd": cost, "notes": notes}

    def command(self, model, level, brief, session_dir):
        base, slugs = split_model_route(model)
        cmd = [
            self.binary,
            "-p",
            "--mode",
            "json",
            "--model",
            f"{base}:{level}",
            "--session-dir",
            str(session_dir),
            "-ne",
            "-ns",
            "-np",
            "-nc",
        ]
        if base.startswith("openrouter/"):
            cmd += ["-e", str(ROUTING_EXTENSION)]
        return cmd + [brief]

    def env(self, model=None, harness_dir=None):
        """Every OpenRouter run logs its upstreams and real cost to ART_CRIT_ROUTE_LOG; a pinned one
        (`MODEL@slug`) also gets ART_CRIT_OPENROUTER_ROUTING. Other models inherit art-crit's env."""
        if model is None or harness_dir is None:
            return None
        base, slugs = split_model_route(model)
        if not base.startswith("openrouter/"):
            return None
        env = {**os.environ, "ART_CRIT_ROUTE_LOG": str(Path(harness_dir) / "route.jsonl")}
        env.pop("ART_CRIT_OPENROUTER_ROUTING", None)
        if slugs:
            env["ART_CRIT_OPENROUTER_ROUTING"] = json.dumps({"only": slugs, "allow_fallbacks": False})
        return env

    def session_file(self, session_dir):
        matches = sorted(p for p in Path(session_dir).glob("*.jsonl") if p.name != "events.jsonl")  # events.jsonl = pi's stdout
        return matches[0] if matches else None


def parse_session(path):
    """Read a pi session file and return metrics + thinkingLevel + whether it ended in error.

    Returns a dict: {thinking_level, turns, tool_calls, tokens: {...}, cost_usd, ended_in_error,
    error_message}. Pure and testable: no subprocess, no filesystem beyond reading `path`.

    Tolerates a partial last line: this is also called on a session file that a running agent
    is still appending to (for live progress), so a line caught mid-write is simply skipped
    rather than raising.
    """
    thinking_level = None
    turns = 0
    tool_calls = 0
    tokens = {"input": 0, "output": 0, "reasoning": 0, "cacheRead": 0, "cacheWrite": 0}
    cost_usd = 0.0
    ended_in_error = False
    error_message = None

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # a line the writer hasn't finished flushing yet
            if entry.get("type") == "thinking_level_change":
                thinking_level = entry.get("thinkingLevel")
                continue
            if entry.get("type") != "message":
                continue
            msg = entry.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            turns += 1
            for block in msg.get("content") or []:
                if block.get("type") == "toolCall":
                    tool_calls += 1
            usage = msg.get("usage") or {}
            for key in tokens:
                tokens[key] += usage.get(key) or 0
            cost_usd += (usage.get("cost") or {}).get("total") or 0
            if msg.get("stopReason") == "error":
                ended_in_error = True
                error_message = msg.get("errorMessage") or error_message

    tokens["total"] = tokens["input"] + tokens["output"]
    return {
        "thinking_level": thinking_level,
        "turns": turns,
        "tool_calls": tool_calls,
        "tokens": tokens,
        "cost_usd": cost_usd,
        "ended_in_error": ended_in_error,
        "error_message": error_message,
    }


class ClaudeCode(Harness):
    """The `claude` CLI (Claude Code) harness. See SPEC.md "Harness interface".

    Each run is one direct agent: --safe-mode keeps the user's CLAUDE.md, memory, skills,
    plugins, hooks and MCP servers out of it (login still works), sub-agents are disallowed,
    and nothing is saved to the user's session history. The stdout stream-json is the session."""

    name = "claude-code"
    tag = "cc"
    # Models and effort levels (Claude Code has no command that lists them, so this mirrors the CLI's
    # own alias table + model catalog and has to be updated when they change). Aliases resolve to
    # these. A level the model doesn't take is silently clamped by the CLI (measured: `--effort xhigh`
    # on *-4-6 sends effort=high; on claude-haiku-4-5 --effort is ignored entirely, so it's not listed),
    # hence the trimmed lists. Levels from the catalog's capabilities, checked against the requests the
    # CLI actually sends.
    MODELS = {
        "claude-fable-5-1": ["low", "medium", "high", "xhigh", "max"],
        "claude-opus-5-5": ["low", "medium", "high", "xhigh", "max"],
        "claude-opus-5": ["low", "medium", "high", "xhigh", "max"],
        "claude-opus-4-8": ["low", "medium", "high", "xhigh", "max"],
        "claude-opus-4-7": ["low", "medium", "high", "xhigh", "max"],
        "claude-opus-4-6": ["low", "medium", "high", "max"],
        "claude-sonnet-5-5": ["low", "medium", "high", "xhigh", "max"],
        "claude-sonnet-5": ["low", "medium", "high", "xhigh", "max"],
        "claude-sonnet-4-6": ["low", "medium", "high", "max"],
        "claude-haiku-5-5": ["low", "medium", "high", "xhigh", "max"],
    }
    ALIASES = {"fable": "claude-fable-5-1", "opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
    # Only the core file and shell tools, like pi: no web, scheduling, messaging or skills, and no
    # sub-agents (each model x effort is one direct run).
    TOOLS = "Bash,Read,Write,Edit,Glob,Grep"
    NO_SUBAGENTS = "Agent,Task"

    def __init__(self, binary="claude"):
        self.binary = binary

    def version(self):
        try:
            r = subprocess.run([self.binary, "--version"], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise CritError(f"cannot run {self.binary} --version: {e}")
        if r.returncode != 0:
            raise CritError(f"{self.binary} --version failed: {r.stderr.strip()}")
        return r.stdout.strip().split()[0]  # "2.1.283 (Claude Code)" -> "2.1.283"

    def models(self):
        return [*self.MODELS, *self.ALIASES]

    def resolve(self, model):
        return self.ALIASES.get(model, model)

    def levels(self, model):
        return self.MODELS[self.resolve(model)]

    def display_model(self, model):
        return f"anthropic/{self.resolve(model)}"

    def command(self, model, level, brief, session_dir):
        return [
            self.binary, "-p",
            "--model", self.resolve(model),
            "--effort", level,
            "--output-format", "stream-json", "--verbose",
            "--safe-mode",
            "--permission-mode", "bypassPermissions",
            "--no-session-persistence",
            f"--tools={self.TOOLS}",
            f"--disallowed-tools={self.NO_SUBAGENTS}",
            "--disable-slash-commands",
            "--", brief,
        ]

    def env(self, model=None, harness_dir=None):
        # art-crit itself may be running inside Claude Code; don't let the agent think it's nested.
        return {k: v for k, v in os.environ.items() if k != "CLAUDECODE" and not k.startswith("CLAUDE_CODE_")}

    def session_file(self, session_dir):
        path = Path(session_dir) / "events.jsonl"
        return path if path.is_file() else None

    def session_entries(self, session_dir, brief, level):
        path = self.session_file(session_dir)
        return convert_claude_stream(read_jsonl(path), brief, level) if path else None

    def metrics(self, session_dir, level=None):
        path = self.session_file(session_dir)
        return claude_metrics(read_jsonl(path), level) if path else None


def add_tool_durations(entries):
    """Set `durationMs` on each toolResult message that lacks one: its entry's timestamp minus the
    timestamp of the assistant entry that made the call (pi stamps entries when they're finished).
    Tools called together share a start, so parallel ones are exact and sequential ones cumulative.
    The Claude Code conversion sets exact ones itself. Entries without usable timestamps are left
    alone. Returns `entries`."""
    called = {}
    for entry in entries or []:
        msg = entry.get("message") or {}
        if msg.get("role") == "assistant":
            for block in msg.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "toolCall":
                    called[block.get("id")] = entry.get("timestamp")
        elif msg.get("role") == "toolResult":
            if "durationMs" not in msg:
                _set_duration(msg, called.get(msg.get("toolCallId")), entry.get("timestamp"))
    return entries


def _set_duration(result, start_iso, end_iso):
    start, end = _ms(start_iso), _ms(end_iso)
    if start is not None and end is not None:
        result["durationMs"] = max(0, round(end - start))


def _ms(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000
    except (AttributeError, ValueError):
        return None


def read_jsonl(path):
    """Parsed JSON lines, skipping blank and partial (still being written) ones."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _claude_messages(events):
    """Assistant API messages from a stream-json event list, merged by message id (the stream
    can emit one event per content block, each repeating the message's usage)."""
    order, merged = [], {}
    for e in events:
        if e.get("type") != "assistant" or e.get("parent_tool_use_id"):
            continue
        msg = e.get("message") or {}
        mid = msg.get("id") or f"_{len(order)}"
        if mid not in merged:
            merged[mid] = {**msg, "content": []}
            order.append(mid)
        merged[mid]["content"] += msg.get("content") or []
        if msg.get("usage"):
            merged[mid]["usage"] = msg["usage"]
    return [merged[mid] for mid in order]


def _pi_usage(u):
    usage = {
        "input": u.get("input_tokens") or 0, "output": u.get("output_tokens") or 0,
        "cacheRead": u.get("cache_read_input_tokens") or 0, "cacheWrite": u.get("cache_creation_input_tokens") or 0,
    }
    usage["totalTokens"] = sum(usage.values())
    return usage


def _tool_content(content):
    """A tool_result's content -> pi content blocks: one text block, then one image block per image.
    An image (e.g. the agent reading a screenshot, often ~500 KB) is kept only as a small JPEG
    thumbnail, plus its original type and size; without ffmpeg it has no `data`."""
    blocks = content if isinstance(content, list) else [content]
    texts, images = [], []
    for c in blocks:
        if isinstance(c, dict) and c.get("type") == "image":
            images.append(_image_block(c.get("source") or {}))
        elif isinstance(c, dict) and c.get("type") == "text":
            texts.append(c.get("text", ""))
        elif isinstance(c, str):
            texts.append(c)
        elif c is not None:
            texts.append(json.dumps(c))
    return [{"type": "text", "text": "\n".join(texts)}, *images]


def _image_block(source):
    try:
        raw = base64.b64decode(source.get("data") or "", validate=True)
    except (binascii.Error, ValueError):
        raw = b""
    block = {"type": "image", "mimeType": "image/jpeg", "sourceMimeType": source.get("media_type"), "bytes": len(raw)}
    thumb = thumbnail(raw) if raw else None
    if thumb:
        block["data"] = base64.b64encode(thumb).decode()
    return block


def _tool_call(block, cwd):
    """A Claude Code tool_use block -> a pi toolCall. The tools the viewer knows (bash, write,
    edit, read) get pi's names and argument shapes, with paths made relative to the run dir."""
    name, args = block.get("name", ""), dict(block.get("input") or {})

    def rel(path):
        return path[len(cwd) + 1:] if cwd and isinstance(path, str) and path.startswith(cwd + "/") else path

    if name == "Bash":
        name, args = "bash", {"command": args.get("command", "")}
    elif name == "Write":
        name, args = "write", {"path": rel(args.get("file_path")), "content": args.get("content", "")}
    elif name == "Edit":
        name, args = "edit", {"path": rel(args.get("file_path")), "edits": [{"oldText": args.get("old_string", ""), "newText": args.get("new_string", "")}]}
    elif name == "MultiEdit":
        edits = [{"oldText": e.get("old_string", ""), "newText": e.get("new_string", "")} for e in args.get("edits") or []]
        name, args = "edit", {"path": rel(args.get("file_path")), "edits": edits}
    elif name == "Read":
        name, args = "read", {"path": rel(args.get("file_path")), **{k: v for k, v in args.items() if k in ("offset", "limit")}}
    return {"type": "toolCall", "id": block.get("id"), "name": name, "arguments": args}


def convert_claude_stream(events, brief, level):
    """Claude Code stream-json events -> pi-format session entries (see SPEC.md "Harness
    interface"): session, model and effort entries, the brief as the user message, assistant
    messages (text / thinking / toolCall, with usage) and toolResult messages. Messages carry
    their stream event's `timestamp`; the session and the brief get the first one in the stream."""
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    cwd = init.get("cwd") or ""
    start = _stamp({}, next((e.get("timestamp") for e in events if e.get("timestamp")), None))
    entries = [
        {"type": "session", "cwd": cwd, **start},
        {"type": "model_change", "provider": "anthropic", "modelId": init.get("model")},
        {"type": "thinking_level_change", "thinkingLevel": level},
        {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": brief}]}, **start},
    ]
    pending = list(_claude_messages(events))  # merged, in stream order: emitted at their first event
    called = {}  # tool_use id -> the timestamp of the event that carried it
    for e in events:
        if e.get("parent_tool_use_id"):
            continue
        if e.get("type") == "assistant":
            for b in (e.get("message") or {}).get("content") or []:
                if b.get("type") == "tool_use":
                    called[b.get("id")] = e.get("timestamp")
            if not pending or (pending[0].get("id") and pending[0]["id"] != (e.get("message") or {}).get("id")):
                continue  # a later event of a message already emitted
            msg = pending.pop(0)
            content = []
            for b in msg["content"]:
                if b.get("type") == "text":
                    content.append({"type": "text", "text": b.get("text", "")})
                elif b.get("type") == "thinking" and b.get("thinking"):  # print mode often omits the text
                    content.append({"type": "thinking", "thinking": b["thinking"]})
                elif b.get("type") == "tool_use":
                    content.append(_tool_call(b, cwd))
            entries.append(_stamp({"type": "message", "message": {
                "role": "assistant", "content": content, "usage": _pi_usage(msg.get("usage") or {}),
                "stopReason": msg.get("stop_reason"),
            }}, e.get("timestamp")))
        elif e.get("type") == "user":
            for b in (e.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    entries.append(_stamp({"type": "message", "message": {
                        "role": "toolResult", "toolCallId": b.get("tool_use_id"),
                        "content": _tool_content(b.get("content")), "isError": bool(b.get("is_error")),
                    }}, e.get("timestamp")))
                    _set_duration(entries[-1]["message"], called.get(b.get("tool_use_id")), e.get("timestamp"))
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result and result.get("is_error"):
        entries.append({"type": "message", "message": {
            "role": "assistant", "content": [{"type": "text", "text": _result_error(result)}], "stopReason": "error",
        }})
    return entries


def _stamp(entry, timestamp):
    """Adds pi's `timestamp` field to a session entry when the stream event had one."""
    if timestamp:
        entry["timestamp"] = timestamp
    return entry


def _result_error(result):
    return str(result.get("result") or ", ".join(result.get("errors") or []) or result.get("subtype") or "error")


def claude_metrics(events, level=None):
    """Metrics from a Claude Code stream (parse_session()'s shape). Turns and tool calls are counted
    over the top-level assistant API messages. Tokens come from the final result's usage (the
    per-message usage in the stream is a snapshot taken before the output is written, so it
    undercounts output); until the run ends they're summed from those snapshots. Reasoning =
    usage.output_tokens_details.thinking_tokens. Cost = total_cost_usd (Claude Code's API-price
    estimate), 0 until the run ends."""
    msgs = _claude_messages(events)
    tool_calls = sum(1 for m in msgs for b in m["content"] if b.get("type") == "tool_use")
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result and result.get("usage"):
        u = _pi_usage(result["usage"])
        reasoning = (result["usage"].get("output_tokens_details") or {}).get("thinking_tokens")
    else:
        u = {k: sum(_pi_usage(m.get("usage") or {})[k] for m in msgs) for k in ("input", "output", "cacheRead", "cacheWrite")}
        reasoning = None
    tokens = {"input": u["input"], "output": u["output"], "reasoning": reasoning, "cacheRead": u["cacheRead"], "cacheWrite": u["cacheWrite"]}
    tokens["total"] = tokens["input"] + tokens["output"]
    ended_in_error = bool(result and result.get("is_error"))
    return {
        "thinking_level": level,
        "turns": len(msgs),
        "tool_calls": tool_calls,
        "tokens": tokens,
        "cost_usd": (result or {}).get("total_cost_usd") or 0.0,
        "ended_in_error": ended_in_error,
        "error_message": _result_error(result)[:200] if ended_in_error else None,
    }


HARNESSES = {"pi": Pi, "claude-code": ClaudeCode}


def split_harness(spec):
    """'claude-code:claude-opus-5-5:high' -> ('claude-code', 'claude-opus-5-5:high'); no known
    harness prefix -> ('pi', spec)."""
    name, sep, rest = spec.partition(":")
    return (name, rest) if sep and name in HARNESSES else ("pi", spec)
