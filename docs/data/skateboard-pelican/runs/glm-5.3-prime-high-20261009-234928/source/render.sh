#!/bin/sh
# Renders pelican_skateboard.svg to output/pelican_skateboard.png
#
# qlmanage renders an SVG at (intrinsic size * 25/12) px for a requested
# thumbnail size of 1600, top-left aligned, on a white 1600x1600 canvas.
# Setting width=768 height=512 makes the full 900x600 viewBox render at
# exactly 1600x1066.67, so a simple crop recovers a clean 3:2 image.
set -e
mkdir -p output
cp pelican_skateboard.svg output/pelican_skateboard.svg
sed 's|width="900" height="600"|width="768" height="512"|' \
    pelican_skateboard.svg > .render.svg
qlmanage -t -s 1600 -o . .render.svg >/dev/null 2>&1
mv .render.svg.png .render.png
ffmpeg -v error -y -i .render.png -vf "crop=1600:1066:0:0" \
    output/pelican_skateboard.png
rm -f .render.svg .render.png
