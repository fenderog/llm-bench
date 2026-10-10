# 0017. The run directory is the unit of work; the effort-run format is retired

- Status: Accepted
- Date: 2026-10-02
- Supersedes: the "input is an effort-run folder" clause of [0003](0003-repo-is-the-database.md) and the
  directory layout in [0009](0009-agents-run-as-local-processes.md).

## Context

`art-crit run` knew everything about a run (harness, model, level, kind, start time, metrics, state) but wrote it
in the `fe-model-effort-fanout/1` layout (one model dir per model holding every effort level, plus `wasm/<level>`,
`media/<level>`, `web/<level>` and `.harness/<level>`), only so that `art-crit import` could parse it back: the run id
from a folder-name regex, the kind by which output directory existed, the metrics from `data.json`. Session files were
copied *into* the agent's project and then skipped again when publishing and exporting. The grouping by model was a
historical artifact: nothing downstream used it. A container executor needs the opposite shape: mount one
directory, run one command, read one file back.

## Decision

- **One directory per run**: `<batch>/<run id>/` with `run.json` (the record, written by the runner), `work/` (the
  agent's working directory, and nothing else is written there), `harness/` (session, stdout, stderr, brief, route
  log, the converted transcript) and `output/` (what the kind made of the work).
- Run ids are assigned at plan time (`make_run_id(model, effort, started, harness_tag)`) and are the directory name.
  Two runs that resolve to one id are an error before anything starts. `batch.json` lists the ids and the agent states.
- **`art-crit import PATH`** publishes one run directory, or every run directory of a batch directory (clean +
  secret-scan, then move, then rebuild). It no longer reads effort-run folders: the only page that came from one
  (voxel-horse) is already published.
- Session files never sit in the project, so there is no list of session files to skip when publishing or when
  exporting a Godot project.
- `status.json` is folded into `run.json`; `source_dir` becomes `batch`.

## Alternatives considered

- **Keep the legacy folder as an input via a converter**: extra code and a fixture for a format nothing produces any more.
- **Keep the model-dir grouping and add `run.json` inside**: keeps the tag-collision check, `entries_by_model` and the
  folder-name parsing, and bakes the legacy shape into the executor contract.

## Consequences

- One path per concern: resume works per run directory, a run can be re-imported on its own, and a container can mount
  a single directory.
- Existing published runs were migrated once (`source_dir` → `batch`); batches written by older versions can't be resumed.
- Runs of the same model at different efforts are no longer grouped on disk; `ls <batch>` lists runs, not models.
