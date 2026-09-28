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


def make_run_id(model, effort, folder_name):
    ts, _, _ = parse_folder(folder_name)
    y, mo, d, hhmmss = ts.split("-")
    model_short = model.rsplit("/", 1)[-1].lower()
    return f"{model_short}-{effort}-{y}{mo}{d}-{hhmmss}"


def title_from_slug(slug):
    return slug.replace("-", " ").capitalize()


def effort_sort_key(run):
    """Sort key for results.json: started_at, then effort order (LEVEL_ORDER, then alpha)."""
    return (run["started_at"], LEVEL_INDEX.get(run["effort"], 99), run["effort"])


def mask(secret):
    return secret[:4] + "…"
