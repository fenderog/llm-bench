"""The agent-program interface (`bench run` drives one of these), and Pi, the only
implementation so far. Also the pure session-file parser: metrics + state (see SPEC.md
"Metrics" and "Harness interface").
"""

import json
import subprocess
import threading
from pathlib import Path

from .util import LEVEL_INDEX, LEVEL_ORDER, BenchError


class Harness:
    """One per agent program."""

    name = "harness"

    def version(self):
        raise NotImplementedError

    def models(self):
        raise NotImplementedError

    def levels(self, model):
        raise NotImplementedError

    def command(self, model, level, brief, session_dir):
        raise NotImplementedError

    def session_file(self, session_dir):
        raise NotImplementedError


class Pi(Harness):
    """The `pi` CLI harness. See SPEC.md "Harness interface"."""

    name = "pi"

    def __init__(self, binary="pi"):
        self.binary = binary

    def version(self):
        try:
            r = subprocess.run([self.binary, "--version"], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise BenchError(f"cannot run {self.binary} --version: {e}")
        if r.returncode != 0:
            raise BenchError(f"{self.binary} --version failed: {r.stderr.strip()}")
        return r.stdout.strip().splitlines()[0].strip()

    def models(self):
        r = subprocess.run([self.binary, "--list-models"], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise BenchError(f"{self.binary} --list-models failed: {r.stderr.strip()}")
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
            raise BenchError(f"cannot run {self.binary}: {e}")
        timer = threading.Timer(30, proc.kill)
        timer.start()
        try:
            proc.stdin.write('{"type":"get_available_thinking_levels"}\n')
            proc.stdin.flush()
            while True:
                line = proc.stdout.readline()
                if not line:
                    raise BenchError(f"{model}: {self.binary} closed its output before answering get_available_thinking_levels (timed out?)")
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "response" and data.get("command") == "get_available_thinking_levels":
                    if not data.get("success"):
                        raise BenchError(f"{model}: could not get thinking levels: {data}")
                    levels = data.get("data", {}).get("levels", [])
                    return [level for level in LEVEL_ORDER if level in levels]
        finally:
            timer.cancel()
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def command(self, model, level, brief, session_dir):
        return [
            self.binary,
            "-p",
            "--mode",
            "json",
            "--model",
            f"{model}:{level}",
            "--session-dir",
            str(session_dir),
            "-ne",
            "-ns",
            "-np",
            "-nc",
            brief,
        ]

    def session_file(self, session_dir):
        matches = sorted(Path(session_dir).glob("*.jsonl"))
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
