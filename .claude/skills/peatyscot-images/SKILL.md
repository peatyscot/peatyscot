---
name: peatyscot-images
description: Use when obtaining, licensing or normalising a whisky bottle photograph for peaty.scot — searching Wikimedia Commons for a free-licensed shot, judging whether it can be cut out, laying it on the standard transparent canvas, and recording its provenance and modification.
---

# Bottle photographs on peaty.scot

Every bottle photograph on the site is **900 × 1800 px, PNG, transparent ground**, with the
bottle 94% of the canvas height and centred. Uniform, so pages sit together instead of
looking scavenged; transparent, so the ground behind a bottle stays a CSS decision rather
than a property baked into the file.

This covers bottlings only. A distillery or landscape photograph keeps its background —
cutting a building out of its glen would be a lie about the place.

## 1. Find a candidate on Commons

Commons is the first and usually the only source. `Category:Whisky bottles` holds ~223
files across ~70 brands.

```sh
# What exists for a brand
curl -sS -m 30 -G "https://commons.wikimedia.org/w/api.php" \
  --data-urlencode "action=query" --data-urlencode "format=json" \
  --data-urlencode "list=categorymembers" \
  --data-urlencode "cmtitle=Category:Ardbeg bottles" --data-urlencode "cmlimit=100"

# Licence, author, dimensions, and a thumbnail URL you can actually fetch
curl -sS -m 30 -G "https://commons.wikimedia.org/w/api.php" \
  --data-urlencode "action=query" --data-urlencode "format=json" \
  --data-urlencode "titles=File:Ardbeg 10 Jahre Flasche.jpg" \
  --data-urlencode "prop=imageinfo" \
  --data-urlencode "iiprop=url|size|extmetadata" --data-urlencode "iiurlwidth=1920"
```

Download the `thumburl` the API hands back, verbatim. Wikimedia's thumbnailer serves only
certain widths — a hand-built URL at an arbitrary width returns HTTP 400 and an HTML error
page, which Pillow reports as "cannot identify image file", naming the file rather than
the refusal. The API rounds `iiurlwidth` up to a width that exists, so ask for what you
want and use what you get: `iiurlwidth=1400` came back as a 1920px thumbnail.

## 2. Three tests, in this order

A candidate must pass all three. The first two are judgement; only the third is new.

**Does it show the expression the page names?** Read the label. Commons' `Macallan 12.jpg`
is Fine Oak, not Double Cask, and metadata will never tell you that — attaching it would
be the visual form of inventing a fact. This test is why a human picks the file.

**Is the bottle alone in the frame?** A carton, a second bottle, a filled glass or a
presentation tin all break the uniform silhouette. `Ardbeg Ten.jpg` is a good photograph
of a bottle *and its box*; the normaliser refuses it on aspect ratio.

**Is it shot on a plain, seamless ground?** This is what makes the cut-out possible, and
it is the test that decides most candidates. Glass is transparent: whatever stood behind
the bottle also stands inside it. A bottle photographed against a red curtain or a pine
wall cannot be separated from it — the tone of the ground runs into the tone of the glass,
and the key eats the bottle. Look for a white, grey or otherwise even studio ground. A
soft gradient is fine; the normaliser follows one.

Then the rules that already applied to any photograph: the licence must be on the
allowlist in `tools/validate/schema.mjs` — CC0, public domain, `CC BY-*`, `CC BY-SA-*` —
and silence is not a licence. Nothing outside the allowlist, ever, and nothing guessed.

If Commons has nothing, [Open Food Facts](https://world.openfoodfacts.org/terms-of-use)
licenses its product photographs CC BY-SA 3.0 and exists to be reused. Whisky coverage
there is unverified. Producer and retailer imagery stays out: all rights reserved, and a
press or affiliate grant is revocable, so it is not a licence this repo can record.

## 3. Cut it out and lay it on the canvas

```sh
python3 tools/images/normalise.py <source.jpg> content/whiskies/<slug>/photo.png \
  --preview /tmp/preview.png
```

The tool grows a region inward from the frame edge, measuring tolerance against the
neighbouring accepted pixel rather than the seed — a seed-relative fill stalls partway
around a graduated studio ground and leaves a band behind. Then it trims, scales and
centres on the canvas.

**It refuses rather than writing a bad cut.** The refusals are the point of the tool:

| Refusal | What it means |
|---|---|
| `the cut is in pieces` | The ground ran into the glass and the key ate the bottle. Solidity and edge-crossings measure this; size and aspect alone pass a shredded cut, which is how both photographs currently in the repo measured as plausible while being confetti. Find a different photograph — no threshold rescues it. |
| `that is not a bottle` | The background survived the cut, or there is a carton or second bottle in the frame. |
| `keyed N% of the frame` | The ground is too close in tone to the bottle to separate at all. |
| `the cut is in N pieces` | The largest connected piece is not substantially all of the cut-out. Something belonging to the bottle keyed away and left the rest floating — most often clear glass in the neck, which shows the ground straight through it. Solidity and crossings are measured per scanline and miss this entirely: a capsule floating above a headless bottle still crosses every scanline exactly twice. |
| `the ground survived as a halo` | The silhouette is whole but rimmed with background: the mask is computed at `WORK_W` and upscaled, so its boundary lands outside the true edge and those pixels keep RGB that is part glass, part ground. `ERODE` pulls the boundary inside the bottle and normally settles this; the refusal means the photograph's edge is softer than the erosion can absorb. This one is invisible in the source — a pale rim against a pale studio ground — and obvious on the site. |

Then **look at the preview**. It shows the cut-out on a checkerboard and on the site's
dark ground, because holes and haloes only show against a ground the photograph was not
shot on. A cut that passes every numeric check can still have a chewed edge.

The numbers to read in the tool's own line: `keyed` near 70%, `solidity` above 0.55, and
`edge bleed` — how far the boundary sits from the bottle towards the ground, 0% being a
boundary the colour of the glass and 100% a boundary that is simply background. The Ardbeg
runs 17%. Anything approaching the 30% limit is worth looking at closely even though it
passes.

## 3b. When no photograph of the expression exists

A page with no free-licensed photograph of *its own* expression may carry a rendered
illustration instead — never in the photograph's place, only where the photograph slot
is empty. `tools/images/illustrate.py` takes the real free-licensed photographs that do
exist as references, and the render goes through the same `normalise.py` canvas, so the
pages sit together.

```sh
python3 tools/images/illustrate.py <slug> --refs <dir> --out /tmp/raw.png --tries 4
```

Generation is stochastic, so the tool samples candidates and keeps the first that
survives the cut. The gate does the choosing; do not loosen it to rescue a draw.

The result goes in `illustration.png` under an `illustration:` block — a separate shape
from `image:`, carrying `model`, `generated`, a `note` saying plainly what it is not,
and the `references` it was derived from. `hero.html` renders it under a caption
beginning **"Illustration, not a photograph."** Free-licensed references still carry
attribution, and naming them is what makes a render auditable.

Two rules hold. A render never displaces a real photograph of the right expression, even
a poor one — Lagavulin 16 keeps its uncuttable pine-background shot. And where the
references are of the *wrong* expression, the label must be blank: a first Macallan run
inherited its references and rendered "FINE OAK / TRIPLE CASK MATURED" in crisp type on
a Double Cask page, which is the failure a caption cannot excuse.

Some bottles will not survive this at all. Yoichi's pale amber body, cream label and
clear glass neck sit too close to any plain ground the model gives it; ten candidates
across two prompts were all refused, and that is a sourcing answer, not a retry answer.

## 4. Record provenance, and that you modified it

Same `image:` block as any photograph, plus one field, because a cut-out is an adaptation
and not the photographer's original:

```yaml
image:
  alt: "…"                       # written by whoever looked at the preview
  credit: "DYVER"
  source_url: "https://commons.wikimedia.org/wiki/File:Ardbeg_10_Jahre_Flasche.jpg"
  license: "CC BY-SA 4.0"
  license_url: "https://creativecommons.org/licenses/by-sa/4.0"
  modified: "background removed, laid on a 900×1800 transparent canvas"
```

Under CC BY you must indicate that you changed the work; under CC BY-SA the cut-out itself
carries the source's licence. The design spec already accepted share-alike for composited
cards — this is the same acceptance one step earlier.

Write the alt text **from the cut-out, not the original frame**. The two photographs in
the repo have alt text ending "against a red curtain" and "against a pine background";
after a cut those sentences describe something the reader cannot see. Describe the bottle
and its label.

## 5. Validate

```sh
npm run check
```

Invariant 7 still applies in both directions: a `photo.*` with no `image:` block and an
`image:` block with no `photo.*` each fail the build.

## What is not built yet

Say so rather than implying otherwise:

- **The repo-side gate.** `tools/validate/` does not yet check that a bottling's photograph
  is a 900 × 1800 PNG with an alpha channel. That check is cheap and dependency-free —
  the PNG IHDR chunk carries width, height and colour type in its first 26 bytes — and it
  should be added. Until it is, the standard is enforced only by the normaliser at ingest,
  so a hand-added JPEG would pass.
- **`modified:` is not in the schema.** Zod strips unknown keys, so writing it today is
  accepted and ignored. Adding it to `image` in `tools/validate/schema.mjs` should make it
  required whenever the file has an alpha channel.
- **The ground is transparent but nothing uses that yet.** `.page-photo img` in
  `assets/css/main.css` paints `--paper-2` behind the image in a rounded rectangle, which
  a JPEG hid entirely. Now it shows through as a panel behind the bottle. That is a design
  decision to make deliberately — a panel, the page ground, or a tinted plinth — and it is
  the decision the transparent canvas exists to make possible.
- **`hero.html` does not render the modification.** Its `<figcaption>` names credit and
  licence only. It also builds a variable called `$jpg` from `.Resize "x560 q82"`, which
  keeps the source format and so happens to be a PNG — but naming `jpg` in a resize spec
  would flatten the transparency to Hugo's `bgColor`, silently, which is the whole thing
  this standard exists to avoid.
- **Both photographs in the repo fail this standard.** They are JPEGs shot against a
  curtain and a pine wall, and neither can be cut out. `Ardbeg 10 Jahre Flasche.jpg`
  (CC BY-SA 4.0, DYVER, 3547 × 5321, plain grey studio ground) is a verified replacement
  for the Ardbeg; the Lagavulin needs a search. Turning on the repo-side gate before
  replacing them would fail the build.
