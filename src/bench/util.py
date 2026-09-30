"""Small shared helpers: the expected-error type, ids, slugs, timestamps."""

import re
from datetime import datetime, timezone


class BenchError(Exception):
    """A user-facing error: printed to stderr without a traceback."""


# "2026-09-26-001158-gpt6sol-voxel-horse" -> ("2026-09-26-001158", "gpt6sol", "voxel-horse")
FOLDER_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})-([^-]+)-(.+)$")

# The full effort-level order a harness may report; used to sort/validate/expand -m LEVELS specs.
LEVEL_ORDER = ["off", "minimal", "low", "medium", "high", "xhigh", "max"]
LEVEL_INDEX = {level: i for i, level in enumerate(LEVEL_ORDER)}


def parse_folder(name):
    m = FOLDER_RE.match(name)
    if not m:
        raise BenchError(f"folder name doesn't look like YYYY-MM-DD-HHMMSS-model-slug: {name}")
    return m.groups()  # (timestamp, model_tag, slug)


def iso_from_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_run_id(model, effort, folder_name, harness_tag=""):
    """'<model>-<effort>-<YYYYMMDD-HHMMSS>', with '-<harness tag>' after the model for harnesses
    other than pi (e.g. 'claude-opus-5-5-cc-high-...'), so one model under two harnesses can't collide.
    URL/filesystem-safe: '@' becomes '-via-' (OpenRouter upstreams), anything else outside
    [a-z0-9.-] becomes '-'."""
    ts, _, _ = parse_folder(folder_name)
    y, mo, d, hhmmss = ts.split("-")
    base, _, route = model.partition("@")  # the route may contain "/" itself ("deepinfra/fp8")
    model_short = base.rsplit("/", 1)[-1].lower() + (f"-via-{route.lower()}" if route else "")
    model_short = re.sub(r"[^a-z0-9.-]", "-", model_short) + (f"-{harness_tag}" if harness_tag else "")
    return f"{model_short}-{effort}-{y}{mo}{d}-{hhmmss}"


def title_from_slug(slug):
    return slug.replace("-", " ").capitalize()


def effort_sort_key(run):
    """Sort key for results.json: started_at, then effort order (LEVEL_ORDER, then alpha)."""
    return (run["started_at"], LEVEL_INDEX.get(run["effort"], 99), run["effort"])


def mask(secret):
    return secret[:4] + "…"
