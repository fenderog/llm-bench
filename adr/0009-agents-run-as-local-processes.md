# 0009. Agents run as local processes, not in a VM

- Status: Accepted
- Recorded: 2026-09-28 (written after the fact from SPEC.md, DESIGN.md and AGENTS.md)

## Context

`art-crit run` starts many agents in parallel, one per model × effort level. The agents run shell commands the
model chooses, with permissions bypassed. They need Godot, python3, node, ffmpeg and the harness's login.

## Decision

- **Each agent is a subprocess on the owner's machine**:
  - Its working directory is an empty `<batch>/<run id>/work/` under `~/dev/art-crit-runs/`.
  - Its scratch files are in `<run id>/harness/`, outside the project, so it stays clean (layout: see 0017).
- `start_new_session=True` puts each agent in its own process group. The runner kills those groups itself on
  timeout and Ctrl-C (which doesn't reach them), and marks the runs `queued` for `--resume`.
- Parallelism uses threads plus subprocesses (`-j`, default 8). Godot exports run one at a time.
- The brief lists the tools that are available (`[run].tools`) instead of controlling what's installed.
- A real `art-crit run` costs money. Tests use a fake `pi`/`claude` first on `PATH`, and never call a real model.

## Alternatives considered

- **A VM or container per agent using the owner's image**: better isolation and reproducibility, but slower,
  more setup, and harness logins inside the VM. Kept open: only the "start one agent" step in `runner.run_agent`
  would change.
- **A hosted runner**: costs money, needs credentials in CI, and moves off the owner's machine.

## Consequences

- Fast and simple, but an agent has the owner's user permissions. Only run prompts and models you trust with
  your machine.
- The environment isn't pinned. Tool versions are whatever's on `PATH`, which under `uv run` means the venv's
  python3 first.
- The `live`/`interrupted` locking in `runner.execute` and `run_agent` exists because of the process-group
  handling. Keep it.
