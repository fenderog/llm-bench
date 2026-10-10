"""Small shared helpers: the expected-error type, ids, slugs, timestamps."""

import re
from datetime import datetime, timezone


class CritError(Exception):
    """A user-facing error: printed to stderr without a traceback."""


# The full effort-level order a harness may report; used to sort/validate/expand -m LEVELS specs.
LEVEL_ORDER = ["off", "minimal", "low", "medium", "high", "xhigh", "max"]
LEVEL_INDEX = {level: i for i, level in enumerate(LEVEL_ORDER)}


def parse_duration(text):
    """'30m' / '90s' / '1h' -> seconds."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([smh])", str(text).strip())
    if not m:
        raise CritError(f"bad duration: {text!r} (expected e.g. 30m, 90s, 1h)")
    n, unit = float(m.group(1)), m.group(2)
    return n * {"s": 1, "m": 60, "h": 3600}[unit]


def iso_from_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_run_id(model, effort, started, harness_tag=""):
    """'<model>-<effort>-<YYYYMMDD-HHMMSS>' (`started` is the batch's start time), with '-<harness tag>'
    after the model for harnesses other than pi (e.g. 'claude-opus-5-5-cc-high-...'), so one model under
    two harnesses can't collide. URL/filesystem-safe: '@' becomes '-via-' (OpenRouter upstreams),
    anything else outside [a-z0-9.-] becomes '-'."""
    base, _, upstream = model.partition("@")  # the upstream may contain "/" itself ("deepinfra/fp8")
    model_short = base.rsplit("/", 1)[-1].lower() + (f"-via-{upstream.lower()}" if upstream else "")
    model_short = re.sub(r"[^a-z0-9.-]", "-", model_short) + (f"-{harness_tag}" if harness_tag else "")
    return f"{model_short}-{effort}-{started:%Y%m%d-%H%M%S}"


def title_from_slug(slug):
    return slug.replace("-", " ").capitalize()


def effort_sort_key(run):
    """Sort key for page.json: started_at, then effort order (LEVEL_ORDER, then alpha)."""
    return (run["started_at"], LEVEL_INDEX.get(run["effort"], 99), run["effort"])


def mask(secret):
    return secret[:4] + "…"
