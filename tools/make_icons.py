"""Generate LobangLeh PNG icons (stdlib only). Run: python tools/make_icons.py"""
import os
import struct
import zlib

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
RED = (200, 38, 38)
WHITE = (255, 255, 255)
YELLOW = (255, 200, 40)
TAG = [(0.22, 0.33), (0.60, 0.33), (0.80, 0.50), (0.60, 0.67), (0.22, 0.67)]


def in_poly(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def in_round(x, y, r):
    if x < 0 or y < 0 or x > 1 or y > 1:
        return False
    cx = min(max(x, r), 1 - r)
    cy = min(max(y, r), 1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def sample(x, y, rounded):
    """Return (r,g,b,a) at normalized point."""
    if rounded and not in_round(x, y, 0.22):
        return (0, 0, 0, 0)
    if (x - 0.33) ** 2 + (y - 0.5) ** 2 <= 0.045 ** 2:
        return RED + (255,)
    if in_poly(x, y, TAG):
        return WHITE + (255,)
    # kaya-yellow underline bar
    if 0.22 <= x <= 0.80 and 0.74 <= y <= 0.79:
        return YELLOW + (255,)
    return RED + (255,)


def render(size, rounded):
    ss = 3
    rows = []
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    c = sample((px + (sx + .5) / ss) / size, (py + (sy + .5) / ss) / size, rounded)
                    a = c[3]
                    acc[0] += c[0] * a
                    acc[1] += c[1] * a
                    acc[2] += c[2] * a
                    acc[3] += a
            if acc[3]:
                row += bytes([round(acc[0] / acc[3]), round(acc[1] / acc[3]), round(acc[2] / acc[3]), round(acc[3] / (ss * ss))])
            else:
                row += bytes([0, 0, 0, 0])
        rows.append(bytes(row))
    return b''.join(rows)


def png(size, rounded, path):
    raw = render(size, rounded)

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)

    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(data)


if __name__ == '__main__':
    png(192, True, os.path.join(OUT, 'icon-192.png'))
    png(512, True, os.path.join(OUT, 'icon-512.png'))
    png(180, False, os.path.join(OUT, 'apple-touch-icon.png'))
    print('ok')
