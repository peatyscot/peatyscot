#!/usr/bin/env python3
"""
Renders a bottle illustration from real reference photographs.

    python3 tools/images/illustrate.py <slug> --out /tmp/raw.png

This produces an *illustration*, never a photograph, and the distinction is the
whole reason the file exists. A bottling with a free-licensed photograph of the
right expression gets the photograph; `tools/images/normalise.py` cuts it out and
`image:` records who took it. Three bottlings have no such photograph and are not
going to acquire one, so they get a render instead — under a separate
`illustration:` block, in a separate `illustration.png` resource, behind a caption
that says what it is. See the 2026-09-04 narrowing in
docs/superpowers/specs/2026-08-31-page-images-design.md.

The references are real, free-licensed photographs of the actual bottling, passed
to the model together so the render inherits a real bottle's proportions, glass
colour and label layout rather than a model's idea of a whisky bottle. Every
reference is recorded in the page's front matter: CC BY-SA inputs that materially
shape an output still carry attribution, and recording them is also what makes a
render auditable rather than a thing that simply appeared.

Output goes on a plain studio ground on purpose, so it passes through the same
normalise.py canvas as every photograph and the pages sit together.

Needs REPLICATE_API_TOKEN. Pillow only, plus stdlib — same constraint as the rest
of tools/.
"""
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import normalise

MODEL = "google/nano-banana"
REF_MAX = 1024          # references are downscaled before upload; the model reads
                        # shape and label layout, not pixels
POLL_SECONDS = 3
TIMEOUT = 300

# The ground is specified, not left to the model, because the render goes through
# normalise.py afterwards and that tool keys on a plain seamless ground. Asking
# for a dark or textured backdrop would produce a render the pipeline refuses.
GROUND = (
    "The bottle stands alone on a plain seamless light grey studio background, "
    "evenly lit, no box, no carton, no glass, no props, no text overlay, "
    "no reflections on the floor, full bottle visible from capsule to base, "
    "centred, shot straight on."
)

BOTTLINGS = {
    "lagavulin-16-year-old": {
        "refs": [
            "lagavulin-ck.jpg",      # front label, colour, in daylight
            "lagavulin-cc0.jpg",     # second angle
            "off-lagavulin-b.jpg",   # label close up
            "rfid-3170.jpg",         # same bottle, plain studio ground, shape
        ],
        "subject": (
            "A 70cl Lagavulin 16 year old Islay single malt Scotch whisky bottle: "
            "dark olive-green glass, deep amber whisky, a dark green capsule over "
            "the neck, and a cream front label with a small oval vignette above it."
        ),
    },
    "yoichi-single-malt": {
        "refs": [
            "off-yoichi-a.jpg",      # the current no-age-statement label, close
            "yoichi-bottle.jpg",     # Yoichi bottle form on a studio ground
            "yoichi-woody.jpg",      # glass colour and capsule
        ],
        # The empty clear glass in this bottle's neck shows the ground straight
        # through it, so the key walked down the neck and the cut came back with
        # the capsule floating free above a headless bottle. Asking for a dark
        # ground made it worse, not better: the model lit the bottle to match, and
        # a dark bottle on a dark ground has no boundary to find at all — solidity
        # fell to 0.52 and the glass vanished entirely, leaving the label. The fix
        # is not the ground but the transparent region: fill the neck.
        "subject": (
            "A 70cl Nikka Yoichi single malt Japanese whisky bottle: squat "
            "round-shouldered glass holding deep dark reddish-amber whisky, a "
            "brown-gold capsule, and a large cream label carrying two bold brushed "
            "Japanese characters."
        ),
        "extra": (
            "The whisky is dark and richly coloured so the bottle reads clearly "
            "darker than the background at every point. The bottle is filled right "
            "up to the base of the capsule and the capsule covers the whole neck, "
            "so no empty clear glass shows anywhere. The label's small print is "
            "softly out of focus and not readable. Do not render any legible "
            "numbers, percentages, ages, volumes or addresses anywhere."
        ),
    },
    # No free-licensed photograph of Double Cask exists; every Macallan reference
    # available is Fine Oak or Triple Cask. A first run inherited that and rendered
    # "FINE OAK / TRIPLE CASK MATURED" in crisp legible type — the wrong expression
    # asserted clearly, which is precisely the failure the caption cannot excuse.
    # So the references here carry bottle form only and the label is required blank.
    "macallan-double-cask-12-year-old": {
        "refs": [
            "macallan-12.jpg",       # bottle form and proportions only
            "macallan-new.png",      # current bottle shape
        ],
        "subject": (
            "A 70cl Macallan Highland single malt Scotch whisky bottle: the "
            "distinctive squat rounded Macallan bottle in clear glass, warm amber "
            "whisky, a dark capsule over the neck, and a plain unprinted pale cream "
            "front label of warm mid-tone tan kraft paper, clearly darker than the "
            "white background, bearing no words, no lettering and no emblem at all."
        ),
        # This one needs its ground chosen against normalise.py's keyer rather than
        # for looks, and it took two failures to see why. The bottle spans nearly
        # the whole luma range — near-black capsule, amber body, pale label — and
        # BAND is 70, so any ground within 70 of *any* part of it leaks. A light
        # ground (198) sat inside the blank cream label (235) and the fill reached
        # the label through the pale glass at the bottle's edge, eating its middle:
        # refused for solidity 0.31. A mid grey (104-127) landed on the capsule
        # (112) and body (115): refused for keying 93%. Near-white ground against a
        # deliberately mid-tone label clears everything by 95 or more.
        "ground": (
            "The bottle stands alone on a plain seamless bright white studio "
            "background, evenly lit, no box, no carton, no glass, no props, no text "
            "overlay, no shadow or reflection on the floor, full bottle visible "
            "from capsule to base, centred, shot straight on."
        ),
        "extra": (
            "The label must be completely blank cream paper. Render no words, no "
            "letters, no numbers and no crest on the label or anywhere in the image. "
            "The whole bottle from the top of the capsule to the base of the glass "
            "must be inside the frame with clear space above and below it."
        ),
    },
}

# Label text is asked for as *unresolved* deliberately. A diffusion model renders
# fine print as convincing gibberish, and gibberish that looks like an ABV or an
# age statement is the one thing a render on a facts page must not do. Out-of-focus
# lettering says "illustration" honestly; invented lettering asserts something false.
LEGIBILITY = (
    "The label's small print is softly out of focus and not readable. Do not render "
    "any legible numbers, percentages, ages, volumes or addresses anywhere."
)

STYLE = (
    "Photorealistic product photograph style, sharp focus on the bottle, "
    "shallow depth of field on the label's fine print, neutral colour, "
    "vertical portrait composition."
)


def data_uri(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((REF_MAX, REF_MAX), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def call(token, prompt, refs):
    body = json.dumps({
        "input": {
            "prompt": prompt,
            "image_input": refs,
            "output_format": "png",
            "aspect_ratio": "9:16",
        }
    }).encode()
    req = urllib.request.Request(
        f"https://api.replicate.com/v1/models/{MODEL}/predictions",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        },
    )
    # Sampling several candidates in a row trips Replicate's rate limit, and a 429
    # is a "wait", not a failure — treat it as one rather than losing the run.
    for backoff in (0, 15, 30, 60, 120):
        if backoff:
            print(f"  rate limited, waiting {backoff}s")
            time.sleep(backoff)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                pred = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    else:
        sys.exit("rate limited past every backoff; try again later")

    waited = 0
    while pred.get("status") in ("starting", "processing") and waited < TIMEOUT:
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        get = urllib.request.Request(
            pred["urls"]["get"], headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(get, timeout=60) as r:
            pred = json.load(r)

    if pred.get("status") != "succeeded":
        sys.exit(f"generation {pred.get('status')}: {pred.get('error')}")
    return pred


def main(argv):
    if len(argv) < 2 or argv[1] not in BOTTLINGS:
        sys.exit(f"{__doc__.strip()}\n\nknown slugs: {', '.join(BOTTLINGS)}")

    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        sys.exit("REPLICATE_API_TOKEN is not set")

    slug = argv[1]
    out = argv[argv.index("--out") + 1] if "--out" in argv else f"/tmp/{slug}.png"
    ref_dir = argv[argv.index("--refs") + 1] if "--refs" in argv else "."
    tries = int(argv[argv.index("--tries") + 1]) if "--tries" in argv else 4

    spec = BOTTLINGS[slug]
    paths = [os.path.join(ref_dir, r) for r in spec["refs"]]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        sys.exit("missing reference photographs:\n  " + "\n  ".join(missing))

    prompt = " ".join(
        (spec["subject"], spec.get("ground", GROUND),
         spec.get("extra", LEGIBILITY), STYLE)
    )
    refs = [data_uri(p) for p in paths]
    print(f"{slug}: {len(paths)} references -> {MODEL}, up to {tries} candidates")

    # Generation is stochastic: the same prompt gives a differently lit bottle each
    # time, and whether normalise.py can key it turns on tonal relationships the
    # prompt does not control. Prompt-tuning against that is tuning against noise.
    # So sample, and let the gate that already exists do the choosing — a candidate
    # counts only if it survives the same cut every photograph on the site goes
    # through. The refusals stay exactly as strict; this only stops one unlucky
    # draw from looking like a dead end.
    rejected = []
    for attempt in range(1, tries + 1):
        if attempt > 1:
            time.sleep(10)
        pred = call(token, prompt, refs)
        url = pred["output"] if isinstance(pred["output"], str) else pred["output"][0]
        with urllib.request.urlopen(url, timeout=120) as r:
            raw = r.read()
        open(out, "wb").write(raw)
        try:
            _, keyed, size, solidity, bleed = normalise.normalise(out)
        except normalise.Refused as why:
            print(f"  candidate {attempt}: {why}")
            rejected.append(str(why).split(" — ")[0])
            continue
        print(f"{out}: candidate {attempt} keyed {keyed:.0%}, subject "
              f"{size[0]}x{size[1]}, solidity {solidity:.2f}, edge bleed {bleed:.0%}")
        print(f"  prediction {pred['id']}  "
              f"(audit trail; the references are in front matter)")
        return

    sys.exit(
        f"no candidate in {tries} survived the cut:\n  "
        + "\n  ".join(rejected)
        + "\nThat is a sourcing answer, not a retry answer: this bottle's tones "
          "are too close to the ground the model keeps giving it."
    )


if __name__ == "__main__":
    main(sys.argv)
