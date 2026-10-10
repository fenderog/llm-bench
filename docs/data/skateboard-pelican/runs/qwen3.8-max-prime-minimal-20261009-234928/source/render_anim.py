#!/usr/bin/env python3
"""Render animation frames (SVG) -> PNG via qlmanage -> mp4 via ffmpeg."""
import os, shutil, subprocess, sys
import make_svg

FPS = 24
DUR = 3.0  # seconds
N = int(FPS * DUR)
FR = "build/frames"

def main():
    shutil.rmtree(FR, ignore_errors=True)
    os.makedirs(FR, exist_ok=True)
    files = []
    for i in range(N):
        t = i / FPS
        p = os.path.join(FR, f"frame_{i:03d}.svg")
        with open(p, "w") as f:
            f.write(make_svg.svg_frame(t=t))
        files.append(p)
    print(f"wrote {N} svg frames")

    # rasterize all frames in one qlmanage pass
    subprocess.run(["qlmanage", "-t", "-s", "800", "-o", FR, *files],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("rasterized")

    # crop square thumbnails back to 800x600 and encode
    os.makedirs("build/cropped", exist_ok=True)
    for i in range(N):
        src = os.path.join(FR, f"frame_{i:03d}.svg.png")
        dst = os.path.join("build/cropped", f"frame_{i:03d}.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                        "-vf", "crop=800:600:0:0", dst], check=True)
    print("cropped")

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-framerate", str(FPS), "-i", "build/cropped/frame_%03d.png",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-movflags", "+faststart", "output/pelican_skateboard.mp4"], check=True)
    print("encoded output/pelican_skateboard.mp4")

if __name__ == "__main__":
    main()
