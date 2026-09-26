"""bench serve: CORS, .wasm/.pck content types, and no COOP/COEP headers."""

import urllib.request

from bench.serve import serve_in_thread


def _get(url):
    with urllib.request.urlopen(url) as resp:
        return resp.status, resp.headers, resp.read()  # headers: case-insensitive email.message.Message


def test_serve_headers(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text("<html></html>")
    (docs / "game.wasm").write_bytes(b"\x00wasm")
    (docs / "game.pck").write_bytes(b"pck-bytes")

    server = serve_in_thread(docs, 0)
    try:
        port = server.server_address[1]
        base = f"http://127.0.0.1:{port}/"

        status, headers, body = _get(base + "game.wasm")
        assert status == 200
        assert headers["Content-Type"] == "application/wasm"
        assert headers["Access-Control-Allow-Origin"] == "*"
        assert "Cross-Origin-Opener-Policy" not in headers
        assert "Cross-Origin-Embedder-Policy" not in headers
        assert body == b"\x00wasm"

        status, headers, _ = _get(base + "game.pck")
        assert status == 200
        assert headers["Content-Type"] == "application/octet-stream"

        status, headers, _ = _get(base + "index.html")
        assert status == 200
        assert headers["Access-Control-Allow-Origin"] == "*"
    finally:
        server.shutdown()
        server.server_close()
