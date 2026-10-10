#!/usr/bin/env python3
"""Independent check of an SNES-style PNG: parses the file itself (no shared code with the generator).

usage: python3 -I src/verify.py output/eiffel_tower_snes.png
"""
import struct
import sys
import zlib


def read_png(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    pos, chunks = 8, {}
    idat = b''
    while pos < len(data):
        n, tag = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if tag == b'IDAT':
            idat += body
        else:
            chunks[tag] = body
        pos += 12 + n
    w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', chunks[b'IHDR'])
    assert ctype == 3 and depth == 8 and interlace == 0, 'expected 8-bit indexed, non-interlaced'
    plte = chunks[b'PLTE']
    palette = [tuple(plte[i:i + 3]) for i in range(0, len(plte), 3)]
    raw = zlib.decompress(idat)
    rows, stride = [], w
    prev = bytearray(stride)
    for y in range(h):
        base = y * (stride + 1)
        f = raw[base]
        line = bytearray(raw[base + 1:base + 1 + stride])
        for i in range(stride):
            a = line[i - 1] if i else 0
            b = prev[i]
            c = prev[i - 1] if i else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        rows.append(line)
        prev = line
    return w, h, palette, rows


def main():
    w, h, palette, rows = read_png(sys.argv[1])
    used = {c for r in rows for c in r}
    rgb_used = {palette[i] for i in used}
    worst, tiles_bad = 0, 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            cols = {rows[y][x] for y in range(ty, ty + 8) for x in range(tx, tx + 8)}
            worst = max(worst, len(cols))
            tiles_bad += len(cols) > 16
    # 15-bit gamut: each 8-bit channel must equal (v5 << 3) | (v5 >> 2)
    ok15 = all(c == ((c >> 3) << 3 | (c >> 3) >> 2) for rgb in rgb_used for c in rgb)
    print('size            :', w, 'x', h, '(expected 256 x 224)')
    print('palette entries :', len(palette))
    print('colours used    :', len(rgb_used), '(limit 128)')
    print('tiles           :', (w // 8) * (h // 8), ' worst colours in one 8x8 tile:', worst, '(limit 16)')
    print('tiles over 16   :', tiles_bad)
    print('15-bit colours  :', ok15)
    good = (w, h) == (256, 224) and len(rgb_used) <= 128 and worst <= 16 and ok15
    print('RESULT          :', 'PASS' if good else 'FAIL')
    sys.exit(0 if good else 1)


if __name__ == '__main__':
    main()
