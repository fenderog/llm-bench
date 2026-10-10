"""Serve docs/ like GitHub Pages: permissive CORS, correct .wasm/.pck types, no COOP/COEP.

Plus a local-only ranking API (GitHub Pages never has it, so the viewer only shows ranking
controls when served by `art-crit serve`):
  GET api/local                 -> {"rank": true}
  PUT api/rank?p=<slug>         body {"ranks": {"<run id>": 1, ...}}  (null/missing = unranked)
    -> writes docs/data/<slug>/ranking.json and rebuilds, so page.json carries each run's rank.
Writes need Content-Type: application/json (so another site can't send one without a CORS
preflight, which this server doesn't answer) and, when present, a same-host Origin."""

import functools
import http.server
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import site

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def save_ranking(docs_root, slug, ranks):
    """Validate and write data/<slug>/ranking.json, then rebuild. Returns an error string or None."""
    if not SLUG_RE.match(slug or ""):
        return "bad page slug"
    runs_dir = docs_root / "data" / slug / "runs"
    if not runs_dir.is_dir():
        return f"no such page: {slug}"
    if not isinstance(ranks, dict):
        return "ranks must be an object"
    run_ids = {p.name for p in runs_dir.iterdir() if (p / "run.json").is_file()}
    clean = {}
    for run_id, rank in ranks.items():
        if run_id not in run_ids:
            return f"no such run: {run_id}"
        if rank is None:
            continue
        if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= len(run_ids):
            return f"rank for {run_id} must be a whole number from 1 to {len(run_ids)}"
        clean[run_id] = rank
    ranking = {"ranks": dict(sorted(clean.items(), key=lambda kv: kv[1])),
               "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    (docs_root / "data" / slug / "ranking.json").write_text(json.dumps(ranking, indent=2) + "\n")
    site.rebuild(docs_root.parent)
    return None


class _Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def guess_type(self, path):
        p = str(path)
        if p.endswith(".wasm"):
            return "application/wasm"
        if p.endswith(".pck"):
            return "application/octet-stream"
        return super().guess_type(path)

    def _json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlsplit(self.path).path.endswith("/api/local"):
            return self._json(200, {"rank": True})
        return super().do_GET()

    def do_PUT(self):
        url = urlsplit(self.path)
        if not url.path.endswith("/api/rank"):
            return self._json(404, {"error": "not found"})
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            return self._json(403, {"error": "cross-origin write refused"})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self._json(415, {"error": "expected application/json"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"error": "bad JSON"})
        slug = parse_qs(url.query).get("p", [None])[0]
        error = save_ranking(Path(self.directory), slug, body.get("ranks") if isinstance(body, dict) else None)
        if error:
            return self._json(400, {"error": error})
        return self._json(200, {"ok": True})

    def log_message(self, fmt, *args):
        pass  # keep test/CLI output quiet


def build_server(docs_root, port=0):
    handler = functools.partial(_Handler, directory=str(docs_root))
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)


def serve_in_thread(docs_root, port=0):
    """Start serving in a daemon thread; return the server (caller shuts it down)."""
    server = build_server(docs_root, port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def serve_forever(docs_root, port):
    server = build_server(docs_root, port)
    print(f"serving {docs_root} at http://127.0.0.1:{server.server_address[1]}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
