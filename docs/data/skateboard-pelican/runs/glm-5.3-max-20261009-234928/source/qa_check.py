#!/usr/bin/env python3
"""QA helper: decode a PNG (8-bit, no interlace) and print an ASCII color map
plus point samples, so the artwork can be verified without eyes."""
import sys, zlib, struct

def decode_png(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a png'
    pos = 8
    width = height = bitdepth = colortype = None
    idat = b''
    palette = None
    while pos < len(data):
        ln, = struct.unpack('>I', data[pos:pos+4])
        typ = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+ln]
        pos += 12 + ln
        if typ == b'IHDR':
            width, height, bitdepth, colortype = struct.unpack('>IIBB', chunk[:10])
        elif typ == b'IDAT':
            idat += chunk
        elif typ == b'PLTE':
            palette = [tuple(chunk[i:i+3]) for i in range(0, len(chunk), 3)]
        elif typ == b'IEND':
            break
    assert bitdepth == 8, f'bitdepth {bitdepth}'
    nch = {0:1, 2:3, 3:1, 4:2, 6:4}[colortype]
    raw = zlib.decompress(idat)
    stride = width * nch
    lines = []
    prev = bytearray(stride)
    p = 0
    for y in range(height):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p+stride]); p += stride
        if f == 1:  # Sub
            for i in range(nch, stride):
                line[i] = (line[i] + line[i-nch]) & 0xff
        elif f == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xff
        elif f == 3:  # Average
            for i in range(stride):
                a = line[i-nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xff
        elif f == 4:  # Paeth
            for i in range(stride):
                a = line[i-nch] if i >= nch else 0
                b = prev[i]
                c = prev[i-nch] if i >= nch else 0
                pp = a + b - c
                pa, pb, pc = abs(pp-a), abs(pp-b), abs(pp-c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xff
        lines.append(bytes(line))
        prev = line
    px = []
    for line in lines:
        row = []
        for x in range(width):
            i = x * nch
            if colortype == 3:
                row.append(palette[line[i]] + (255,))
            elif colortype == 6:
                row.append(tuple(line[i:i+4]))
            elif colortype == 2:
                row.append(tuple(line[i:i+3]) + (255,))
            elif colortype == 0:
                v = line[i]
                row.append((v, v, v, 255))
            elif colortype == 4:
                v = line[i]
                row.append((v, v, v, line[i+1]))
        px.append(row)
    return width, height, px

# color classes: (name, char, representative rgb)
CLASSES = [
    ('sky-blue',   '.', (126, 201, 238)),
    ('pale-sky',   ',', (238, 249, 255)),
    ('sun-yellow', ('#'), (255, 213, 79)),
    ('white',      ('W'), (255, 255, 255)),
    ('sea-blue',   ('~'), (60, 170, 210)),
    ('wood-brown', ('='), (207, 160, 107)),
    ('wood-dark',  ('-'), (181, 135, 79)),
    ('purple-deck',('P'), (126, 87, 194)),
    ('amber',      ('o'), (255, 202, 40)),
    ('orange',     ('O'), (245, 124, 0)),
    ('cream-body', ('B'), (251, 246, 236)),
    ('wing-tan',   ('b'), (233, 223, 201)),
    ('red-helmet', ('R'), (255, 82, 82)),
    ('dark',       ('@'), (38, 50, 56)),
    ('gray',       ('+'), (96, 125, 139)),
]

def classify(rgb):
    best, bd = None, 1e9
    for name, ch, rep in CLASSES:
        d = sum((a-b)**2 for a, b in zip(rgb[:3], rep))
        if d < bd:
            bd, best = d, ch
    return best

def main():
    path = sys.argv[1]
    w, h, px = decode_png(path)
    print(f'{path}: {w}x{h}')
    if len(sys.argv) > 2:
        for spec in sys.argv[2:]:
            x, y = map(int, spec.split(','))
            # PNG may be scaled; sample center of 4x4 block
            rgb = px[min(y, h-1)][min(x, w-1)]
            print(f'  ({x},{y}) -> rgb{rgb[:3]} char={classify(rgb)}')
        return
    # ASCII map: sample grid ~ 100x62
    cols, rows = 100, 60
    out = []
    for r in range(rows):
        y = int((r + 0.5) * h / rows)
        line = []
        for c in range(cols):
            x = int((c + 0.5) * w / cols)
            line.append(classify(px[y][x]))
        out.append(''.join(line))
    print('\n'.join(out))

if __name__ == '__main__':
    main()
