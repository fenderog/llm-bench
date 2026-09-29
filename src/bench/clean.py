"""Cleaning rules applied to session/session-derived files before they reach docs/.

See SPEC.md "Cleaning": drop sensitive keys, rewrite path prefixes, then scan (or redact)
secrets in the final text.
"""

import json
import re

DROP_KEYS = {
    "thinkingSignature",
    "encrypted_content",
    "pid",
    "completionOwnerId",
    "sessionId",
    "sessionFile",
    "sessionRoot",
    "launchContractDigest",
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"gho_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)[\"'\s:=]+[A-Za-z0-9_\-/+]{24,}"),
]


def strip_keys(obj):
    """Recursively drop DROP_KEYS from dicts, at any depth."""
    if isinstance(obj, dict):
        return {k: strip_keys(v) for k, v in obj.items() if k not in DROP_KEYS}
    if isinstance(obj, list):
        return [strip_keys(v) for v in obj]
    return obj


def rewrite_text(text, rewrites):
    """Apply each (old, new) substring rewrite. Returns (text, n_replacements)."""
    n = 0
    for old, new in rewrites:
        c = text.count(old)
        if c:
            text = text.replace(old, new)
            n += c
    return text, n


def scan_secrets(text):
    """Return [(line_number, matched_text), ...] for every secret pattern hit."""
    hits = []
    for pat in SECRET_PATTERNS:
        for m in pat.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append((line, m.group(0)))
    return sorted(hits)


def redact_secrets(text):
    """Replace every secret pattern hit with [REDACTED]. Returns (text, n_redacted)."""
    n = 0
    for pat in SECRET_PATTERNS:
        text, k = pat.subn("[REDACTED]", text)
        n += k
    return text, n


BASE64 = re.compile(r"[A-Za-z0-9+/]+={0,2}")


def set_aside_images(obj, images):
    """Replace the base64 `data` of every image block ({"type": "image", "data": ...}) with a
    placeholder and append the data to `images`. Image data is binary, not text: path rewrites
    could corrupt it and the secret scan finds random matches in it (AKIA...). Data that isn't
    plain base64 is left in place, so it's still scanned."""
    if isinstance(obj, list):
        return [set_aside_images(v, images) for v in obj]
    if not isinstance(obj, dict):
        return obj
    obj = {k: set_aside_images(v, images) for k, v in obj.items()}
    data = obj.get("data")
    if obj.get("type") == "image" and isinstance(data, str) and BASE64.fullmatch(data):
        images.append(data)
        obj["data"] = f"<image data {len(images) - 1}>"
    return obj


def restore_images(text, images):
    """Put back the data set aside by set_aside_images()."""
    for i, data in enumerate(images):
        text = text.replace(f'"<image data {i}>"', json.dumps(data), 1)
    return text


def clean_json(text, rewrites, images=None):
    """A whole-document JSON file (object or array): strip keys, then rewrite paths. With `images`
    (a list), image data is set aside there (see set_aside_images); restore it after scanning."""
    obj = strip_keys(json.loads(text))
    if images is not None:
        obj = set_aside_images(obj, images)
    text = json.dumps(obj, indent=2) + "\n"
    return rewrite_text(text, rewrites)


def clean_jsonl(text, rewrites, images=None):
    """A JSONL file: clean line by line."""
    n = 0
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        obj = strip_keys(json.loads(line))
        if images is not None:
            obj = set_aside_images(obj, images)
        line, k = rewrite_text(json.dumps(obj), rewrites)
        n += k
        out.append(line)
    return "\n".join(out) + "\n", n


def clean_plain(text, rewrites):
    """output.md and source files: path rewriting only (no key stripping)."""
    return rewrite_text(text, rewrites)
