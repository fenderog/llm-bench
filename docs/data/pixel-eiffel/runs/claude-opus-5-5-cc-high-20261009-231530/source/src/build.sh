#!/bin/sh
# Render the 256x224 pixel art, then upscale 4x with nearest-neighbor to JPG.
set -e
cd "$(dirname "$0")"
python3 eiffel.py eiffel.ppm
ffmpeg -y -loglevel error -i eiffel.ppm -vf scale=iw*4:ih*4:flags=neighbor \
  -pix_fmt yuvj444p -q:v 1 ../output/eiffel_tower_16bit.jpg
rm eiffel.ppm
