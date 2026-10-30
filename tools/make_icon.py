"""Generate assets/icon.ico for Quick Snake using only the Python stdlib.

Procedural pixel art (coiled green snake + red apple on a dark square),
rendered at 256x256 RGBA, nearest-neighbour scaled down to 48/32/16, and
packed into a PNG-in-ICO container (supported since Windows Vista).

Run directly (or let build.ps1 call it when the icon is missing):
    .venv\\Scripts\\python.exe tools\\make_icon.py
"""

import io
import os
import struct
import zlib

BG = (13, 17, 23, 255)  # dark navy background
SNAKE = (74, 222, 128, 255)  # green body
HEAD = (134, 239, 172, 255)  # lighter green head
EYE = (13, 17, 23, 255)  # dark eye
APPLE = (239, 68, 68, 255)  # red apple
STEM = (34, 197, 94, 255)  # green stem

# Coil path in 256x256 design coordinates, outer ring -> inner ring.
_COIL = [
    (56, 200), (200, 200), (200, 64), (64, 64),
    (64, 172), (172, 172), (172, 104), (116, 104),
]


def _render(size):
    """RGBA pixel matrix of the icon at the given square size."""
    px = [[BG for _ in range(size)] for _ in range(size)]
    s = size / 256.0

    def disc(cx, cy, r, color):
        if r <= 0:
            return
        r2 = r * r
        for y in range(max(0, int(cy - r) - 1), min(size, int(cy + r) + 2)):
            for x in range(max(0, int(cx - r) - 1), min(size, int(cx + r) + 2)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                    px[y][x] = color

    def line(x0, y0, x1, y1, r, color):
        dx, dy = x1 - x0, y1 - y0
        n = max(1, int((dx * dx + dy * dy) ** 0.5 / 2.0))
        for i in range(n + 1):
            t = i / n
            disc(x0 + dx * t, y0 + dy * t, r, color)

    # Snake body: stamped discs along the coil path.
    for a, b in zip(_COIL, _COIL[1:]):
        line(a[0] * s, a[1] * s, b[0] * s, b[1] * s, 14 * s, SNAKE)
    # Head at the inner end of the coil, plus one eye pixel.
    disc(104 * s, 104 * s, 22 * s, HEAD)
    disc(96 * s, 96 * s, 5 * s, EYE)
    # Apple resting in the open middle of the coil.
    disc(118 * s, 138 * s, 16 * s, APPLE)
    disc(118 * s, 120 * s, 4 * s, STEM)
    return px


def _png_bytes(size, px):
    """Encode an RGBA pixel matrix as PNG bytes (stdlib zlib only)."""
    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *px[y][x]) for x in range(size))
        for y in range(size)
    )

    def chunk(tag, data):
        block = tag + data
        return struct.pack(">I", len(data)) + block + struct.pack(
            ">I", zlib.crc32(block) & 0xFFFFFFFF
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def make_ico(path, sizes=(16, 32, 48, 256)):
    """Write a PNG-in-ICO file containing one entry per size."""
    images = [(size, _png_bytes(size, _render(size))) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    payload = b""
    for size, data in images:
        dim = 0 if size >= 256 else size  # 0 encodes 256 in the header byte
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        payload += data
        offset += len(data)
    with open(path, "wb") as handle:
        handle.write(header + entries + payload)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "assets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "icon.ico")
    make_ico(out_path)
    print("Wrote %s (%d bytes)" % (out_path, os.path.getsize(out_path)))


if __name__ == "__main__":
    main()
