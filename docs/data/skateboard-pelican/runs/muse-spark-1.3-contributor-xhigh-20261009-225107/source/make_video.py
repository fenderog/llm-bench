import pathlib, subprocess, shutil, os, sys
from make_illustration import svg_string, W, H

frames_dir = pathlib.Path("/tmp/pelican_frames")
frames_dir.mkdir(exist_ok=True, parents=True)
# clean old
for p in frames_dir.glob("*.png"):
    p.unlink()

total = 48
fps = 12
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

print(f"generating {total} SVG frames...")
for i in range(total):
    svg = svg_string(frame=i, total_frames=total, animated=True)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{{margin:0;padding:0;background:#fff;width:{W}px;height:{H}px;overflow:hidden}}svg{{display:block;width:{W}px;height:{H}px}}</style></head><body>{svg}</body></html>"""
    html_path = frames_dir / f"frame_{i:03d}.html"
    html_path.write_text(html)
print("rendering via chrome...")
for i in range(total):
    html_path = frames_dir / f"frame_{i:03d}.html"
    out_png = frames_dir / f"frame_{i:03d}.png"
    cmd=[chrome,"--headless","--disable-gpu","--no-sandbox",f"--screenshot={out_png}",f"--window-size={W},{H}",f"file://{html_path.resolve()}"]
    r=subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if not out_png.exists():
        print(f"FAILED frame {i}", r.stderr[-500:])
        sys.exit(1)
    if i%12==0:
        print(f"  rendered {i+1}/{total} ({out_png.stat().st_size//1024}KB)")
    # delete html to keep clean
    html_path.unlink()

# encode with ffmpeg - scale down to 1280x960 for smaller file? keep 1600x1200 but crf high
out_mp4 = pathlib.Path("output/pelican-skateboard.mp4")
# use 1280 width for balance (divisible by 2)
cmd=["ffmpeg","-y","-framerate",str(fps),"-i",str(frames_dir/"frame_%03d.png"),
     "-vf","scale=1280:960:flags=lanczos",
     "-c:v","libx264","-pix_fmt","yuv420p","-crf","23","-preset","medium",
     "-movflags","+faststart",str(out_mp4)]
print(" ".join(cmd))
r=subprocess.run(cmd, capture_output=True, text=True)
print(r.stderr[-2000:])
print("mp4 exists?", out_mp4.exists(), out_mp4.stat().st_size if out_mp4.exists() else 0)
# also make webm? no, mp4 enough
# cleanup frames
shutil.rmtree(frames_dir)
print("cleaned frames")
