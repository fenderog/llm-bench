"""Render a 16-bit (RGB565) pixel-art Eiffel Tower and save it as a JPG.

The tower is drawn procedurally on a small 160x200 grid, each colour is
quantised to RGB565 (5 bits red, 6 bits green, 5 bits blue), then the grid
is scaled 4x with nearest-neighbour so the pixels stay blocky. The raw
image is piped to ffmpeg as PPM, so no intermediate files are written.
"""
import os
import subprocess

W, H = 160, 200
SCALE = 4
GROUND = 185          # y of the ground line
TOP = 20              # y of the tower's tip
CX = 80               # centre column


def half_width(y):
    """Half-width of the tower at height y (wider at the base)."""
    t = min(max((GROUND - y) / (GROUND - TOP), 0.0), 1.0)
    return 38 * (1 - t) ** 1.35 + 0.8


def sky(x, y):
    """Dusk gradient from deep blue at the top to orange at the horizon."""
    t = min(y / GROUND, 1.0)
    top = (18, 22, 58)
    hor = (244, 146, 86)
    r = top[0] + (hor[0] - top[0]) * t
    g = top[1] + (hor[1] - top[1]) * t
    b = top[2] + (hor[2] - top[2]) * t
    if y < 60 and (x * 7 + y * 13) % 97 == 0:   # a few stars
        return (250, 250, 220)
    return (r, g, b)


def ground(x, y):
    shade = 1.0 + 0.12 * ((x * 3 + y * 5) % 4 - 1.5) / 1.5
    return (int(26 * shade), int(72 * shade), int(34 * shade))


def tower_colour(x, y):
    """Return the tower colour at (x, y), or None if it's not tower."""
    dx = abs(x - CX)
    if 8 <= y < TOP and x == CX:                 # antenna
        return (200, 180, 120)
    if y < TOP or y > GROUND:
        return None
    h = half_width(y)
    if dx > h:
        return None

    lit = x < CX      # sun from the left
    base = (150, 104, 62) if lit else (84, 58, 38)

    if y < 86:                                   # solid spire
        return base
    if abs(y - 86) <= 1 and dx <= 14:            # second platform
        return (196, 150, 96) if lit else (128, 92, 56)
    if abs(y - 140) <= 1 and dx <= 27:           # first platform
        return (196, 150, 96) if lit else (128, 92, 56)
    if y >= 160 and dx < h - 7:                  # arch opening under legs
        return None
    if dx >= h - 3:                              # outer leg edges
        return base
    if (x % 5 == 0) or (y % 5 == 0):             # iron lattice
        return (176, 128, 80) if lit else (104, 74, 48)
    return None


def pixel(x, y):
    if y >= GROUND:
        return ground(x, y)
    c = tower_colour(x, y)
    if c is None:
        c = sky(x, y)
    return c


def to_rgb565(r, g, b):
    """Quantise an 8-bit colour to 16-bit RGB565 and expand back to 8-bit."""
    r5 = int(r) >> 3
    g6 = int(g) >> 2
    b5 = int(b) >> 3
    return ((r5 << 3) | (r5 >> 2),
            (g6 << 2) | (g6 >> 4),
            (b5 << 3) | (b5 >> 2))


def main():
    rows = bytearray()
    for y in range(H):
        row = bytearray()
        for x in range(W):
            r, g, b = to_rgb565(*pixel(x, y))
            row += bytes((r, g, b)) * SCALE
        rows += bytes(row) * SCALE

    w, h = W * SCALE, H * SCALE

    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "eiffel_tower_16bit.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-s", "%dx%d" % (w, h), "-i", "pipe:0",
         "-q:v", "2", out],
        input=bytes(rows), check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
