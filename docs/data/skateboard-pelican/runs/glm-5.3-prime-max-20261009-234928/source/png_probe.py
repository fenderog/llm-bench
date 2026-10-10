#!/usr/bin/env python3
"""
Pure-python PNG pixel prober (8-bit RGB/RGBA, non-interlaced).
Samples expected colors at key locations to verify SVG renders.

Usage: python3 png_probe.py image.png [scale]
  scale = svg-units-per-pixel factor if image was rendered at a size
  different from the 1024 design grid (e.g. 2 for a 512 render).
"""

import struct
import sys
import zlib


def decode(path):
    d = open(path, "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n", "not a png"
    pos, idat, meta = 8, b"", {}
    while pos < len(d):
        ln, typ = struct.unpack(">I4s", d[pos:pos + 8])
        pos += 8
        body = d[pos:pos + ln]
        pos += ln + 4
        if typ == b"IHDR":
            meta = dict(zip(
                ("w", "h", "bd", "ct", "comp", "filt", "inter"),
                struct.unpack(">IIBBBBB", body)))
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
    raw = zlib.decompress(idat)
    w, h, bd, ct = meta["w"], meta["h"], meta["bd"], meta["ct"]
    assert bd == 8 and meta["inter"] == 0, f"unsupported png bd={bd} inter={meta['inter']}"
    nch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    if ct == 3:
        raise AssertionError("palette png not expected")
    stride = w * nch
    # undo per-scanline filters
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        if f == 1:  # sub
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 0xFF
        elif f == 2:  # up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:  # average
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + (a + prev[i]) // 2) & 0xFF
        elif f == 4:  # paeth
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, nch, out


def hex2rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def main():
    path = sys.argv[1]
    scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    w, h, nch, px = decode(path)
    print(f"{path}: {w}x{h} channels={nch}")

    def sample(x, y):
        sx, sy = min(int(x / scale), w - 1), min(int(y / scale), h - 1)
        o = (sy * w + sx) * nch
        return tuple(px[o:o + 3]), (px[o + 3] if nch == 4 else 255)

    # (name, svg-x, svg-y, expected hex, tolerance)
    checks = [
        ("sky top",       30,   30,  "#a8e6ff", 40),
        ("sky mid",       512, 420,  "#7fd5f8", 40),
        ("sun",           152, 128,  "#ffd94e", 40),
        ("cloud",         436, 130,  "#ffffff", 45),
        ("hill A",        240, 860,  "#c6e6b4", 45),
        ("hill B",       1000, 850,  "#b2d9a1", 45),
        ("road top",      60,  895,  "#78838f", 40),
        ("road bot",      60, 1015,  "#5c6670", 40),
        ("road dash",      36,  952,  "#ffd95e", 45),
        ("road edge",    512,  880,  "#4a545e", 40),
        ("pelican body", 600,  620,  "#fdfaf0", 35),
        ("wing",         500,  570,  "#f0e8d2", 40),
        ("neck",         655,  420,  "#fdfaf0", 35),
        ("head/cheek",   660,  275,  "#fdfaf0", 35),
        ("beak upper",   860,  270,  "#fa9c33", 45),
        ("beak tip",     945,  295,  "#f97316", 45),
        ("pouch",        840,  345,  "#ffc06a", 45),
        ("helmet",       632,  200,  "#e5484d", 45),
        ("eye",          692,  252,  "#23262b", 45),
        ("tail feather", 365,  522,  "#fdfaf0", 35),
        ("leg",          596,  700,  "#f28c28", 45),
        ("foot",         610,  748,  "#f28c28", 45),
        ("deck",         540,  770,  "#ff5964", 45),
        ("grip",         540,  760,  "#31363d", 45),
        ("truck",        400,  786,  "#7e8a99", 50),
        ("wheel",        431,  840,  "#2d2f33", 45),
        ("hub",          400,  840,  "#ffd95e", 45),
        ("front wheel",  698,  840,  "#2d2f33", 45),
        ("beak base",    720,  245,  "#fbb24b", 50),
        ("speed line",   200,  468,  "#ffffff", 60),
        ("outline body", 540,  445,  "#37393f", 55),
        ("shadow",       534,  892,  "#515c68", 50),
    ]
    fails = 0
    for name, x, y, exp, tol in checks:
        got, a = sample(x, y)
        e = hex2rgb(exp)
        ok = all(abs(g - c) <= tol for g, c in zip(got, e)) and a > 200
        if not ok:
            fails += 1
        print(f"  {'OK ' if ok else 'FAIL'} {name:14s} @({x:4d},{y:4d}) want {exp} got "
              f"#{got[0]:02x}{got[1]:02x}{got[2]:02x} a={a}")
    print(f"{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
