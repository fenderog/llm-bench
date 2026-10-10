import os, subprocess, math, shutil
from make_pelican import full_svg_frame

frames_dir = "/tmp/pelican_frames"
if os.path.exists(frames_dir):
    shutil.rmtree(frames_dir)
os.makedirs(frames_dir, exist_ok=True)

N = 90  # 3 seconds at 30fps
print(f"generating {N} frames...")
for i in range(N):
    t = i / N
    svg = full_svg_frame(t)
    svg_path = f"{frames_dir}/f{i:03d}.svg"
    png_path = f"{frames_dir}/f{i:03d}.png"
    open(svg_path, "w").write(svg)
    # rasterize with sips
    r = subprocess.run(["sips", "-s", "format", "png", svg_path, "--out", png_path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit("sips failed")
    os.remove(svg_path)

# compile to mp4
out = "output/pelican-skateboard.mp4"
# ensure output dir
os.makedirs("output", exist_ok=True)
cmd = ["ffmpeg", "-y", "-framerate", "30", "-i", f"{frames_dir}/f%03d.png",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
       "-movflags", "+faststart", out]
print(" ".join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stderr[-2000:])
print("done", os.path.getsize(out))
# high-res png from middle frame
import shutil as sh
sh.copy(f"{frames_dir}/f045.png", "output/pelican-skateboard.png")
print("png", os.path.getsize("output/pelican-skateboard.png"))
# cleanup frames
shutil.rmtree(frames_dir)
print("cleaned frames")
