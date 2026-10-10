"""Minimal PNG reading/writing with the standard library only."""
import struct
import zlib


def _chunk(kind, data):
    out = struct.pack('>I', len(data)) + kind + data
    return out + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_indexed(path, rows, palette):
    """rows: list of lists of palette indices; palette: list of (r, g, b)."""
    h, w = len(rows), len(rows[0])
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    png = b'\x89PNG\r\n\x1a\n'
    png += _chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 3, 0, 0, 0))
    png += _chunk(b'PLTE', b''.join(bytes(c) for c in palette))
    png += _chunk(b'IDAT', zlib.compress(raw, 9))
    png += _chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def write_rgb(path, rows):
    """rows: list of lists of (r, g, b)."""
    h, w = len(rows), len(rows[0])
    raw = b''.join(b'\x00' + bytes(v for px in r for v in px) for r in rows)
    png = b'\x89PNG\r\n\x1a\n'
    png += _chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += _chunk(b'IDAT', zlib.compress(raw, 9))
    png += _chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def read_rgb(path):
    """Decode an 8-bit PNG (gray, RGB, indexed, gray+alpha, RGBA) to RGB rows."""
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    pos, idat, plte = 8, b'', None
    while pos < len(data):
        n, = struct.unpack('>I', data[pos:pos + 4])
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if kind == b'IHDR':
            w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', body)
        elif kind == b'PLTE':
            plte = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif kind == b'IDAT':
            idat += body
        pos += 12 + n
    assert depth == 8 and interlace == 0, 'only 8-bit non-interlaced PNGs'
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * bpp
    prev = bytearray(stride)
    rows = []
    for y in range(h):
        ft = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                line[i] = (line[i] + a) & 255
            elif ft == 2:
                line[i] = (line[i] + b) & 255
            elif ft == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        prev = line
        if ctype == 3:
            rows.append([plte[v] for v in line])
        elif ctype == 0:
            rows.append([(v, v, v) for v in line])
        elif ctype == 4:
            rows.append([(line[i], line[i], line[i]) for i in range(0, stride, 2)])
        else:
            rows.append([tuple(line[i:i + 3]) for i in range(0, stride, bpp)])
    return rows
