"""The `web` kind: package the page an agent wrote (work/index.html, its scripts and stylesheets,
and the npm packages they import) into one self-contained index.html with esbuild.
See SPEC.md "bench run" step 6 and ADR-0013."""

import base64
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..browser import copy_thumb, verify_page
from . import Kind, Staged

SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.I | re.S)
LINK_RE = re.compile(r"<link\b([^>]*)>", re.I)
ATTR_SRC_RE = re.compile(r"""\s+src\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+)""", re.I)
ATTR_RE = re.compile(r"""([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?""")
# Imported assets become data: URLs, so the bundle never loads a file at runtime.
ASSET_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".glb", ".gltf", ".bin", ".hdr", ".ktx2",
              ".wav", ".mp3", ".ogg", ".woff", ".woff2", ".ttf", ".otf")
MAX_BYTES = 20 * 1024 * 1024
ENTRY = "index.html"


class PackageError(Exception):
    pass


def parse_attrs(text):
    return {m.group(1).lower(): next((g for g in m.groups()[1:] if g is not None), "") for m in ATTR_RE.finditer(text)}


def is_local(url):
    return not re.match(r"^([a-z][a-z0-9+.-]*:|//)", url.strip(), re.I)


def local_file(project_dir, url):
    """A page-relative URL -> the file it names, which must be inside project_dir."""
    rel = re.split(r"[?#]", url.strip(), maxsplit=1)[0].lstrip("/")
    path = (project_dir / rel).resolve()
    if not path.is_relative_to(project_dir.resolve()) or not path.is_file():
        raise PackageError(f"{url!r} is not a file inside the project")
    return path


def esbuild(esbuild_bin, project_dir, entry=None, stdin=None, fmt=None):
    """Bundle one entry (a file, or JS on stdin resolved from project_dir) and return the output text."""
    cmd = [esbuild_bin, "--bundle", "--minify", "--charset=utf8", "--log-level=error", "--legal-comments=none",
           *(f"--loader:{ext}=dataurl" for ext in ASSET_EXTS)]
    if fmt:
        cmd.append(f"--format={fmt}")
    cmd += [str(entry)] if entry else ["--loader=js", "--sourcefile=inline-script.js"]
    try:
        r = subprocess.run(cmd, cwd=project_dir, input=stdin, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise PackageError(f"esbuild failed: {e}") from e
    if r.returncode != 0:
        detail = next((line.strip() for line in r.stderr.splitlines() if line.strip()), f"exit {r.returncode}")
        raise PackageError(f"esbuild: {detail}")
    return r.stdout


def _inline_script(code, module):
    code = re.sub(r"</(script)", r"<\\/\1", code, flags=re.I)  # the code must not close its own tag
    return ('<script type="module">' if module else "<script>") + code + "</script>"


def bundle_html(project_dir, esbuild_bin="esbuild"):
    """<project_dir>/index.html with every local script and stylesheet bundled and inlined.
    Module scripts are bundled with their imports; classic scripts with a local src become data: URLs;
    remote URLs, import maps and other script types are left as they are, so the offline verify step
    catches them."""
    html_path = project_dir / ENTRY
    if not html_path.is_file():
        raise PackageError(f"no {ENTRY} in the project")
    html = html_path.read_text(encoding="utf-8")

    def script(m):
        attrs, body = parse_attrs(m.group(1)), m.group(2)
        kind = attrs.get("type", "").strip().lower()
        module = kind == "module"
        if kind not in ("", "module", "text/javascript", "application/javascript"):
            return m.group(0)  # importmap, shaders, JSON data...
        src = attrs.get("src")
        if src is not None:
            if not is_local(src):
                return m.group(0)
            path = local_file(project_dir, src)
            if module:  # inline module scripts are deferred just like the original
                return _inline_script(esbuild(esbuild_bin, project_dir, entry=path, fmt="esm"), True)
            # A classic script can't import anything, and bundling it would turn its top-level vars
            # (globals other scripts use) into locals. A data: URL keeps it as it is, defer/async included.
            url = "data:text/javascript;base64," + base64.b64encode(path.read_bytes()).decode()
            return "<script" + ATTR_SRC_RE.sub(lambda _: f' src="{url}"', m.group(1), count=1) + "></script>"
        if not module:
            return m.group(0)  # classic inline script: nothing to resolve
        return _inline_script(esbuild(esbuild_bin, project_dir, stdin=body, fmt="esm"), True)

    def link(m):
        attrs = parse_attrs(m.group(1))
        href = attrs.get("href")
        if "stylesheet" not in attrs.get("rel", "").lower().split() or not href or not is_local(href):
            return m.group(0)
        css = esbuild(esbuild_bin, project_dir, entry=local_file(project_dir, href))
        return "<style>" + re.sub(r"</(style)", r"<\\/\1", css, flags=re.I) + "</style>"

    # Stylesheets first: bundled JS may contain "<link ..." strings that must stay untouched.
    return SCRIPT_RE.sub(script, LINK_RE.sub(link, html))


def esbuild_version(esbuild_bin="esbuild"):
    try:
        r = subprocess.run([esbuild_bin, "--version"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (r.stdout.strip() or None) if r.returncode == 0 else None


def package(project_dir, out_dir, esbuild_bin="esbuild"):
    """Write out_dir/index.html (one file) and out_dir/package-manifest.json.
    Returns (ok, manifest_or_None, error_or_None); never raises for a page that doesn't package."""
    try:
        html = bundle_html(project_dir, esbuild_bin)
    except PackageError as e:
        return False, None, f"packaging failed: {e}"
    size = len(html.encode("utf-8"))
    if size > MAX_BYTES:
        return False, None, f"packaging failed: page is {size / 1024 / 1024:.1f} MB (limit {MAX_BYTES // 1024 // 1024} MB)"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ENTRY).write_text(html, encoding="utf-8")
    manifest = {
        "esbuild": esbuild_version(esbuild_bin),
        "bytes": size,
        "packagedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (out_dir / "package-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return True, manifest, None


def read_manifest(web_dir):
    path = Path(web_dir) / "package-manifest.json"
    return json.loads(path.read_text()) if path.is_file() else {}


class Web(Kind):
    name = "web"
    tools = ("esbuild", "npm")
    tools_hint = "brew install esbuild node"
    activity = "packaging"

    def finalize(self, work_dir, out_dir):
        ok, _manifest, error = package(work_dir, out_dir)
        return ok, error

    def verify(self, out_dir):
        """The page loaded offline inside the site's sandbox, with no page errors and no blocked requests."""
        return verify_page(out_dir, "document.readyState === 'complete'",
                           lambda r: r["booted"] and not r["pageErrors"] and not r["blockedRequests"], sandboxed=True)

    def stage(self, out_dir, run_dir, ctx):
        """The page is model-written code, so it's cleaned and secret-scanned like source."""
        ctx.write_text(out_dir / ENTRY, run_dir / "game" / ENTRY)
        manifest = read_manifest(out_dir)
        fields = {"entry": f"game/{ENTRY}", "bytes": manifest.get("bytes"), "esbuild": manifest.get("esbuild")}
        return Staged(fields, copy_thumb(out_dir, run_dir))
