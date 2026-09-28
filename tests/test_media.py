"""media.finalize: checking and normalizing the files a media run left in ./output/.
Inputs are generated with ffmpeg, so the module is skipped without it."""

import json
import shutil
import subprocess

import pytest

from bench import media

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="needs ffmpeg")


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True)


@pytest.fixture
def out(tmp_path):
    (tmp_path / "lvl" / "output").mkdir(parents=True)
    return tmp_path / "lvl" / "output"


def finalize(out):
    return media.finalize(out.parent, out.parent.parent / "media")


def test_valid_image_svg_and_video(out):
    ffmpeg("-f", "lavfi", "-i", "testsrc=size=64x48", "-frames:v", "1", out / "a.png")
    (out / "b.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="30px" height="20"/>')
    ffmpeg("-f", "lavfi", "-i", "testsrc=size=160x120:rate=10", "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", out / "c.mp4")
    m = finalize(out)
    assert m["ok"] and not m["errors"]
    a, b, c = m["items"]
    assert (a["type"], a["width"], a["height"]) == ("image", 64, 48)
    assert (b["type"], b["width"], b["height"]) == ("image", 30, 20)
    assert c["type"] == "video" and not c["transcoded"] and c["poster"] == "c.poster.jpg"
    written = out.parent.parent / "media"
    assert json.loads((written / "manifest.json").read_text()) == m
    assert {p.name for p in written.iterdir()} == {"a.png", "b.svg", "c.mp4", "c.poster.jpg", "manifest.json"}


def test_long_webm_is_trimmed_and_reencoded_to_mp4(out):
    ffmpeg("-f", "lavfi", "-i", "testsrc=size=320x240:rate=10", "-t", "12", out / "clip.webm")
    [item] = finalize(out)["items"]
    assert item["file"] == "clip.mp4" and item["transcoded"] and item["trimmed"]
    assert item["duration_s"] <= media.MAX_VIDEO_S
    info = media.probe(out.parent.parent / "media" / "clip.mp4")
    assert info["codec"] == "h264" and info["duration"] <= media.MAX_VIDEO_S + 0.1


def test_bad_files_become_errors_and_ok_is_false(out):
    (out / "fake.png").write_bytes(b"not a png")
    (out / "notes.txt").write_text("hello")
    (out / "broken.svg").write_text("<svg")
    m = finalize(out)
    assert not m["ok"] and m["items"] == []
    assert m["errors"] == ["broken.svg: not a valid SVG", "fake.png: not a readable image", "notes.txt: unsupported file type"]


def test_empty_output_and_too_many_files(out, monkeypatch):
    assert finalize(out)["errors"] == ["no files in ./output/"]
    monkeypatch.setattr(media, "MAX_FILES", 2)
    for name in "abc":
        (out / f"{name}.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>')
    m = finalize(out)
    assert len(m["items"]) == 2 and "only the first 2" in m["errors"][0]


def test_oversized_png_becomes_jpeg(out, monkeypatch):
    ffmpeg("-f", "lavfi", "-i", "mandelbrot=s=320x240", "-frames:v", "1", out / "big.png")  # ~66 KB png, ~23 KB jpeg
    monkeypatch.setattr(media, "MAX_BYTES", 40_000)
    [item] = finalize(out)["items"]
    assert item["file"] == "big.jpg" and item["width"] == 320 and item["bytes"] <= 40_000


def test_name_collisions_are_reported_not_overwritten(out):
    ffmpeg("-f", "lavfi", "-i", "testsrc=size=160x120:rate=10", "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", out / "x.mp4")
    ffmpeg("-f", "lavfi", "-i", "testsrc=size=160x120:rate=10", "-t", "1", out / "x.webm")
    m = finalize(out)
    assert [i["file"] for i in m["items"]] == ["x.mp4"]
    assert m["errors"] == ["x.webm: skipped, another output is already named x.mp4"]
