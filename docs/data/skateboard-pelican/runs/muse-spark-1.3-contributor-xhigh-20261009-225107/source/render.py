import subprocess, pathlib, shutil, os
W,H=1600,1200
# create html wrapper that embeds svg inline for perfect rendering
svg = pathlib.Path("output/pelican-skateboard.svg").read_text()
html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{{margin:0;padding:0;background:#fff;width:{W}px;height:{H}px;overflow:hidden}}svg{{display:block;width:{W}px;height:{H}px}}</style></head><body>{svg}</body></html>"""
pathlib.Path("/tmp/render.html").write_text(html)
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
out="/tmp/pelican.png"
# remove old
try: os.remove(out)
except: pass
cmd=[chrome,"--headless","--disable-gpu","--no-sandbox",f"--screenshot={out}",f"--window-size={W},{H}","file:///tmp/render.html"]
print(" ".join(cmd))
import subprocess
r=subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print(r.stdout[-1000:])
print(r.stderr[-2000:])
print("exists?", pathlib.Path(out).exists())
if pathlib.Path(out).exists():
    print(pathlib.Path(out).stat().st_size)
    # copy to output, then optimize? just copy
    shutil.copy(out, "output/pelican-skateboard.png")
    print("copied")
