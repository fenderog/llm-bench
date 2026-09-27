"""bench import: turn an effort-run folder into one run per effort level on the site."""

import json
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from types import SimpleNamespace

from . import clean, godot, site
from .util import BenchError, iso_from_ms, make_run_id, mask, parse_folder

# level-dir file -> (path under the run dir, how to clean it)
SESSION_FILES = {
    "conversation.json": ("session/conversation.json", "json"),
    "events.jsonl": ("session/events.jsonl", "jsonl"),
    "status.json": ("session/status.json", "json"),
    "output.md": ("session/output.md", "text"),
}
# Files under <level>/ that are never part of the copied source (session files, plus editor cache).
SOURCE_SKIP = {
    "session.jsonl",
    "conversation.json",
    "events.jsonl",
    "status.json",
    "output.md",
    "data.json",
    ".DS_Store",
    ".godot",
}


def load_rewrites(root):
    """Home dir -> '~', plus any extra [clean].rewrite entries from <root>/bench.toml."""
    rewrites = [(str(Path.home()), "~")]
    cfg_path = root / "bench.toml"
    if cfg_path.is_file():
        cfg = tomllib.loads(cfg_path.read_text())
        rewrites += list(cfg.get("clean", {}).get("rewrite", {}).items())
    return sorted(rewrites, key=lambda kv: -len(kv[0]))


def write_cleaned(src, dest, kind, rewrites, redact, batch):
    """Clean src's text per `kind` and write it to dest, tracking rewrites/hits on `batch`."""
    try:
        raw = src.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
        return
    if kind == "json":
        text, n = clean.clean_json(raw, rewrites)
    elif kind == "jsonl":
        text, n = clean.clean_jsonl(raw, rewrites)
    else:
        text, n = clean.clean_plain(raw, rewrites)
    batch.rewritten += n
    if redact:
        text, k = clean.redact_secrets(text)
        batch.redacted += k
    else:
        rel = dest.relative_to(batch.run_dir)
        for line, secret in clean.scan_secrets(text):
            batch.hits.append((batch.run_id, rel.as_posix(), line, secret))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")


def stage_session(level_dir, run_dir, rewrites, redact, batch):
    if not level_dir.is_dir():
        return None
    session = {}
    for fname, (relpath, kind) in SESSION_FILES.items():
        src = level_dir / fname
        if not src.is_file():
            continue
        write_cleaned(src, run_dir / relpath, kind, rewrites, redact, batch)
        key = relpath.split("/")[1].split(".")[0]  # "session/conversation.json" -> "conversation"
        session[key] = relpath
    return session or None


def stage_source(level_dir, run_dir, rewrites, redact, batch):
    if not level_dir.is_dir():
        return None
    files = []
    for src in sorted(level_dir.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(level_dir)
        if rel.parts[0] in SOURCE_SKIP or src.name in SOURCE_SKIP:
            continue
        write_cleaned(src, run_dir / "source" / rel, "text", rewrites, redact, batch)
        files.append(rel.as_posix())
    return {"root": "source/", "files": sorted(files)} if files else None


def stage_run(effort_dir, level, run_data, slug, tmp_root, docs_root, rewrites, redact, allow_threads, known_engines):
    run_id = make_run_id(run_data["model"], level, effort_dir.name)
    run_dir = tmp_root / run_id
    run_dir.mkdir(parents=True)
    batch = SimpleNamespace(rewritten=0, redacted=0, hits=[], run_dir=run_dir, run_id=run_id)

    level_dir = effort_dir / level
    wasm_dir = effort_dir / "wasm" / level

    game = engine_sha = engine_files = thumb = verified = None
    if wasm_dir.is_dir():
        game, engine_sha, engine_files = godot.stage_game(
            wasm_dir, run_dir / "game", docs_root, slug, run_id, allow_threads, known_engines
        )
        thumb = godot.stage_thumb(wasm_dir, run_dir)
        verified = godot.read_verified(wasm_dir)

    session = stage_session(level_dir, run_dir, rewrites, redact, batch)
    source = stage_source(level_dir, run_dir, rewrites, redact, batch)

    tokens = run_data.get("tokens", {})
    run_json = {
        "id": run_id,
        "page": slug,
        "model": run_data["model"],
        "effort": level,
        "started_at": iso_from_ms(run_data["startedAt"]),
        "source_dir": effort_dir.name,
        "verified": verified,
        "metrics": {
            "duration_ms": run_data.get("durationMs"),
            "cost_usd": run_data.get("costUsd"),
            "tool_calls": run_data.get("toolCalls"),
            "turns": run_data.get("turns"),
            "tokens_total": tokens.get("total"),
            "tokens_input": tokens.get("input"),
            "tokens_output": tokens.get("output"),
            "tokens_reasoning": tokens.get("reasoning"),
            "tokens_cache_read": tokens.get("cacheRead"),
        },
        "thumb": thumb,
        "game": game,
        "session": session,
        "source": source,
    }
    (run_dir / "run.json").write_text(json.dumps(run_json, indent=2) + "\n")
    n_bytes = sum(p.stat().st_size for p in run_dir.rglob("*") if p.is_file())
    return SimpleNamespace(
        run_id=run_id,
        run_dir=run_dir,
        engine_sha=engine_sha,
        engine_files=engine_files,
        bytes=n_bytes,
        rewritten=batch.rewritten,
        redacted=batch.redacted,
        hits=batch.hits,
    )


def cmd_import(root, effort_dir, page=None, redact=False, allow_threads=False, dry_run=False):
    effort_dir = Path(effort_dir).resolve()
    if not effort_dir.is_dir():
        raise BenchError(f"not a directory: {effort_dir}")
    data_path = effort_dir / "data.json"
    if not data_path.is_file():
        raise BenchError(f"missing data.json: {effort_dir}")
    data = json.loads(data_path.read_text())

    _, _, folder_slug = parse_folder(effort_dir.name)
    slug = page or folder_slug
    docs_root = root / "docs"
    (docs_root / "data").mkdir(parents=True, exist_ok=True)
    (docs_root / "engines").mkdir(parents=True, exist_ok=True)
    rewrites = load_rewrites(root)
    # The originating prompt (not the brief given to subagents); cleaned and scanned like everything else.
    prompt_path = effort_dir / "prompt.md"
    prompt = clean.rewrite_text(prompt_path.read_text().strip(), rewrites)[0] if prompt_path.is_file() else None
    if prompt and redact:
        prompt = clean.redact_secrets(prompt)[0]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        results = []
        known_engines = set()
        for level, run_data in data.get("runs", {}).items():
            r = stage_run(effort_dir, level, run_data, slug, tmp_root, docs_root, rewrites, redact, allow_threads, known_engines)
            if r.engine_files is not None:
                known_engines.add(r.engine_sha)
            results.append(r)

        all_hits = [h for r in results for h in r.hits]
        if prompt and not redact:
            all_hits += [("page", "prompt.md", line, secret) for line, secret in clean.scan_secrets(prompt)]
        if all_hits and not redact:
            for run_id, rel, line, secret in all_hits:
                print(f"secret: {run_id}/{rel}:{line}: {mask(secret)}", file=sys.stderr)
            raise BenchError(f"{len(all_hits)} possible secret(s) found before writing anything; use --redact to continue")

        for r in results:
            status = "n/a" if r.engine_sha is None else ("stored" if r.engine_files is not None else "reused")
            tag = "[dry-run] " if dry_run else ""
            engine_note = f" {r.engine_sha}" if r.engine_sha else ""
            secret_note = r.redacted if redact else len(r.hits)
            print(
                f"{tag}{r.run_id}: engine {status}{engine_note}, {r.bytes} bytes, "
                f"{r.rewritten} paths rewritten, {secret_note} secret hits"
            )

        if dry_run:
            return 0

        for r in results:
            if r.engine_sha and r.engine_files is not None:
                engine_dir = docs_root / "engines" / r.engine_sha
                if not engine_dir.is_dir():
                    engine_dir.mkdir(parents=True)
                    for name, content in r.engine_files.items():
                        (engine_dir / name).write_bytes(content)
            target = docs_root / "data" / slug / "runs" / r.run_id
            if target.is_dir():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(r.run_dir), str(target))

        page_path = docs_root / "data" / slug / "page.json"
        page_json = json.loads(page_path.read_text()) if page_path.is_file() else {"slug": slug}
        if prompt:
            page_json["prompt"] = prompt
        page_path.write_text(json.dumps(page_json, indent=2) + "\n")

        site.rebuild(root)
    return 0
