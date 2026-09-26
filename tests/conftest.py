"""Synthetic effort-run fixture: two effort levels, tiny fake Godot engine files, a real
Godot index.html template, and small session files with the sensitive shapes the cleaning
rules must strip. Built at runtime (not committed) so nothing under a real home dir, or any
real session content, ends up in this public repo.
"""

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
GODOT_INDEX_HTML = (FIXTURES / "godot_index.html").read_text()

DEFAULT_LEVELS = ["low", "high"]
ENGINE_BYTES = {
    "index.wasm": b"FAKE-WASM-BYTES-0001",
    "index.js": b"FAKE-JS-BYTES-0001",
    "index.audio.worklet.js": b"FAKE-AUDIO-WORKLET-0001",
    "index.audio.position.worklet.js": b"FAKE-AUDIO-POSITION-WORKLET-0001",
}


def _write_conversation(path, home, secret=None):
    thinking_sig = json.dumps({"id": "rs_1", "type": "reasoning", "encrypted_content": "gAAAAA-secret-blob-not-real"})
    text = f"Working in {home}/effort-runs/x now."
    if secret:
        text += f" token={secret}"
    convo = [
        {"type": "session", "id": "s1", "timestamp": "2026-09-26T07:12:42.000Z", "cwd": f"{home}/effort-runs/x"},
        {
            "type": "message",
            "id": "m1",
            "parentId": "s1",
            "pid": 4242,
            "sessionId": "sess-xyz",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "plan", "thinkingSignature": thinking_sig},
                    {"type": "text", "text": text},
                ],
            },
        },
    ]
    path.write_text(json.dumps(convo, indent=2))


def _write_events(path, home):
    lines = [
        {"type": "agent_start", "cwd": f"{home}/effort-runs/x", "pid": 4242},
        {"type": "tool_execution_start", "toolCallId": "t1", "ts": 1},
        {"type": "tool_execution_end", "toolCallId": "t1", "ts": 2},
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")


def _write_status(path, home):
    status = {
        "runId": "r1",
        "pid": 4242,
        "cwd": f"{home}/effort-runs/x",
        "sessionId": "sess-xyz",
        "sessionFile": f"{home}/.pi/sessions/x.jsonl",
        "sessionRoot": f"{home}/.pi",
        "completionOwnerId": "owner-1",
        "launchContractDigest": "deadbeef",
        "state": "complete",
    }
    path.write_text(json.dumps(status, indent=2))


def make_effort_run(base, folder_name="2026-09-26-001158-gpt6sol-voxel-horse", levels=None, threads=False, secret=None):
    """Build a synthetic effort-run folder under `base`, matching fe-model-effort-fanout/1."""
    levels = levels if levels is not None else DEFAULT_LEVELS
    home = str(Path.home())
    root = base / folder_name
    root.mkdir(parents=True)
    (root / "prompt.md").write_text("draw a running horse")
    (root / "conversation.json").write_text(json.dumps({"type": "orchestrator"}))  # orchestrator-level: ignored

    runs = {}
    started = 1790406762000
    for i, level in enumerate(levels):
        level_dir = root / level
        (level_dir / "scenes").mkdir(parents=True)
        (level_dir / "scripts").mkdir(parents=True)
        (level_dir / "project.godot").write_text("config_version=5\n")
        (level_dir / "README.md").write_text(f"# {level} run\nbuilt from {home}\n")
        (level_dir / "export_presets.cfg").write_text("[preset.0]\nname=\"Web\"\n")
        (level_dir / "scenes" / "main.tscn").write_text('[gd_scene load_steps=1 format=3]\n')
        (level_dir / "scripts" / "main.gd").write_text("extends Node\nfunc _ready():\n\tpass\n")
        (level_dir / "scripts" / "main.gd.uid").write_text("uid://abc123\n")
        _write_conversation(level_dir / "conversation.json", home, secret=secret if level == levels[0] else None)
        (level_dir / "session.jsonl").write_text("{}\n")  # identical copy of conversation.json: must be skipped
        _write_events(level_dir / "events.jsonl", home)
        _write_status(level_dir / "status.json", home)
        (level_dir / "output.md").write_text(f"Ran the {level} task from {home}/effort-runs.\n")
        (level_dir / "data.json").write_text("{}")
        (level_dir / ".DS_Store").write_bytes(b"\x00\x00")
        cache_dir = level_dir / ".godot" / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "whatever.tmp").write_text("editor cache junk, never copied")

        wasm_dir = root / "wasm" / level
        wasm_dir.mkdir(parents=True)
        for name, content in ENGINE_BYTES.items():
            (wasm_dir / name).write_bytes(content)
        (wasm_dir / "index.pck").write_bytes(b"PCK-DATA")
        (wasm_dir / "index.png").write_bytes(b"PNG-DATA")
        (wasm_dir / "index.icon.png").write_bytes(b"ICON-DATA")
        (wasm_dir / "index.apple-touch-icon.png").write_bytes(b"TOUCH-DATA")
        html = GODOT_INDEX_HTML.replace(
            "const GODOT_THREADS_ENABLED = false;",
            f"const GODOT_THREADS_ENABLED = {'true' if threads else 'false'};",
        )
        (wasm_dir / "index.html").write_text(html)
        (wasm_dir / "export-manifest.json").write_text(
            json.dumps({"threads": threads, "godot": "4.7.2.stable.official.ed1daf0bf"})
        )
        verify_dir = wasm_dir / "verification"
        verify_dir.mkdir()
        (verify_dir / "frame-1.png").write_bytes(b"FRAME-1-DATA")
        (verify_dir / "verify-report.json").write_text(json.dumps({"ok": True}))

        runs[level] = {
            "level": level,
            "model": "openai-codex/gpt-6-sol",
            "thinkingLevel": level,
            "startedAt": started,
            "endedAt": started + 1000 + i * 500,
            "durationMs": 1000 + i * 500,
            "costUsd": 0.01 * (i + 1),
            "toolCalls": 2 + i,
            "turns": 2 + i,
            "tokens": {
                "input": 100 * (i + 1),
                "output": 40 * (i + 1),
                "total": 140 * (i + 1),
                "reasoning": 5 * (i + 1),
                "cacheRead": 10 * (i + 1),
                "cacheWrite": 0,
            },
        }

    (root / "data.json").write_text(json.dumps({"schema": "fe-model-effort-fanout/1", "runs": runs}, indent=2))
    return root


@pytest.fixture
def effort_run_factory(tmp_path):
    def factory(**kwargs):
        return make_effort_run(tmp_path, **kwargs)

    return factory


@pytest.fixture
def effort_run(effort_run_factory):
    return effort_run_factory()


@pytest.fixture
def bench_root(tmp_path):
    root = tmp_path / "site"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / ".nojekyll").touch()
    return root
