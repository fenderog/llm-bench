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


# --- local ranking API ---------------------------------------------------------------------------

import json
import shutil
import urllib.error
from pathlib import Path

import pytest

from bench.cli import main

FIXTURE_DATA = Path(__file__).parent / "fixtures/site/data"
LOW, HIGH = "model-x-low-20260101-000000", "model-x-high-20260101-001000"


@pytest.fixture
def served(tmp_path):
    docs = tmp_path / "site" / "docs"
    shutil.copytree(FIXTURE_DATA, docs / "data")
    server = serve_in_thread(docs, 0)
    yield docs, f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()
    server.server_close()


def _put(url, body, headers=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="PUT",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_api_local_says_ranking_is_available(served):
    _, base = served
    status, _, body = _get(base + "api/local")
    assert status == 200 and json.loads(body) == {"rank": True}


def test_saving_a_ranking_writes_it_and_rebuilds(served):
    docs, base = served
    status, body = _put(base + "api/rank?p=demo", {"ranks": {HIGH: 1, LOW: 2}})
    assert (status, body) == (200, {"ok": True})
    ranking = json.loads((docs / "data/demo/ranking.json").read_text())
    assert ranking["ranks"] == {HIGH: 1, LOW: 2}
    ranks = {r["id"]: r["rank"] for r in json.loads((docs / "data/demo/results.json").read_text())}
    assert ranks == {HIGH: 1, LOW: 2, "model-x-medium-20260101-000500": None}

    _put(base + "api/rank?p=demo", {"ranks": {HIGH: 1, LOW: None}})  # null = unranked
    assert json.loads((docs / "data/demo/ranking.json").read_text())["ranks"] == {HIGH: 1}


@pytest.mark.parametrize("query, ranks, error", [
    ("p=../../etc", {}, "bad page slug"),
    ("p=nope", {}, "no such page"),
    ("p=demo", {"not-a-run": 1}, "no such run"),
    ("p=demo", {HIGH: 0}, "whole number from 1 to 3"),
    ("p=demo", {HIGH: 4}, "whole number from 1 to 3"),
    ("p=demo", {HIGH: "1"}, "whole number"),
])
def test_bad_rankings_are_refused(served, query, ranks, error):
    docs, base = served
    status, body = _put(base + f"api/rank?{query}", {"ranks": ranks})
    assert status == 400 and error in body["error"]
    assert not (docs / "data/demo/ranking.json").exists()


def test_cross_site_writes_are_refused(served):
    docs, base = served
    status, _ = _put(base + "api/rank?p=demo", {"ranks": {HIGH: 1}}, {"Origin": "https://evil.example"})
    assert status == 403
    req = urllib.request.Request(base + "api/rank?p=demo", data=b'{"ranks":{}}', method="PUT", headers={"Content-Type": "text/plain"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 415
    assert not (docs / "data/demo/ranking.json").exists()


def test_rm_drops_the_removed_run_from_the_ranking(served):
    docs, base = served
    _put(base + "api/rank?p=demo", {"ranks": {HIGH: 1, LOW: 2}})
    assert main(["rm", "demo", LOW, "--root", str(docs.parent)]) == 0
    assert json.loads((docs / "data/demo/ranking.json").read_text())["ranks"] == {HIGH: 1}
