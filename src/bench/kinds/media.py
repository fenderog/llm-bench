"""The `media` kind: check and normalize the image/video files an agent saved in <level>/output/.
See SPEC.md "bench run" step 6. Uses ffmpeg/ffprobe (checked for before a media batch starts)."""

import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

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


def finalize(level_dir, out_dir):
    """Check every file in level_dir/output/ and write the publishable versions plus manifest.json
    to out_dir. Returns the manifest: {ok, items: [...], errors: [...]}. ok = at least one item
    and no errors. Never raises for bad agent output: problems become `errors`."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    output = level_dir / "output"
    files = sorted(p for p in output.rglob("*") if p.is_file() and not p.name.startswith(".")) if output.is_dir() else []
    items, errors = [], []
    if not files:
        errors.append("no files in ./output/")
    if len(files) > MAX_FILES:
        errors.append(f"{len(files)} files in ./output/; only the first {MAX_FILES} were kept")
        files = files[:MAX_FILES]
    for src in files:
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
        elif ext in VIDEO_EXTS:
            item, error = do_video(src, out_dir, name)
        else:
            item, error = None, f"{name}: unsupported file type"
        if item:
            items.append(item)
        if error:
            errors.append(error)
    manifest = {"ok": bool(items) and not errors, "items": items, "errors": errors}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
