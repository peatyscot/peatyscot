#!/usr/bin/env python3
"""
Cuts a bottle photograph out of its background and lays it on the standard canvas.

    python3 tools/images/normalise.py <source> content/whiskies/<slug>/photo.png
    python3 tools/images/normalise.py <source> <dest> --preview out.png

Every bottle photograph on the site is the same pixel size with a transparent
ground, so the pages sit together rather than looking scavenged and the ground
stays a CSS decision rather than a property baked into each file.

Pillow only — no ImageMagick, no numpy, no matting model is installed here, the
same constraint that made tools/favicon/generate.py draw rather than rasterise.

The background is found by growing a region inward from the frame edge, with the
tolerance measured against the *neighbouring accepted pixel* rather than the
seed. That distinction is the whole trick: studio grounds are graduated, and a
seed-relative fill stalls partway round the bottle and leaves a band of ground
behind. `BAND` stops the growth wandering into the subject through a soft edge.

This will not rescue a photograph shot against a busy or dark background. Glass
is transparent, so whatever stood behind the bottle also stands *inside* it, and
a dark bottle on a dark ground has no boundary to find. That is a sourcing
problem, not a processing one: the script refuses rather than shipping a bottle
with holes in it. See .claude/skills/peatyscot-images/SKILL.md.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from collections import deque
import sys

CANVAS = (900, 1800)   # every bottle photograph, exactly
HEIGHT_FILL = 0.94     # subject height as a fraction of the canvas
WIDTH_MAX = 0.90       # a wide bottle scales to width instead

WORK_W = 700           # the mask is computed small, then scaled up: faster, and
                       # the upscale feathers the edge for free
STEP = 9               # tolerance against the neighbouring accepted pixel
BAND = 70              # tolerance against the median edge value, overall

# Refusal thresholds, measured against real Commons files. A clean cut of a
# studio shot keys ~70% of the frame and leaves a subject of aspect ~0.30; a
# frame holding a carton as well as a bottle comes out at 0.61.
KEYED_RANGE = (0.35, 0.90)
ASPECT_RANGE = (0.18, 0.60)

# Size and aspect alone pass a shredded cut: when the tone of the ground runs
# into the tone of the glass, the key eats the bottle and leaves floating scraps
# of label whose bounding box is still bottle-shaped. Both photographs in the
# repo failed exactly this way while measuring as plausible.
#
# What actually separates a cut-out from confetti is the silhouette. A bottle is
# one solid shape: every scanline crosses its edge exactly twice, and it fills
# most of its own bounding box. Measured — studio shot: solidity 0.73, median
# crossings 2. Red curtain: 0.13 and 4. Pine ground: 0.46 and 4.
MIN_SOLIDITY = 0.55
MAX_MEDIAN_CROSSINGS = 2


class Refused(Exception):
    """The cut is not good enough to write."""


def background_mask(im):
    """A mask that is 0 where the background is and 255 where the bottle is."""
    small = im.convert("L").resize(
        (WORK_W, round(WORK_W * im.height / im.width)), Image.LANCZOS
    )
    w, h = small.size
    px = small.load()

    edge = ([px[x, 0] for x in range(w)] + [px[x, h - 1] for x in range(w)]
            + [px[0, y] for y in range(h)] + [px[w - 1, y] for y in range(h)])
    ref = sorted(edge)[len(edge) // 2]

    seen = bytearray(w * h)
    queue = deque()

    def seed(x, y):
        if not seen[y * w + x] and abs(px[x, y] - ref) <= BAND:
            seen[y * w + x] = 1
            queue.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    while queue:
        x, y = queue.popleft()
        here = px[x, y]
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                there = px[nx, ny]
                if abs(there - here) <= STEP and abs(there - ref) <= BAND:
                    seen[ny * w + nx] = 1
                    queue.append((nx, ny))

    keyed = sum(seen) / len(seen)
    mask = Image.frombytes("L", (w, h), bytes(0 if s else 255 for s in seen))
    mask = mask.filter(ImageFilter.MedianFilter(5))          # despeckle
    mask = mask.resize(im.size, Image.LANCZOS)               # and feather
    return mask.filter(ImageFilter.GaussianBlur(1.2)), keyed


def silhouette(subject):
    """How solid the cut-out is, and how many times a scanline crosses its edge."""
    alpha = subject.getchannel("A")
    w, h = alpha.size
    px = alpha.load()
    rows = range(0, h, 4)
    opaque = 0
    crossings = []
    for y in rows:
        run = [1 if px[x, y] > 128 else 0 for x in range(w)]
        opaque += sum(run)
        crossings.append(sum(1 for i in range(1, w) if run[i] != run[i - 1]))
    crossings.sort()
    return opaque / (w * len(rows)), crossings[len(crossings) // 2]


def normalise(src_path):
    im = ImageOps.exif_transpose(Image.open(src_path))

    if im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 255:
        cut, keyed = im.convert("RGBA"), None   # already cut out elsewhere
    else:
        mask, keyed = background_mask(im.convert("RGB"))
        if not KEYED_RANGE[0] <= keyed <= KEYED_RANGE[1]:
            raise Refused(
                f"keyed {keyed:.0%} of the frame, outside "
                f"{KEYED_RANGE[0]:.0%}-{KEYED_RANGE[1]:.0%} — the background is "
                f"too close in tone to the bottle to separate. Source a "
                f"photograph shot on a plain seamless ground instead."
            )
        cut = im.convert("RGBA")
        cut.putalpha(mask)

    box = cut.getbbox()
    if box is None:
        raise Refused("nothing left after keying")
    subject = cut.crop(box)
    aspect = subject.width / subject.height
    if not ASPECT_RANGE[0] <= aspect <= ASPECT_RANGE[1]:
        raise Refused(
            f"subject is {subject.width}x{subject.height} (aspect {aspect:.2f}), "
            f"outside {ASPECT_RANGE[0]}-{ASPECT_RANGE[1]} — that is not a bottle. "
            f"Either the background survived the cut, or the frame holds a carton "
            f"or a second bottle."
        )

    solidity, median_crossings = silhouette(subject)
    if solidity < MIN_SOLIDITY or median_crossings > MAX_MEDIAN_CROSSINGS:
        raise Refused(
            f"the cut is in pieces — solidity {solidity:.2f} (want "
            f"{MIN_SOLIDITY}+), scanlines cross the edge {median_crossings} times "
            f"(want {MAX_MEDIAN_CROSSINGS}). The ground is too close in tone to the "
            f"glass, so the key ate the bottle. No threshold rescues this; source a "
            f"photograph shot on a plain seamless ground."
        )

    cw, ch = CANVAS
    scale = (ch * HEIGHT_FILL) / subject.height
    if subject.width * scale > cw * WIDTH_MAX:
        scale = (cw * WIDTH_MAX) / subject.width
    subject = subject.resize(
        (round(subject.width * scale), round(subject.height * scale)), Image.LANCZOS
    )

    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.paste(subject, ((cw - subject.width) // 2, (ch - subject.height) // 2), subject)

    corners = [canvas.getpixel(p)[3] for p in
               ((0, 0), (cw - 1, 0), (0, ch - 1), (cw - 1, ch - 1))]
    if any(corners):
        raise Refused(f"canvas corners are not transparent: {corners}")

    return canvas, keyed, subject.size, solidity


def preview(canvas, path):
    """The cut-out on a checkerboard and on the site's dark ground, side by side.

    Someone has to look at this. Invariant 7 says alt text is written by a person
    who has seen the photograph; a cut-out is a new photograph, and its holes and
    haloes only show against a ground that is not the one it was shot on.
    """
    cw, ch = canvas.size
    cell = 60
    left = Image.new("RGB", canvas.size, (255, 255, 255))
    draw = ImageDraw.Draw(left)
    for y in range(0, ch, cell):
        for x in range(0, cw, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(205, 205, 205))
    right = Image.new("RGB", canvas.size, (20, 17, 15))   # --paper in dark mode
    left.paste(canvas, (0, 0), canvas)
    right.paste(canvas, (0, 0), canvas)

    strip = Image.new("RGB", (cw * 2, ch))
    strip.paste(left, (0, 0))
    strip.paste(right, (cw, 0))
    strip.resize((900, round(900 * ch / (cw * 2))), Image.LANCZOS).save(path)


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__.strip())
    src, dest = argv[1], argv[2]
    if not dest.endswith(".png"):
        sys.exit("dest must be a .png — a cut-out in JPEG has no alpha channel")

    try:
        canvas, keyed, size, solidity = normalise(src)
    except Refused as why:
        sys.exit(f"refused: {why}")

    canvas.save(dest)
    keyed_note = f"keyed {keyed:.0%}, " if keyed is not None else "already cut out, "
    print(f"{dest}: {keyed_note}subject {size[0]}x{size[1]} on "
          f"{CANVAS[0]}x{CANVAS[1]}, solidity {solidity:.2f}")

    if "--preview" in argv:
        out = argv[argv.index("--preview") + 1]
        preview(canvas, out)
        print(f"{out}: look at this before you write the alt text")


if __name__ == "__main__":
    main(sys.argv)
