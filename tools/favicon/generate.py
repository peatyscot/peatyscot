#!/usr/bin/env python3
"""
Generates peaty.scot's favicons.

Drawn directly at pixel sizes rather than rasterised from SVG: no rasteriser is
installed, and supersampling + LANCZOS gives better control of how the mark
degrades at 16px, which is the size that actually matters.

The mark matches the header .brand-mark in assets/css/main.css — an amber dram
disc — set on a dark peat ground so it holds against both light and dark
browser chrome.

    python3 tools/favicon/generate.py
"""
from PIL import Image, ImageDraw
import os

OUT = "static"
SS = 8  # supersample factor

GROUND = (26, 21, 18, 255)      # #1a1512 deep peat
AMBER_HI = (232, 164, 92, 255)  # #e8a45c
AMBER_LO = (164, 88, 26, 255)   # #a4581a
SHEEN = (255, 226, 190, 255)    # warm highlight


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def draw(size: int, rounded: bool = True) -> Image.Image:
    """Draw the mark at `size` px, supersampled."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Ground: rounded square, or full bleed for large touch icons.
    radius = int(s * 0.22) if rounded else 0
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=GROUND)

    # Dram disc, drawn as concentric rings to fake a radial gradient.
    cx, cy = s * 0.5, s * 0.52
    r = s * 0.30
    steps = max(24, int(r / 2))
    for i in range(steps, 0, -1):
        t = i / steps
        col = lerp(AMBER_HI, AMBER_LO, 1 - t)
        rr = r * t
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)

    # Offset sheen, upper-left, echoing the CSS radial-gradient highlight.
    hx, hy = cx - r * 0.34, cy - r * 0.38
    hr = r * 0.30
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=SHEEN)

    return img.resize((size, size), Image.LANCZOS)


def write_ico(path: str, sizes: list[int]) -> None:
    """Assemble a multi-image .ico with PNG-compressed frames."""
    import io
    import struct

    frames = []
    for n in sizes:
        buf = io.BytesIO()
        draw(n).save(buf, format="PNG")
        frames.append((n, buf.getvalue()))

    header = struct.pack("<HHH", 0, 1, len(frames))  # reserved, type=icon, count
    offset = len(header) + 16 * len(frames)
    entries, blobs = b"", b""
    for n, data in frames:
        entries += struct.pack(
            "<BBBBHHII",
            n if n < 256 else 0,  # width (0 means 256)
            n if n < 256 else 0,  # height
            0,                    # palette size
            0,                    # reserved
            1,                    # colour planes
            32,                   # bits per pixel
            len(data),
            offset,
        )
        blobs += data
        offset += len(data)

    with open(path, "wb") as f:
        f.write(header + entries + blobs)


def main():
    os.makedirs(OUT, exist_ok=True)

    # Multi-resolution .ico, written directly.
    #
    # Pillow's ICO plugin ignores append_images and would silently emit a
    # single frame, so the container is assembled by hand. Each size is drawn
    # at its own resolution rather than downsampled from one large render,
    # which matters most at 16px.
    write_ico(os.path.join(OUT, "favicon.ico"), [16, 32, 48])

    draw(180, rounded=False).save(os.path.join(OUT, "apple-touch-icon.png"))
    draw(192).save(os.path.join(OUT, "icon-192.png"))
    draw(512).save(os.path.join(OUT, "icon-512.png"))

    print("wrote favicon.ico (16/32/48), apple-touch-icon.png, icon-192.png, icon-512.png")

    # Legibility check: the 16px render is the one that has to survive.
    px = draw(16).convert("RGB")
    ramp = " .:-=+*#%@"
    print("\n16px preview:")
    for y in range(16):
        row = ""
        for x in range(16):
            r, g, b = px.getpixel((x, y))
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            row += ramp[min(len(ramp) - 1, int(lum * len(ramp)))] * 2
        print("   " + row)


if __name__ == "__main__":
    main()
