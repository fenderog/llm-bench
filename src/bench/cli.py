"""bench: argparse wiring for import/list/rm/rebuild/serve/publish."""

import argparse
import subprocess
import sys
from pathlib import Path

from .harness import HARNESSES
from .importer import cmd_import
from .runner import cmd_models, cmd_run
from .serve import serve_forever
from .site import cmd_list, cmd_rm, rebuild
from .util import BenchError


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-C", "--root", default=".", type=Path, help="repo root (site is <root>/docs)")

    parser = argparse.ArgumentParser(prog="bench")
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", parents=[common], help="import an effort-run folder")
    imp.add_argument("effort_dir")
    imp.add_argument("-p", "--page", help="override the page slug")
    imp.add_argument("-t", "--title", help="override the page title")
    imp.add_argument("-r", "--redact", action="store_true", help="redact secret hits instead of aborting")
    imp.add_argument("-a", "--allow-threads", action="store_true", help="allow a threaded Godot export")
    imp.add_argument("-n", "--dry-run", action="store_true", help="do the work but write nothing to docs/")

    sub.add_parser("list", parents=[common], help="list pages and their runs")

    rm = sub.add_parser("rm", parents=[common], help="remove a run, or a whole page")
    rm.add_argument("slug")
    rm.add_argument("run_id", nargs="?")

    sub.add_parser("rebuild", parents=[common], help="regenerate page.json + pages.json")

    srv = sub.add_parser("serve", parents=[common], help="serve docs/ like GitHub Pages")
    srv.add_argument("-p", "--port", type=int, default=8000)

    pub = sub.add_parser("publish", parents=[common], help="git add docs && commit && push")
    pub.add_argument("-m", "--message")

    run = sub.add_parser("run", parents=[common], help="run agents locally, then import")
    run.add_argument("prompt", nargs="?", help="the task prompt")
    run.add_argument("-f", "--prompt-file", type=Path)
    run.add_argument("-m", "--model", dest="models", action="append", default=[], help="[claude-code:]MODEL[:LEVELS], repeatable (no prefix = pi)")
    run.add_argument("-s", "--set", dest="sets", action="append", default=[], help="a model set: a NAME from bench.toml [sets], or a FILE with one MODEL[:LEVELS] per line; repeatable, combines with -m")
    run.add_argument("-e", "--effort", help="default LEVELS for every model without a suffix")
    run.add_argument("-k", "--kind", choices=["godot", "media", "web"], help="what the agents produce (default: the page's kind, else godot)")
    run.add_argument("-p", "--page", help="page slug (default: from the prompt); an existing page with no PROMPT reuses its prompt")
    run.add_argument("-c", "--change-prompt", action="store_true", help="allow a different prompt for an existing page (replaces it for the whole page)")
    run.add_argument("-t", "--title", help="page title (default: from slug)")
    run.add_argument("-b", "--brief", type=Path, help="brief template file ({prompt} is substituted)")
    run.add_argument("-j", type=int, dest="parallel", help="max agents at once")
    run.add_argument("-T", "--timeout", help='per agent, e.g. "30m" (default [run].timeout or 30m)')
    run.add_argument("-y", "--yes", action="store_true", help="don't ask for confirmation")
    run.add_argument("-n", "--dry-run", action="store_true", help="print the plan and exit")
    run.add_argument("-P", "--publish", action="store_true", help="run `bench publish` after importing")
    run.add_argument("-r", "--resume", type=Path, help="finish an interrupted batch dir")

    models_p = sub.add_parser("models", parents=[common], help="models the harness can run")
    models_p.add_argument("search", nargs="?", help="also show effort levels for matching models")
    models_p.add_argument("-H", "--harness", default="pi", choices=sorted(HARNESSES), help="which agent program's models (default: pi)")

    return parser


def cmd_publish(root, message):
    def git(*args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)

    add = git("add", "docs")
    if add.returncode != 0:
        raise BenchError(f"git add failed: {add.stderr.strip()}")
    commit = git("commit", "-m", message or "bench publish")
    if commit.returncode != 0 and "nothing to commit" not in (commit.stdout + commit.stderr):
        raise BenchError(f"git commit failed: {commit.stderr.strip()}")
    push = git("push")
    if push.returncode != 0:
        raise BenchError(f"git push failed: {push.stderr.strip()}")
    print((commit.stdout + commit.stderr).strip() or "nothing to commit")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "import":
            return cmd_import(
                root,
                args.effort_dir,
                page=args.page,
                title=args.title,
                redact=args.redact,
                allow_threads=args.allow_threads,
                dry_run=args.dry_run,
            )
        if args.command == "list":
            return cmd_list(root)
        if args.command == "rm":
            return cmd_rm(root, args.slug, args.run_id)
        if args.command == "rebuild":
            rebuild(root)
            return 0
        if args.command == "serve":
            serve_forever(root / "docs", args.port)
            return 0
        if args.command == "publish":
            return cmd_publish(root, args.message)
        if args.command == "run":
            return cmd_run(
                root,
                prompt=args.prompt,
                prompt_file=args.prompt_file,
                model_specs=args.models,
                model_sets=args.sets,
                effort=args.effort,
                page=args.page,
                title=args.title,
                brief_file=args.brief,
                parallel=args.parallel,
                timeout=args.timeout,
                yes=args.yes,
                dry_run=args.dry_run,
                publish=args.publish,
                resume=args.resume,
                kind=args.kind,
                change_prompt=args.change_prompt,
            )
        if args.command == "models":
            return cmd_models(HARNESSES[args.harness](), args.search)
    except BenchError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 1
