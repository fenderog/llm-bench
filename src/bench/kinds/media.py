"""The `media` kind: check and normalize the image/video files an agent saved in work/output/.
See SPEC.md "bench run" step 6. Uses ffmpeg/ffprobe (checked for before a media batch starts)."""

import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from . import Kind, Staged

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov"}
SVG_EXT = ".svg"
MAX_FILES = 8
MAX_BYTES = 2 * 1024 * 1024
MAX_VIDEO_S = 10
VIDEO_CRFS = (26, 32, 38)  # tried in order until the re-encoded video fits MAX_BYTES


def probe(path):
    """ffprobe -> {"width", "height", "codec", "pix_fmt", "duration"} of the first video stream, or None."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width,height,codec_name,pix_fmt:format=duration,format_name", "-of", "json", str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    data = json.loads(r.stdout or "{}")
    streams = data.get("streams") or []
    if not streams or not streams[0].get("width"):
        return None
    s, fmt = streams[0], data.get("format") or {}
    duration = fmt.get("duration")
    return {
        "width": s["width"], "height": s["height"], "codec": s.get("codec_name"), "pix_fmt": s.get("pix_fmt"),
        "format": fmt.get("format_name", ""), "duration": float(duration) if duration not in (None, "N/A") else None,
    }


def thumbnail(raw, width=320):
    """Image bytes -> a small JPEG (at most `width` px wide), or None when ffmpeg is missing or fails."""
    if not shutil.which("ffmpeg"):
        return None
    cmd = ["ffmpeg", "-v", "error", "-i", "pipe:0", "-vf", f"scale='min({width},iw)':-2", "-frames:v", "1",
           "-q:v", "6", "-f", "image2pipe", "-c:v", "mjpeg", "pipe:1"]
    try:
        r = subprocess.run(cmd, input=raw, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 and r.stdout else None


def _ffmpeg(*args):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True, timeout=600)
    return r.returncode == 0


def svg_size(path):
    """(width, height) from the svg's width/height attributes or viewBox; None if it isn't an SVG."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    if root.tag.rsplit("}", 1)[-1] != "svg":
        return None

    def num(v):
        try:
            return round(float(str(v).removesuffix("px")))
        except (TypeError, ValueError):
            return None

    w, h = num(root.get("width")), num(root.get("height"))
    box = (root.get("viewBox") or "").replace(",", " ").split()
    if (w is None or h is None) and len(box) == 4:
        w, h = w or num(box[2]), h or num(box[3])
    return w, h


def do_image(src, dest_dir, name):
    info = probe(src)
    if info is None:
        return None, f"{name}: not a readable image"
    dest = dest_dir / name
    if src.stat().st_size > MAX_BYTES and src.suffix.lower() != ".gif":
        # Too big: re-encode as JPEG (always available in ffmpeg; WebP often isn't). Loses transparency.
        dest = dest.with_suffix(".jpg")
        if dest.exists():
            return None, f"{name}: skipped, another output is already named {dest.name}"
        if not _ffmpeg("-i", str(src), "-q:v", "3", str(dest)) or dest.stat().st_size > MAX_BYTES:
            dest.unlink(missing_ok=True)
            return None, f"{name}: larger than 2 MB, even as JPEG"
    elif src.stat().st_size > MAX_BYTES:
        return None, f"{name}: larger than 2 MB"
    else:
        shutil.copy(src, dest)
    return {"type": "image", "file": dest.name, "width": info["width"], "height": info["height"], "bytes": dest.stat().st_size}, None


def do_svg(src, dest_dir, name):
    size = svg_size(src)
    if size is None:
        return None, f"{name}: not a valid SVG"
    if src.stat().st_size > MAX_BYTES:
        return None, f"{name}: larger than 2 MB"
    shutil.copy(src, dest_dir / name)
    return {"type": "image", "file": name, "width": size[0], "height": size[1], "bytes": src.stat().st_size}, None


def do_video(src, dest_dir, name):
    info = probe(src)
    if info is None or not info["duration"]:
        return None, f"{name}: not a readable video"
    trimmed = info["duration"] > MAX_VIDEO_S + 0.05
    playable = "mp4" in info["format"] and info["codec"] == "h264" and info["pix_fmt"] == "yuv420p"
    dest = dest_dir / (Path(name).stem + ".mp4")
    if playable and not trimmed and src.stat().st_size <= MAX_BYTES:
        shutil.copy(src, dest)
        transcoded = False
    else:
        for crf in VIDEO_CRFS:
            ok = _ffmpeg("-i", str(src), "-t", str(MAX_VIDEO_S), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                         "-crf", str(crf), "-preset", "medium", "-vf", "scale=trunc(min(1280\\,iw)/2)*2:-2",
                         "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(dest))
            if not ok:
                dest.unlink(missing_ok=True)
                return None, f"{name}: ffmpeg could not re-encode it"
            if dest.stat().st_size <= MAX_BYTES:
                break
        else:
            dest.unlink(missing_ok=True)
            return None, f"{name}: larger than 2 MB even after re-encoding"
        transcoded = True
        info = probe(dest) or info
    poster = dest.with_name(dest.stem + ".poster.jpg")
    duration = min(info["duration"] or MAX_VIDEO_S, MAX_VIDEO_S)
    if not _ffmpeg("-ss", f"{duration * 0.3:.2f}", "-i", str(dest), "-frames:v", "1", "-q:v", "4", str(poster)):
        poster = None
    item = {"type": "video", "file": dest.name, "width": info["width"], "height": info["height"],
            "duration_s": round(duration, 2), "bytes": dest.stat().st_size,
            "poster": poster.name if poster else None, "transcoded": transcoded}
    if trimmed:
        item["trimmed"] = True
    return item, None


MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS | {SVG_EXT}


def normalize(work_dir, out_dir):
    """Check every media file in work_dir/output/ and write the publishable versions plus manifest.json
    to out_dir. Returns the manifest: {ok, items: [...], errors: [...]}. ok = at least one item
    and no errors. Never raises for bad agent output: problems become `errors`.
    A file that isn't an image or video isn't output at all: it's left alone, so a script the model
    kept in ./output/ is not an error (the importer still publishes it as source when it's text)."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    output = work_dir / "output"
    files = sorted(p for p in output.rglob("*") if p.is_file() and not p.name.startswith(".")) if output.is_dir() else []
    media = [p for p in files if p.suffix.lower() in MEDIA_EXTS]
    items, errors = [], []
    if not files:
        errors.append("no files in ./output/")
    elif not media:
        errors.append("no image or video files in ./output/")
    if len(media) > MAX_FILES:
        errors.append(f"{len(media)} files in ./output/; only the first {MAX_FILES} were kept")
        media = media[:MAX_FILES]
    for src in media:
        name = "-".join(src.relative_to(output).parts)
        ext = src.suffix.lower()
        planned = Path(name).stem + ".mp4" if ext in VIDEO_EXTS else name
        if (out_dir / planned).exists():  # e.g. x.webm and x.mp4 would both become x.mp4
            errors.append(f"{name}: skipped, another output is already named {planned}")
            continue
        if ext == SVG_EXT:
            item, error = do_svg(src, out_dir, name)
        elif ext in IMAGE_EXTS:
            item, error = do_image(src, out_dir, name)
        else:  # the only extension left in MEDIA_EXTS
            item, error = do_video(src, out_dir, name)
        if item:
            items.append(item)
        if error:
            errors.append(error)
    manifest = {"ok": bool(items) and not errors, "items": items, "errors": errors}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


# A media run's source is the code that made the files: text only (rendered frames and the like are
# skipped), each file at most this big. work/output/ itself is published as the output, not as source.
SOURCE_MAX_BYTES = 512 * 1024


def _is_text(path):
    try:
        path.read_text(encoding="utf-8")
        return True
    except UnicodeDecodeError:
        return False


class Media(Kind):
    name = "media"
    tools = ("ffmpeg", "ffprobe")

    def finalize(self, work_dir, out_dir):
        """ok = at least one file was kept; problems with the ones it kept (unreadable, too big) are the
        error (the kept files are still published); files that aren't images/videos are ignored."""
        manifest = normalize(work_dir, out_dir)
        return bool(manifest["items"]), "; ".join(manifest["errors"])[:200] or None

    def verify(self, out_dir):
        """Every file was a readable image or video within the limits."""
        return {"ok": json.loads((out_dir / "manifest.json").read_text())["ok"]}

    def keep_source(self, rel, path):
        """Text files of at most 512 KB. `output/` itself is the media output, never source, but a non-media
        file the model left there (its generator script) is: the media step ignores it and dropping it would
        lose the code that made the files."""
        if rel.parts[0] == "output" and path.suffix.lower() in MEDIA_EXTS:
            return False
        return path.stat().st_size <= SOURCE_MAX_BYTES and _is_text(path)

    def stage(self, out_dir, run_dir, ctx):
        """SVGs are text written by the model, so they're cleaned and secret-scanned like source."""
        manifest = json.loads((out_dir / "manifest.json").read_text())
        items = []
        for item in manifest["items"]:
            out = {k: v for k, v in item.items() if k not in ("file", "poster")}
            out["path"] = f"media/{item['file']}"
            if item["file"].lower().endswith(".svg"):
                ctx.write_text(out_dir / item["file"], run_dir / out["path"])
            else:
                (run_dir / "media").mkdir(parents=True, exist_ok=True)
                shutil.copy(out_dir / item["file"], run_dir / out["path"])
            if item.get("poster"):
                out["poster"] = f"media/{item['poster']}"
                shutil.copy(out_dir / item["poster"], run_dir / out["poster"])
            items.append(out)
        thumb = next((i.get("poster") or i["path"] for i in items if i["type"] == "image" or i.get("poster")), None)
        return Staged({"items": items}, thumb)
