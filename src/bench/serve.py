"""Serve docs/ like GitHub Pages: permissive CORS, correct .wasm/.pck types, no COOP/COEP."""

import functools
import http.server
import threading


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
