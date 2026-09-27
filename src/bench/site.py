"""Regenerate results.json / page.json / pages.json from runs/*/run.json, and GC unreferenced
engines. Also `rm` and `list`, which both end by calling rebuild()."""

import json
import shutil
from datetime import datetime, timedelta, timezone

from .util import BenchError, effort_sort_key, title_from_slug


def _ended_at(run):
    started = datetime.strptime(run["started_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ms = (run.get("metrics") or {}).get("duration_ms") or 0
    return (started + timedelta(milliseconds=ms)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_thumb(runs):
    """The most recent run (by started_at, then effort order) that has a thumb."""
    for run in sorted(runs, key=effort_sort_key, reverse=True):
        if run.get("thumb"):
            return run
    return None


def rebuild(root):
    docs = root / "docs"
    data_dir = docs / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    referenced_engines = set()
    pages = []

    for page_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        runs = []
        runs_dir = page_dir / "runs"
        if runs_dir.is_dir():
            for run_dir in sorted(runs_dir.iterdir()):
                rj = run_dir / "run.json"
                if rj.is_file():
                    runs.append(json.loads(rj.read_text()))
        if not runs:
            shutil.rmtree(page_dir)
            continue

        runs.sort(key=effort_sort_key)
        (page_dir / "results.json").write_text(json.dumps(runs, indent=2) + "\n")
        for run in runs:
            game = run.get("game")
            if game and game.get("engine"):
                referenced_engines.add(game["engine"])

        slug = page_dir.name
        page_json_path = page_dir / "page.json"
        existing = json.loads(page_json_path.read_text()) if page_json_path.is_file() else {}
        page = {
            "slug": slug,
            "title": existing.get("title") or title_from_slug(slug),
            "prompt": existing.get("prompt", ""),
            "final_prompt": existing.get("final_prompt"),
            "created": existing.get("created") or min(r["started_at"] for r in runs),
            "updated": max(_ended_at(r) for r in runs),
        }
        page_json_path.write_text(json.dumps(page, indent=2) + "\n")

        thumb_run = _pick_thumb(runs)
        pages.append(
            {
                "slug": slug,
                "title": page["title"],
                "n_runs": len(runs),
                "models": sorted({r["model"] for r in runs}),
                "updated": page["updated"],
                "thumb": f"data/{slug}/runs/{thumb_run['id']}/thumb.png" if thumb_run else None,
            }
        )

    pages.sort(key=lambda p: p["updated"], reverse=True)
    (data_dir / "pages.json").write_text(json.dumps(pages, indent=2) + "\n")

    engines_dir = docs / "engines"
    if engines_dir.is_dir():
        for d in engines_dir.iterdir():
            if d.is_dir() and d.name not in referenced_engines:
                shutil.rmtree(d)


def cmd_rm(root, slug, run_id=None):
    page_dir = root / "docs" / "data" / slug
    if not page_dir.is_dir():
        raise BenchError(f"no such page: {slug}")
    if run_id is None:
        shutil.rmtree(page_dir)
        print(f"removed page {slug}")
    else:
        run_dir = page_dir / "runs" / run_id
        if not run_dir.is_dir():
            raise BenchError(f"no such run: {slug}/{run_id}")
        shutil.rmtree(run_dir)
        print(f"removed run {slug}/{run_id}")
    rebuild(root)
    return 0


def cmd_list(root):
    pages_json = root / "docs" / "data" / "pages.json"
    if not pages_json.is_file():
        print("no pages")
        return 0
    for p in json.loads(pages_json.read_text()):
        print(f"{p['slug']}\t{p['n_runs']} runs\tupdated {p['updated']}\t{', '.join(p['models'])}")
        results = json.loads((root / "docs" / "data" / p["slug"] / "results.json").read_text())
        for r in results:
            verified = {True: "yes", False: "no", None: "?"}[r["verified"]]
            print(f"  {r['id']}\t{r['effort']}\t{r['model']}\tverified={verified}")
    return 0
