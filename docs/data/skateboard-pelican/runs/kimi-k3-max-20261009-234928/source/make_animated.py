#!/usr/bin/env python3
"""Generate pelican_skateboard_animated.svg from pelican_skateboard.svg by
injecting SMIL animation elements (spinning wheels, bobbing pelican,
drifting clouds/sun rays, sliding speed lines, pulsing dust)."""
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).parent / "output"
SRC = OUT / "pelican_skateboard.svg"
DST = OUT / "pelican_skateboard_animated.svg"

svg = SRC.read_text()

def inject(old, new):
    global svg
    assert svg.count(old) == 1, f"anchor not unique/found: {old[:70]!r}"
    svg = svg.replace(old, new)

# --- sun rays: slow rotation around the sun center ---
inject(
    '<g stroke="#ffd93b" stroke-width="7" stroke-linecap="round">',
    '<g stroke="#ffd93b" stroke-width="7" stroke-linecap="round">'
    '<animateTransform attributeName="transform" type="rotate" from="0 740 130" '
    'to="360 740 130" dur="40s" repeatCount="indefinite"/>',
)

# --- clouds: gentle drift ---
inject(
    '<g fill="#ffffff" opacity=".92">',
    '<g fill="#ffffff" opacity=".92">'
    '<animateTransform attributeName="transform" type="translate" '
    'values="0 0;26 0;0 0" dur="7s" repeatCount="indefinite"/>',
)
inject(
    '<g fill="#ffffff" opacity=".85">',
    '<g fill="#ffffff" opacity=".85">'
    '<animateTransform attributeName="transform" type="translate" '
    'values="0 0;-22 0;0 0" dur="9s" repeatCount="indefinite"/>',
)
inject(
    '<g fill="#ffffff" opacity=".8">',
    '<g fill="#ffffff" opacity=".8">'
    '<animateTransform attributeName="transform" type="translate" '
    'values="0 0;18 0;0 0" dur="8s" repeatCount="indefinite"/>',
)

# --- speed lines: slide backwards and fade in/out ---
inject(
    '<g stroke="#ffffff" stroke-linecap="round" fill="none" opacity=".75">',
    '<g stroke="#ffffff" stroke-linecap="round" fill="none" opacity=".75">'
    '<animateTransform attributeName="transform" type="translate" '
    'values="50 0;-70 0" dur="1.1s" repeatCount="indefinite"/>'
    '<animate attributeName="opacity" values="0;.75;.75;0" keyTimes="0;.15;.75;1" '
    'dur="1.1s" repeatCount="indefinite"/>',
)
inject(
    '<g stroke="#d8a860" stroke-linecap="round" fill="none" opacity=".8">',
    '<g stroke="#d8a860" stroke-linecap="round" fill="none" opacity=".8">'
    '<animateTransform attributeName="transform" type="translate" '
    'values="60 0;-80 0" dur="0.9s" repeatCount="indefinite"/>'
    '<animate attributeName="opacity" values="0;.8;.8;0" keyTimes="0;.15;.75;1" '
    'dur="0.9s" repeatCount="indefinite"/>',
)

# --- wheels: spinning spokes ---
for cx in ("368", "559"):
    hub = (f'<circle cx="{cx}" cy="574" r="7" fill="#e8fbff" '
           f'stroke="#1d8f84" stroke-width="2.5"/>')
    x1, x2 = int(cx) - 15, int(cx) + 15
    inject(
        hub,
        f'<g><animateTransform attributeName="transform" type="rotate" '
        f'from="0 {cx} 574" to="360 {cx} 574" dur="0.7s" repeatCount="indefinite"/>'
        f'<path d="M{cx} 559 V589 M{x1} 574 H{x2}" stroke="#1d8f84" '
        f'stroke-width="3" fill="none"/>{hub}</g>',
    )

# --- dust: pulsing puffs ---
inject(
    '<g fill="#e9c48a" opacity=".75">',
    '<g fill="#e9c48a" opacity=".75">'
    '<animate attributeName="opacity" values=".75;.3;.75" dur="1s" '
    'repeatCount="indefinite"/>',
)

# --- pelican: happy bounce ---
inject(
    '<!-- ===== pelican ===== -->\n  <g>',
    '<!-- ===== pelican ===== -->\n  <g>'
    '<animateTransform attributeName="transform" type="translate" '
    'values="0 0;0 -6;0 0" keyTimes="0;0.5;1" dur="1.3s" repeatCount="indefinite"/>',
)

# sanity check: the result must be well-formed XML
ET.fromstring(svg)

DST.write_text(svg)
print(f"wrote {DST}")
