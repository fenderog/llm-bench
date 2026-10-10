#!/bin/sh
# Rasterise the hand-written SVG to a 2x PNG using macOS's built-in sips (CoreSVG).
set -e
cd "$(dirname "$0")"
mkdir -p tmp
sed 's/width="1200" height="900"/width="2400" height="1800"/' output/pelican-skateboard.svg > tmp/pelican-2x.svg
sips -s format png tmp/pelican-2x.svg --out output/pelican-skateboard.png >/dev/null
rm -rf tmp
