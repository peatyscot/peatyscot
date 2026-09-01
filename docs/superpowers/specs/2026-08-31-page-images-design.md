# Every page gets an image

**Status:** approved design, not yet implemented
**Date:** 2026-08-31

## Problem

`layouts/partials/head.html` emits no `og:image` and declares `twitter:card` as
`summary`. Every peaty.scot link shared anywhere renders as a bare text stub. The
site owns no imagery at all — `static/` holds favicons and nothing else.

The site is designed for ~5,000 bottling pages (README, stack spike). Any answer
that needs a human to choose an image per page does not survive that scale.

## Decisions

Four decisions were taken deliberately and constrain everything below.

| Decision | Chosen | Rejected, and why |
|---|---|---|
| Visual register | Generated cards for every page, plus real photographs where a free licence permits — including CC BY-SA | PD/CC0 only (too small a pool: most usable distillery photography is BY-SA). AI imagery (a photoreal render of a real distillery or a real bottle fabricates a depiction of a real thing — the visual form of what "never invent a tasting note" forbids) |
| Where PNGs are produced | Build time, one per page, hash-cached | Edge generation (`og:image` would point at no file, so offline linkcheck could no longer verify it). Sharing one card across a distillery's bottlings (a share would stop naming the bottling) |
| On-page use | Hero image *and* list thumbnails, not just social cards | Social-only (a vendored photo doing one job). Hero-only |
| Share-alike | Accepted: cards composited from a BY-SA photo are themselves offered under CC BY-SA 4.0 | Avoiding derivation by shipping the bare photo, or by keeping photos out of cards entirely |

### On share-alike specifically

CC BY-SA 2.0 requires adaptations to carry the same licence or a later version of
it. A card that composites a photograph with a title, a rule and a wordmark is an
adaptation, not a reproduction. Section 4(b) of BY-SA 2.0 permits distributing an
adaptation under a later version of the same licence, so CC BY-SA 4.0 is a valid
choice for cards derived from 2.0 photographs.

Geograph is the dominant source of UK distillery photography and is uniformly
BY-SA 2.0. This is the common case, not an edge case.

## Content model

Photographs attach to *places* only. No bottling will ever have a free-licensed
shot, so bottlings are excluded from the photo half of this design entirely.

`distilleries/`, `regions/` and `countries/` migrate to Hugo page bundles.
`whiskies/`, `glossary/` and `guides/` stay flat. `flavours/` already uses
`_index.md` bundles.

```
content/distilleries/macallan/
    index.md          # was content/distilleries/macallan.md
    photo.jpg         # committed, longest edge 1600px
```

Permalinks, `relref` targets and the published URL structure are all unchanged.
This is only where the bytes sit. It buys Hugo's `.Resources`, so the hero and
thumbnails get resizing and WebP without a second pipeline.

Front matter carries provenance only — the file itself is a page resource:

```yaml
image:
  alt: "The approach to The Macallan distillery and visitor centre"
  credit: "Peter Moore"
  source_url: "https://commons.wikimedia.org/wiki/File:Approach_to_the_Macallan_Distillery_%26_Visitor_Centre-geograph-6189211-by-Peter-Moore.jpg"
  license: "CC BY-SA 2.0"
  license_url: "https://creativecommons.org/licenses/by-sa/2.0"
```

The photograph is committed rather than cached for the same reason generated SKU
pages are committed: a fresh clone must build with no network, and a licence you
cannot diff is a licence nobody reviews. At ~250 KB × a few hundred places this
is tens of MB. Revisit if the place count ever reaches thousands.

## Vendoring — `npm run images:fetch`

A separate, network-touching step. **Never invoked by `build`.** A deploy must
not depend on Wikimedia being reachable.

```
front matter wikidata: Q982891
  → wbgetclaims P18            filename, or stop here permanently
  → imageinfo + extmetadata    licence, author, credit, description, dimensions
  → licence allowlist          cc0 · pd · cc-by-* · cc-by-sa-*
  → iiurlwidth=1600            photo.jpg written into the bundle
  → image: block               written into front matter as a reviewable diff
```

Verified working end to end against the live APIs on 2026-08-31. `Q982891`
resolves to `Approach to the Macallan Distillery & Visitor Centre-geograph-
6189211-by-Peter-Moore.jpg`, 2400×1350, `LicenseShortName: "CC BY-SA 2.0"`,
`Artist: "Peter Moore"`, `Credit: "From geograph.org.uk"`,
`AttributionRequired: "true"`.

Rules:

1. **An unrecognised licence is skipped, never guessed.** Anything outside the
   allowlist — non-free, fair-use, absent — logs and moves on. This mirrors the
   tri-state disclosure rule: silence is not a value.
2. **An existing `photo.*` is never overwritten**, so a hand-picked image always
   beats P18.
3. **A missing P18 is not an error.** That page keeps its typographic card.
4. **Alt text is not fabricated.** Proposed from `extmetadata.ImageDescription`
   where present; otherwise left unset, and validation fails until a human
   writes it. The script has not seen the photograph and must not describe it.
5. Requests carry a descriptive User-Agent with a contact address. Wikimedia
   blocks generic ones.

## Card renderer — `npm run images:cards`

`satori` (JSX-ish flexbox → SVG) → `@resvg/resvg-js` (SVG → PNG) → `sharp`
(JPEG encode for photo-backed cards, and the 1200×630 cover crop before
embedding). No browser. ~40 ms a card.

Rejected: Hugo's own `images.Text` — dependency-free, but it has no line wrapping,
which makes it unusable for a title of unknown length, and it cannot decode SVG.
Headless Chrome — would reuse the site CSS directly, but ~200 ms a page is ~20
minutes of build at 5,000 SKUs.

### Pipeline order

```
validate  →  hugo --minify  →  images:cards  →  linkcheck
                                (writes into public/og/)
```

Cards are generated *after* Hugo, straight into `public/`, so `linkcheck` sees
real files. They are not routed through Hugo Pipes: they are already exactly
1200×630 and re-processing 5,000 of them would add minutes for nothing.

### Card URLs have exactly one definition

Hugo renders `og:image` before the cards exist, so the URL must be derivable
from the page alone:

```
/og/<section>/<slug>.png    no photo   (flat colour, PNG compresses well)
/og/<section>/<slug>.jpg    photo      (photographic, JPEG q82)
```

An earlier draft had this rule stated twice — once in the template and once in
the Node generator — and accepted the divergence risk on the grounds that
`linkcheck` would catch it. Planning removed the duplication instead.

`layouts/partials/og-image.html` is the sole definition. `head.html` calls it for
the meta tag, and a Hugo-generated manifest (`public/og-manifest.json`) calls it
for the file path. The generator consumes `card` from the manifest and never
derives a path of its own, so there is no second rule to drift.

The manifest also settles a question Node could not have answered correctly:
which pages exist. `site.Pages` is Hugo's own canonical set, so section lists,
the taxonomy and its terms are all included, and paginated URLs — which are not
separate pages — are correctly absent. Re-deriving that from `content/` would
have missed a third of the site.

`linkcheck` still resolves every `og:image` against a real file. With one
definition it is verifying that two *tools* agree rather than that two copies of
a rule agree, which is the check actually worth having.

### Which pages get a card

Hugo generates considerably more pages than `content/` contains, so "every page"
needs enumerating rather than assuming:

| Page | Card |
|---|---|
| Entity and content pages | `/og/<section>/<slug>.{png,jpg}` |
| Home | `/og/home.png` |
| Section lists (`/whiskies/`) | `/og/<section>.png` |
| Taxonomy terms (`/flavours/peat-smoke/`) | `/og/flavours/<term>.png` |
| Paginated pages 2..n | inherit the section's card automatically |
| `404.html` | none; exempt |

A file `og/whiskies.png` and a directory `og/whiskies/` coexist without
collision, so section and entity cards need no separate namespace. Paginated
pages need no handling at all: Hugo already reports the section's own
`RelPermalink` when rendering `/whiskies/page/2/`, which is why they also
already canonicalise there.

Invariant 7 exempts `404.html` and nothing else — its `RelPermalink` is
`/404.html` rather than a directory, so the slug rule would not produce a sane
path for it, and nobody deliberately shares a 404. The exemption list lives beside
`UTILITY_SECTIONS` in `tools/validate/index.mjs`, which already carries this kind
of rule — note that the utility exemption there is about the interlinking floor
and does *not* imply an image exemption. `/about/` pages and `/explore` get
cards like anything else; they are shared like anything else.

### Cache

`.cache/og/<hash>.png`, gitignored. Hash covers the template version, both font
files, every card-relevant front-matter field, and the photo's own hash. A
template change invalidates everything; a steady-state build re-renders only what
actually changed. First full build at 5,000 SKUs is a few minutes parallelised
across cores.

### Layout

```
1200×630, --paper ground (#faf7f2), 48px optical margin

┌────────────────────────────────────────────────┐
│ ●  peaty.scot                      DISTILLERY  │
│                                                │
│    The Macallan                                │
│                                                │
│    Speyside · Scotland · founded 1824          │
│    ─────────────────────────────               │
│    sherry · vanilla                            │
└────────────────────────────────────────────────┘

with a photo: image fills the frame, a --peat-to-transparent
scrim carries the text, credit bottom-right —
"Peter Moore / CC BY-SA 2.0"
```

Title in Source Serif 4: 76px to 24 characters, 64px to 40, 56px beyond, clamped
to three lines with an ellipsis past that. Eyebrow, fact line and flavour tags in Source Sans 3. Both are SIL OFL
and come from npm as devDependencies — `@fontsource/source-serif-4` and
`@fontsource/source-sans-3`, which ship the `.woff` satori accepts (it does not
read `woff2`). Nothing is committed. Satori needs real font files, and the site's
own stack (Iowan Old Style, Palatino) is proprietary system fonts it cannot use.

One grid and one type scale for every kind. Kinds differ only in the eyebrow and
the fact line: a bottling shows `12 yr · 40% · Single Malt`, a region its
distillery count, a flavour a definition fragment, glossary and guides the
eyebrow alone.

## Template integration

- **`head.html`** — add `og:image` (absolute), `og:image:width`,
  `og:image:height`, `og:image:alt`; change `twitter:card` from `summary` to
  `summary_large_image`. This one line converts every existing share from a grey
  stub to a full-bleed card.
- **`partials/og-image.html`** — constructs the card URL from the page. Unlike
  `href.html` it never returns empty: every page must have a card, so there is no
  degraded case to represent. It cannot check the file exists — Hugo runs before
  the cards do — so verifying that is `linkcheck`'s job, not the template's.
- **`partials/hero.html`** — page opener from the bundle resource, `<picture>`
  with WebP and a JPEG fallback, and a real `<figcaption>` carrying credit and a
  linked licence. This is where BY-SA attribution is unambiguous and uncontested.
- **`partials/card.html`** — a `480x270` thumbnail, plus a designed fallback tile
  reusing the kind's eyebrow and accent so a mixed grid reads as intentional
  rather than broken.
- **`/about/image-credits/`** — generated, not hand-kept. Every vendored
  photograph with author, licence, and Commons link, and the statement that cards
  composited from a BY-SA photograph are offered under CC BY-SA 4.0.

## Guards

Following the existing two-guard split rather than inventing a third style.

**New invariant 7, in `tools/linkcheck`:** every page carries exactly one
`og:image`; it is absolute; it resolves to a real file under `public/`. Finding
zero across the whole site is a hard failure — the same discipline that already
protects the unquoted-attribute extractor.

**In `tools/validate/schema.mjs`:**

- An `image` object schema. When present, `credit`, `license`, `license_url` and
  `alt` are all required.
- A bundle containing `photo.*` must have an `image:` block, and an `image:`
  block must have a `photo.*`. Either alone is an error.
- The licence allowlist is enforced here too, not only at fetch time, so a
  hand-added photo cannot smuggle in an unlicensed file.

`CLAUDE.md` gains the invariant, the never-guess-a-licence rule, and the rule
that `build` never touches the network.

## Testing

- **Metadata mapper** — unit tested against a committed fixture of the real
  Commons `imageinfo` response for the Macallan file.
- **Licence allowlist** — `cc-by-sa-2.0` accepted; `fair use`, empty and unknown
  rejected. This is the rule with legal consequences, so it gets explicit cases.
- **Card renderer** — golden test over a fixture page: PNG magic bytes, exactly
  1200×630, and a stable hash for fixed input (satori and resvg are deterministic
  given the same fonts). A separate case asserts the credit line is present
  whenever the source photo requires attribution.
- **Invariant 7** — a fixture site with one `og:image` removed must exit 1.

## Phasing

Each phase ships independently and is useful on its own.

| Phase | Scope | Value |
|---|---|---|
| 1 | Typographic cards for all 38 pages, `head.html`, linkcheck invariant 7 | Every share stops being a text stub. No Commons dependency at all. |
| 2 | Bundle migration, `images:fetch`, validator rules, credits page | Photographs in the repo, licensed and reviewable. |
| 3 | Photo compositing into cards, hero partial, list thumbnails | The visual index. |

Phase 1 is most of the perceived benefit for a fraction of the work and is worth
doing even if 2 and 3 never happen.

The implementation plan should cover **phase 1 only**. Phases 2 and 3 get their
own plans once phase 1 is shipped and the card design has survived contact with
a real share preview.

## Risks and constraints

- **This commits to a paid Workers plan at scale.** Static assets cap at 20,000
  files on the free plan and 100,000 on paid. One card per page roughly doubles
  the file count; ~5,000 bottlings lands near 12,000 files, over the free limit.
  Nothing to do now — Wrangler 4.127 already supports the higher cap — but the
  cost follows directly from "one image per page" and should not arrive as a
  surprise.
- **Repo size.** Committed photographs are binary blobs git cannot delta. Tens of
  MB at a few hundred places; revisit past ~2,000.
- **First build cost.** The cache is empty once. Subsequent builds are cheap.
- **Wikimedia User-Agent policy.** Needs a real contact address before
  `images:fetch` is run in anger.
- **Two native dependencies** (`@resvg/resvg-js`, `sharp`). `@resvg/resvg-wasm`
  is the portable fallback if a CI environment ever makes native bindings
  awkward.

## Out of scope

- Bottle photography of any kind. Producer imagery is all rights reserved and
  there is no free-licensed equivalent.
- AI-generated depictions of real distilleries, places or products.
- Per-page hand-designed images.
- Retrofitting photographs onto bottling pages.
