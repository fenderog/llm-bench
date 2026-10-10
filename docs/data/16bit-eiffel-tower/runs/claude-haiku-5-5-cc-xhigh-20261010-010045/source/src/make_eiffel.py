#!/usr/bin/env python3
"""Paint a dusk Eiffel Tower in SNES style and save it as a 256x224 PNG.

Standard library only. Colors are authored as 15-bit SNES values (5 bits per
channel) and written as an indexed PNG. After writing, the file is read back
and checked against the hardware limits:

  * 256x224 pixels, no scaling
  * at most 128 distinct colors in the picture
  * at most 16 distinct colors in every 8x8 tile

Usage: python3 make_eiffel.py [OUT_PNG] [--preview PREVIEW_PNG]
"""

import math
import os
import random
import struct
import sys
import zlib

W, H = 256, 224
TILE = 8
MAX_COLORS = 128
MAX_TILE_COLORS = 16

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "output", "eiffel_tower_snes.png")

GROUND_Y = 180  # row where the feet meet the lawn
TOWER_TOP = 20  # row of the spire tip
TOWER_H = GROUND_Y - TOWER_TOP
ANTENNA = 12  # rows of antenna above the spire tip

# Colors are (r, g, b) with 5 bits per channel, as on the SNES.
SKY_STOPS = [
    (0, (2, 2, 10)),
    (40, (5, 5, 20)),
    (80, (11, 8, 29)),
    (108, (18, 11, 31)),
    (128, (27, 16, 31)),
    (142, (31, 25, 29)),
]
STAR_BRIGHT = (31, 31, 27)
STAR_DIM = (17, 18, 30)
SPARKLE = (22, 22, 31)
SUN_CORE = (31, 31, 24)
SUN_MID = (31, 27, 12)
SUN_RIM = (31, 19, 6)
SUN_HALO = (31, 23, 16)
CLOUD_TOP = (31, 24, 31)
CLOUD_MID = (25, 17, 31)
CLOUD_LOW = (17, 11, 30)
CITY = (10, 5, 18)
CITY_EDGE = (17, 9, 26)
WINDOW = (31, 21, 8)
GRASS_FAR = (4, 12, 6)
GRASS_A = (6, 17, 8)
GRASS_B = (8, 21, 10)
GRASS_HI = (12, 28, 14)
TREE_DARK = (3, 8, 5)
TREE_MID = (5, 14, 8)
TREE_LIGHT = (9, 22, 11)
PATH_LIGHT = (25, 19, 16)
PATH_DARK = (18, 13, 13)
PATH_JOINT = (13, 9, 10)
SHADOW = (2, 6, 3)
BRONZE_HI = (28, 20, 11)
BRONZE_LIGHT = (22, 14, 7)
BRONZE = (16, 9, 4)
BRONZE_SHADE = (9, 5, 3)
BRONZE_DARK = (6, 3, 2)
STEEL_OUTLINE = (3, 1, 2)
GLINT = (31, 28, 13)

# Cloud puffs as (cx, cy, rx, ry) ellipses.
CLOUDS = [
    [(28, 60, 16, 7), (42, 54, 12, 9), (56, 60, 12, 6), (20, 62, 8, 4)],
    [(206, 74, 20, 8), (220, 68, 12, 8), (192, 76, 10, 5)],
    [(150, 98, 12, 4), (162, 95, 8, 4)],
]
SPARKLES = [(20, 22), (226, 28), (150, 40), (100, 30)]

# Deck positions: (height fraction, extra half-width, has railing).
DECKS = [(0.17, 7, True), (0.42, 4, True), (0.84, 2, False)]


def expand(c):
    """SNES 5-bit channel to 8-bit, replicating the top bits into the bottom."""
    return tuple((v << 3) | (v >> 2) for v in c)


def sky_color(y):
    for (y0, c0), (y1, c1) in zip(SKY_STOPS, SKY_STOPS[1:]):
        if y0 <= y <= y1:
            t = (y - y0) / float(y1 - y0)
            return tuple(int(round(a + (b - a) * t)) for a, b in zip(c0, c1))
    return SKY_STOPS[-1][1]


def in_cloud(x, y):
    for puffs in CLOUDS:
        for cx, cy, rx, ry in puffs:
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                return True
    return False


def tower_profile(h):
    """Outer half-width in pixels at height h (0 = feet, 1 = spire tip)."""
    if h < 0.17:  # splayed legs under the first deck
        return 20 + 16 * (1 - h / 0.17) ** 1.7
    if h < 0.42:
        return 20 - 11 * (h - 0.17) / 0.25
    if h < 0.84:
        return 9 - 6 * (h - 0.42) / 0.42
    return 3 * max(0.0, 1 - (h - 0.84) / 0.16) ** 0.8


def arch_inner(h):
    """Inner edge of the arch under the first deck; 0 once the arch closes."""
    if h >= 0.13:
        return 0.0
    return 22 * math.sqrt(1 - (h / 0.13) ** 2)


def lattice(x, y, h):
    """Diagonal X-bracing. The upper section uses a finer weave."""
    period = 6 if h < 0.6 else 4
    return (x + y) % period == 0 or (x - y) % period == 0


def draw_sky(put, rng):
    for y in range(GROUND_Y):
        for x in range(W):
            put(x, y, sky_color(y))

    for _ in range(60):
        x, y = rng.randrange(W), rng.randrange(0, 72)
        if not in_cloud(x, y):
            put(x, y, STAR_BRIGHT if rng.random() < 0.3 else STAR_DIM)
    for x, y in SPARKLES:
        put(x, y, STAR_BRIGHT)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(x + dx, y + dy, SPARKLE)


def draw_sun(put, sx=62, sy=132):
    for y in range(sy - 16, sy + 17):
        for x in range(sx - 16, sx + 17):
            d = math.hypot(x - sx, y - sy)
            if d <= 5:
                put(x, y, SUN_CORE)
            elif d <= 8.5:
                put(x, y, SUN_MID)
            elif d <= 11:
                put(x, y, SUN_RIM)
            elif d <= 15:
                put(x, y, SUN_HALO)


def draw_clouds(put):
    for y in range(GROUND_Y):
        for x in range(W):
            if not in_cloud(x, y):
                continue
            if not in_cloud(x, y - 2):
                c = CLOUD_TOP
            elif not in_cloud(x, y + 2):
                c = CLOUD_LOW
            else:
                c = CLOUD_MID
            put(x, y, c)


def draw_city(put, rng):
    x = 0
    while x < W:
        bw = rng.randint(6, 13)
        top = GROUND_Y + 2 - rng.randint(18, 40)
        for xx in range(x, min(W, x + bw)):
            for yy in range(top, GROUND_Y + 2):
                c = CITY_EDGE if yy == top else CITY
                if (yy > top and (xx - x) % 3 == 1 and (yy - top) % 4 == 2
                        and rng.random() < 0.4):
                    c = WINDOW
                put(xx, yy, c)
        x += bw


def draw_ground(put, rng):
    for y in range(GROUND_Y, H):
        for x in range(W):
            if y < GROUND_Y + 4:
                c = GRASS_FAR
            elif (y - GROUND_Y) // 4 % 2 == 0:
                c = GRASS_A
            else:
                c = GRASS_B
            put(x, y, c)
    for _ in range(90):
        put(rng.randrange(W), rng.randrange(GROUND_Y + 6, H), GRASS_HI)


def draw_bush(put, cx, cy, r):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > r * r + r:
                continue
            if dx + dy < -r * 0.7:  # sunlit upper-left rim
                c = TREE_LIGHT
            elif dy > r * 0.4:  # shaded underside
                c = TREE_DARK
            elif (x * 5 + y * 3) % 7 == 0:
                c = TREE_LIGHT
            else:
                c = TREE_MID
            put(x, y, c)


def draw_path(put):
    for y in range(GROUND_Y + 2, H):
        row = y - GROUND_Y - 2
        half = 2 + row * 1.6
        offset = (row // 4 * 4) % 8  # running bond between stone courses
        for x in range(W):
            dx = x + 0.5 - W / 2
            if abs(dx) > half:
                continue
            if row % 4 == 0 or (x + offset) % 8 == 0:
                c = PATH_JOINT
            elif abs(dx) > half - 2:
                c = PATH_DARK
            else:
                c = PATH_LIGHT
            put(x, y, c)


def draw_shadow(put):
    for y in range(GROUND_Y, GROUND_Y + 4):
        half = 42 - (y - GROUND_Y) * 8
        for x in range(W):
            if abs(x + 0.5 - W / 2) <= half:
                put(x, y, SHADOW)


def draw_tower(put):
    """Draw the lattice tower. Returns the solid body pixels for glints."""
    solid = []
    for y in range(TOWER_TOP - ANTENNA, GROUND_Y):
        h = (GROUND_Y - (y + 0.5)) / TOWER_H
        for x in range(W):
            dx = x + 0.5 - W / 2
            adx = abs(dx)
            left = dx < 0
            if h > 1.0:  # antenna
                if adx <= 0.6:
                    put(x, y, BRONZE_HI if left else BRONZE_SHADE)
                continue
            w = tower_profile(h)
            inner = arch_inner(h)
            if adx > w or adx < inner:
                continue
            if w - adx < 1.0:  # outer outline, same on both sides
                c = STEEL_OUTLINE
            elif w - adx < 2.0:  # rim light from the sun on the left
                c = BRONZE_HI if left else BRONZE_SHADE
            elif inner and adx - inner < 1.2:  # arch frame
                c = BRONZE_LIGHT if left else BRONZE_DARK
            elif h < 0.03 or lattice(x, y, h):  # solid feet, or bracing
                c = BRONZE_LIGHT if left else BRONZE
                solid.append((x, y))
            else:
                continue  # open lattice: the sky shows through
            put(x, y, c)
    return solid


def draw_decks(put):
    for hd, extra, railing in DECKS:
        yd = round(GROUND_Y - hd * TOWER_H) - 1
        half = tower_profile(hd) + extra
        for x in range(W):
            dx = x + 0.5 - W / 2
            if abs(dx) > half:
                continue
            if railing and x % 2 == 0:
                put(x, yd - 2, BRONZE_LIGHT)
            put(x, yd, BRONZE_HI if dx < 0 else BRONZE_LIGHT)
            put(x, yd + 1, BRONZE_SHADE)

    # Small enclosed cabin on the top deck.
    cy = round(GROUND_Y - 0.84 * TOWER_H) - 1
    for y in range(cy - 6, cy):
        for x in range(W):
            if abs(x + 0.5 - W / 2) <= 2.5:
                c = GLINT if y == cy - 3 and x % 2 == 0 else BRONZE_DARK
                put(x, y, c)


def build_canvas():
    px = [[None] * W for _ in range(H)]

    def put(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = c

    rng = random.Random(1994)
    draw_sky(put, rng)
    draw_sun(put)
    draw_clouds(put)
    draw_city(put, rng)
    draw_ground(put, rng)
    draw_bush(put, 24, 166, 22)
    draw_bush(put, 232, 166, 22)
    draw_bush(put, 206, 178, 12)
    draw_path(put)
    draw_shadow(put)
    solid = draw_tower(put)
    draw_decks(put)
    for x, y in rng.sample(solid, 18):  # lights strung along the ironwork
        put(x, y, GLINT)
    return px


def to_indices(px):
    palette = []
    index_of = {}
    indices = bytearray()
    for row in px:
        for c in row:
            if c is None:
                raise SystemExit("canvas has an unpainted pixel")
            if c not in index_of:
                index_of[c] = len(palette)
                palette.append(c)
            indices.append(index_of[c])
    return palette, bytes(indices)


PNG_SIG = b"\x89PNG\r\n\x1a\n"


def png_chunk(tag, body):
    crc = zlib.crc32(tag + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", crc)


def write_png(path, width, height, indices, palette):
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # filter type: none
        rows += indices[y * width:(y + 1) * width]
    plte = bytes(v for c in palette for v in expand(c))
    data = (PNG_SIG
            + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
            + png_chunk(b"PLTE", plte)
            + png_chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + png_chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)


def read_png(path):
    """Decode an 8-bit indexed PNG written by write_png (filter type 0 only)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != PNG_SIG:
        raise SystemExit("not a PNG file")
    chunks = {}
    idat = b""
    pos = 8
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        (crc,) = struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])
        if zlib.crc32(tag + body) & 0xFFFFFFFF != crc:
            raise SystemExit("bad CRC in " + tag.decode())
        if tag == b"IDAT":
            idat += body
        else:
            chunks[tag] = body
        pos += 12 + n
    width, height, depth, ctype, _, _, _ = struct.unpack(">IIBBBBB", chunks[b"IHDR"])
    plte = chunks[b"PLTE"]
    palette = [tuple(plte[i:i + 3]) for i in range(0, len(plte), 3)]
    raw = zlib.decompress(idat)
    stride = width + 1
    indices = bytearray()
    for y in range(height):
        if raw[y * stride] != 0:
            raise SystemExit("unexpected PNG filter type")
        indices += raw[y * stride + 1:(y + 1) * stride]
    return width, height, depth, ctype, palette, bytes(indices)


def verify(path):
    width, height, depth, ctype, palette, indices = read_png(path)
    if (width, height) != (W, H):
        raise SystemExit(f"size is {width}x{height}, expected {W}x{H}")
    if depth != 8 or ctype != 3:
        raise SystemExit("expected an 8-bit indexed-color PNG")
    used = set(indices)
    if max(used) >= len(palette):
        raise SystemExit("pixel refers to a missing palette entry")
    if len(used) > MAX_COLORS:
        raise SystemExit(f"{len(used)} colors used, limit is {MAX_COLORS}")
    worst = 0
    for ty in range(H // TILE):
        for tx in range(W // TILE):
            tile = set()
            for y in range(ty * TILE, (ty + 1) * TILE):
                start = y * W + tx * TILE
                tile.update(indices[start:start + TILE])
            worst = max(worst, len(tile))
    if worst > MAX_TILE_COLORS:
        raise SystemExit(f"a tile uses {worst} colors, limit is {MAX_TILE_COLORS}")
    return len(used), worst


def scale(indices, k):
    out = bytearray()
    for y in range(H):
        row = indices[y * W:(y + 1) * W]
        big = bytes(b for b in row for _ in range(k))
        out += big * k
    return bytes(out)


def main(argv):
    args = list(argv[1:])
    preview = None
    if "--preview" in args:
        i = args.index("--preview")
        preview = args[i + 1]
        del args[i:i + 2]
    out = args[0] if args else DEFAULT_OUT

    palette, indices = to_indices(build_canvas())
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    write_png(out, W, H, indices, palette)
    used, worst = verify(out)
    print(f"wrote {os.path.normpath(out)}: {W}x{H}, {used} colors, "
          f"worst 8x8 tile {worst}/{MAX_TILE_COLORS}")
    if preview:
        write_png(preview, W * 3, H * 3, scale(indices, 3), palette)


if __name__ == "__main__":
    main(sys.argv)
