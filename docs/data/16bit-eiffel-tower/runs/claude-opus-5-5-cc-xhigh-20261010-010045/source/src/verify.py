"""Check a PNG against the SNES limits: 256x224, <=128 colours, <=16 per 8x8 tile,
and every colour exactly representable in 15-bit BGR555."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pngio import read_rgb  # noqa: E402


def check(path):
    rows = read_rgb(path)
    h, w = len(rows), len(rows[0])
    colours = {px for r in rows for px in r}
    worst = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            tile = {rows[y][x] for y in range(ty, ty + 8) for x in range(tx, tx + 8)}
            worst = max(worst, len(tile))
    bgr555 = all(((c >> 3) << 3 | (c >> 5)) == c for px in colours for c in px)
    ok = (w, h) == (256, 224) and len(colours) <= 128 and worst <= 16 and bgr555
    print(f'{path}: {w}x{h}, {len(colours)} colours, max {worst} per 8x8 tile, '
          f'BGR555-exact={bgr555} -> {"OK" if ok else "FAIL"}')
    return ok


if __name__ == '__main__':
    sys.exit(0 if all(check(p) for p in sys.argv[1:]) else 1)
