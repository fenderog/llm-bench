"""bench: argparse wiring for import/list/rm/rebuild/serve/publish."""

import argparse
import subprocess
import sys
from pathlib import Path

from .importer import cmd_import
from .serve import serve_forever
from .site import cmd_list, cmd_rm, rebuild
from .util import BenchError


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=".", type=Path, help="repo root (site is <root>/docs)")

    parser = argparse.ArgumentParser(prog="bench")
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", parents=[common], help="import an effort-run folder")
    imp.add_argument("effort_dir")
    imp.add_argument("--page", help="override the page slug")
    imp.add_argument("--redact", action="store_true", help="redact secret hits instead of aborting")
    imp.add_argument("--allow-threads", action="store_true", help="allow a threaded Godot export")
    imp.add_argument("--dry-run", action="store_true", help="do the work but write nothing to docs/")

    sub.add_parser("list", parents=[common], help="list pages and their runs")

    rm = sub.add_parser("rm", parents=[common], help="remove a run, or a whole page")
    rm.add_argument("slug")
    rm.add_argument("run_id", nargs="?")

    sub.add_parser("rebuild", parents=[common], help="regenerate results.json + pages.json")

    srv = sub.add_parser("serve", parents=[common], help="serve docs/ like GitHub Pages")
    srv.add_argument("--port", type=int, default=8000)

    pub = sub.add_parser("publish", parents=[common], help="git add docs && commit && push")
    pub.add_argument("-m", "--message")

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
    except BenchError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 1
