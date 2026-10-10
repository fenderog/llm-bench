#!/usr/bin/env bash
# Rebuilds every deliverable in output/ from make_pelican.py.
# Requires: macOS qlmanage (SVG rasterization), ffmpeg (video/gif).
set -euo pipefail

OUT=output
FRAMES=_frames

mkdir -p "$OUT" "$FRAMES"

# 1) master SVG illustration (vector, with embedded SMIL animation)
python3 make_pelican.py --static "$OUT/pelican_skateboard.svg"

# 2) high-res PNG rendered from the deterministic t=0 frame
python3 make_pelican.py --frame 0 "$FRAMES/t0.svg"
qlmanage -t -s 2048 -o "$FRAMES" "$FRAMES/t0.svg" >/dev/null 2>&1
mv "$FRAMES/t0.svg.png" "$OUT/pelican_skateboard.png"

# 3) 192 video frames (24 fps x 8 s = two seamless 4 s loops)
python3 make_pelican.py --frames "$FRAMES/" 24 192
qlmanage -t -s 1024 -o "$FRAMES" "$FRAMES"/frame_*.svg >/dev/null 2>&1
i=0
for f in "$FRAMES"/frame_*.svg.png; do
  mv "$f" "$(printf '%s/f_%04d.png' "$FRAMES" "$i")"
  i=$((i + 1))
done

# 4) MP4 (H.264) and WebM (VP9), 8 s @ 24 fps, 1024x1024
ffmpeg -y -hide_banner -loglevel error -framerate 24 -i "$FRAMES"/f_%04d.png \
  -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -movflags +faststart \
  "$OUT/pelican_skateboard.mp4"
ffmpeg -y -hide_banner -loglevel error -framerate 24 -i "$FRAMES"/f_%04d.png \
  -c:v libvpx-vp9 -crf 34 -b:v 0 -deadline good -cpu-used 4 -pix_fmt yuv420p \
  "$OUT/pelican_skateboard.webm"

# 5) GIF: one 4 s loop @ 12 fps, 512 px, forever-looping
ffmpeg -y -hide_banner -loglevel error -framerate 24 -i "$FRAMES"/f_%04d.png \
  -vf "fps=12,scale=512:512:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5" \
  -frames:v 48 -loop 0 "$OUT/pelican_skateboard.gif"

# 6) verify the raster render against expected colors (32 sample points)
python3 png_probe.py "$OUT/pelican_skateboard.png" 0.5 | tail -1

rm -rf "$FRAMES"
ls -la "$OUT"
