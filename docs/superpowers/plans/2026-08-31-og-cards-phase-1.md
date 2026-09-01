# OG Cards, Phase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every page on peaty.scot carries a generated 1200×630 typographic social card, and the build fails if any page does not.

**Architecture:** Hugo emits a manifest of every canonical page (`public/og-manifest.json`) using the same partial that writes the `og:image` tag, so the card URL has exactly one definition. A Node step then renders each manifest entry through satori → resvg into `public/og/`, hash-cached so unchanged pages do not re-render. `tools/linkcheck` gains invariant 7: every page has exactly one absolute `og:image` resolving to a real file.

**Tech Stack:** Hugo 0.159 extended · Node 22 (`node:test`, no test framework) · satori 0.33.4 · @resvg/resvg-js 2.6.2 · @fontsource/source-serif-4 + @fontsource/source-sans-3 (5.3.0, `.woff`)

**Spec:** `docs/superpowers/specs/2026-08-31-page-images-design.md`

## Global Constraints

- **Phase 1 only.** No photographs, no Wikidata/Commons fetching, no page-bundle migration, no hero or thumbnail partials. Every card is typographic and every card is `.png`. Phases 2 and 3 get their own plans.
- **The build never touches the network.** No step added here may make an HTTP request.
- **Never weaken a validator or linkcheck rule to get a build green.** Fix the content or the generator.
- **`npm run check` must pass before any deploy.** It is not advisory.
- **The card URL has exactly one definition:** `layouts/partials/og-image.html`. Node never derives a card path; it only consumes `card` from the manifest.
- **A checker that finds nothing must fail.** Any new check counts what it inspected and exits non-zero on zero, matching the existing extractor discipline in `tools/linkcheck/index.mjs`.
- Card dimensions are exactly **1200×630**. Palette values are copied verbatim from `assets/css/main.css` light theme: paper `#faf7f2`, ink `#1e1a16`, ink-2 `#574e45`, ink-3 `#857a6e`, rule `#ddd3c5`, accent `#9d5420`, peat `#2f2620`.
- Cards are build output. They live under `public/og/` and are never committed. `.cache/` is gitignored.

---

### Task 1: Card design module and test harness

Pure functions only — what a card *says*, with no rendering. This is where every design decision lives, so it must be testable without satori.

**Files:**
- Create: `tools/images/card.mjs`
- Create: `tools/images/card.test.mjs`
- Modify: `package.json` (add `test` script)

**Interfaces:**
- Consumes: nothing.
- Produces: `TEMPLATE_VERSION: number`, `PALETTE: object`, `eyebrowFor(entry) -> string`, `factsFor(entry) -> string[]`, `titleSize(title) -> number`, `cardTree(entry) -> object` (a satori element tree).
- A **manifest entry** is the object shape produced by Task 3 and consumed here:
  ```
  { url, card, kind, section, title,
    abv: number, age: number, category: string, founded: number,
    spirit: string, count: number, region: string, country: string,
    flavours: string[] }
  ```
  `kind` is one of `home`, `page`, `section`, `taxonomy`, `term`.

- [ ] **Step 1: Add the test script**

In `package.json`, add to `scripts`:

```json
"test": "node --test",
```

Node 22's runner discovers `*.test.mjs` and skips `node_modules` by default.

- [ ] **Step 2: Write the failing tests**

Create `tools/images/card.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { eyebrowFor, factsFor, titleSize, cardTree, TEMPLATE_VERSION } from "./card.mjs";

const whisky = {
  url: "/whiskies/ardbeg-10-year-old/", card: "/og/whiskies/ardbeg-10-year-old.png",
  kind: "page", section: "whiskies", title: "Ardbeg 10 Year Old",
  abv: 46, age: 10, category: "Single Malt Scotch Whisky", founded: 0,
  spirit: "", count: 0, region: "Islay", country: "Scotland",
  flavours: ["Peat smoke", "Iodine"],
};

const distillery = {
  ...whisky, url: "/distilleries/macallan/", card: "/og/distilleries/macallan.png",
  section: "distilleries", title: "The Macallan", abv: 0, age: 0, category: "",
  founded: 1824, region: "Speyside", country: "Scotland", flavours: ["Sherry"],
};

test("eyebrow names the kind, not the section, for non-page kinds", () => {
  assert.equal(eyebrowFor({ ...whisky, kind: "home", section: "" }), "Whiskies of the World");
  assert.equal(eyebrowFor({ ...whisky, kind: "term", section: "flavours" }), "Flavour");
  assert.equal(eyebrowFor({ ...whisky, kind: "section", section: "whiskies" }), "Index");
  assert.equal(eyebrowFor({ ...whisky, kind: "taxonomy", section: "flavours" }), "Index");
  assert.equal(eyebrowFor(whisky), "Bottling");
  assert.equal(eyebrowFor(distillery), "Distillery");
});

test("eyebrow falls back rather than throwing on an unknown section", () => {
  assert.equal(eyebrowFor({ ...whisky, section: "nonesuch" }), "peaty.scot");
});

test("facts are section-specific and skip absent values", () => {
  assert.deepEqual(factsFor(whisky), ["10 yr", "46%", "Single Malt Scotch Whisky"]);
  assert.deepEqual(factsFor({ ...whisky, age: 0 }), ["46%", "Single Malt Scotch Whisky"]);
  assert.deepEqual(factsFor(distillery), ["Speyside", "Scotland", "founded 1824"]);
  assert.deepEqual(
    factsFor({ ...distillery, section: "regions", country: "Scotland", count: 9 }),
    ["Scotland", "9 distilleries"]
  );
  assert.deepEqual(
    factsFor({ ...distillery, section: "countries", spirit: "Scotch whisky" }),
    ["Scotch whisky"]
  );
});

test("pages with no facts to show produce an empty list, not a placeholder", () => {
  assert.deepEqual(factsFor({ ...whisky, section: "glossary" }), []);
  assert.deepEqual(factsFor({ ...whisky, kind: "section" }), []);
});

test("title size steps down by length", () => {
  assert.equal(titleSize("Ardbeg 10 Year Old"), 76);
  assert.equal(titleSize("The Macallan Double Cask 12 Years"), 64);
  assert.equal(titleSize("A title considerably longer than forty characters"), 56);
});

test("cardTree carries the title and is a flex column", () => {
  const tree = cardTree(whisky);
  assert.equal(tree.props.style.display, "flex");
  assert.equal(tree.props.style.flexDirection, "column");
  assert.equal(tree.props.style.width, "1200px");
  assert.equal(tree.props.style.height, "630px");
  assert.ok(JSON.stringify(tree).includes("Ardbeg 10 Year Old"));
  assert.ok(JSON.stringify(tree).includes("Single Malt Scotch Whisky"));
});

test("TEMPLATE_VERSION is an integer so the cache can key on it", () => {
  assert.equal(Number.isInteger(TEMPLATE_VERSION), true);
});
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `npm test`
Expected: FAIL — `Cannot find module './card.mjs'`

- [ ] **Step 4: Write the implementation**

Create `tools/images/card.mjs`:

```js
/*
 * What a social card says. Pure: no fonts, no rendering, no filesystem.
 *
 * Every design decision lives here so it can be tested without satori, and so
 * that bumping TEMPLATE_VERSION invalidates every cached card at once.
 */

export const TEMPLATE_VERSION = 1;

/* Copied verbatim from the light theme in assets/css/main.css. A card is the
   site's face on someone else's page; it must not drift from the site. */
export const PALETTE = {
  paper: "#faf7f2",
  ink: "#1e1a16",
  ink2: "#574e45",
  ink3: "#857a6e",
  rule: "#ddd3c5",
  accent: "#9d5420",
  peat: "#2f2620",
};

const SECTION_EYEBROW = {
  whiskies: "Bottling",
  distilleries: "Distillery",
  regions: "Region",
  countries: "Country",
  glossary: "Glossary",
  guides: "Guide",
  about: "peaty.scot",
};

export function eyebrowFor(entry) {
  if (entry.kind === "home") return "Whiskies of the World";
  if (entry.kind === "term") return "Flavour";
  if (entry.kind === "section" || entry.kind === "taxonomy") return "Index";
  return SECTION_EYEBROW[entry.section] ?? "peaty.scot";
}

export function factsFor(entry) {
  if (entry.kind !== "page") return [];
  const facts = [];
  switch (entry.section) {
    case "whiskies":
      if (entry.age) facts.push(`${entry.age} yr`);
      if (entry.abv) facts.push(`${entry.abv}%`);
      if (entry.category) facts.push(entry.category);
      break;
    case "distilleries":
      if (entry.region) facts.push(entry.region);
      if (entry.country) facts.push(entry.country);
      if (entry.founded) facts.push(`founded ${entry.founded}`);
      break;
    case "regions":
      if (entry.country) facts.push(entry.country);
      if (entry.count) facts.push(`${entry.count} distilleries`);
      break;
    case "countries":
      if (entry.spirit) facts.push(entry.spirit);
      break;
  }
  return facts;
}

export function titleSize(title) {
  if (title.length <= 24) return 76;
  if (title.length <= 40) return 64;
  return 56;
}

/* satori requires an explicit display:flex on any element with more than one
   child, and a `children` key on every element including leaves. */
const leaf = (style) => ({ type: "div", props: { style, children: "" } });
const text = (style, content) => ({ type: "div", props: { style, children: content } });

export function cardTree(entry) {
  const title = entry.title ?? "";
  const size = titleSize(title);
  const facts = factsFor(entry);
  const tags = entry.flavours ?? [];

  const body = [
    text(
      {
        fontFamily: "Source Serif 4",
        fontWeight: 700,
        fontSize: `${size}px`,
        lineHeight: 1.12,
        color: PALETTE.ink,
        maxHeight: `${Math.round(size * 1.12 * 3)}px`,
        overflow: "hidden",
      },
      title
    ),
  ];

  if (facts.length) {
    body.push(text({ marginTop: "24px", fontSize: "28px", color: PALETTE.ink2 }, facts.join(" · ")));
  }

  body.push(leaf({ marginTop: "28px", width: "220px", height: "3px", backgroundColor: PALETTE.accent }));

  if (tags.length) {
    body.push(text({ marginTop: "24px", fontSize: "24px", color: PALETTE.ink3 }, tags.join(" · ")));
  }

  return {
    type: "div",
    props: {
      style: {
        width: "1200px",
        height: "630px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        backgroundColor: PALETTE.paper,
        padding: "48px",
        fontFamily: "Source Sans 3",
      },
      children: [
        {
          type: "div",
          props: {
            style: { display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" },
            children: [
              {
                type: "div",
                props: {
                  style: { display: "flex", alignItems: "center" },
                  children: [
                    leaf({ width: "18px", height: "18px", borderRadius: "9px", backgroundColor: PALETTE.accent, marginRight: "12px" }),
                    text({ fontSize: "26px", fontWeight: 600, color: PALETTE.ink }, "peaty.scot"),
                  ],
                },
              },
              text(
                { fontSize: "20px", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: PALETTE.ink3 },
                eyebrowFor(entry)
              ),
            ],
          },
        },
        {
          type: "div",
          props: { style: { display: "flex", flexDirection: "column" }, children: body },
        },
      ],
    },
  };
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `npm test`
Expected: PASS — 7 tests.

- [ ] **Step 6: Commit**

```bash
git add package.json tools/images/card.mjs tools/images/card.test.mjs
git commit -m "Add social card design module"
```

---

### Task 2: Renderer

Turns a card tree into PNG bytes. Owns fonts, satori and resvg — nothing else in the codebase touches those.

**Files:**
- Create: `tools/images/render.mjs`
- Create: `tools/images/render.test.mjs`
- Modify: `package.json` (devDependencies)

**Interfaces:**
- Consumes: `cardTree(entry)` from `tools/images/card.mjs`.
- Produces: `renderCard(entry) -> Promise<Buffer>` (PNG bytes, exactly 1200×630) and `fontFingerprint() -> Promise<string>` (hex sha256 over all font files, for the Task 4 cache key).

- [ ] **Step 1: Install the dependencies**

```bash
npm install --save-dev satori@^0.33.4 @resvg/resvg-js@^2.6.2 \
  @fontsource/source-serif-4@^5.3.0 @fontsource/source-sans-3@^5.3.0
```

Satori accepts `ttf`, `otf` and `woff` — **not** `woff2`. Fontsource ships both; use the `.woff` files.

- [ ] **Step 2: Verify the font files are where the code expects**

```bash
ls node_modules/@fontsource/source-serif-4/files/source-serif-4-latin-700-normal.woff \
   node_modules/@fontsource/source-sans-3/files/source-sans-3-latin-400-normal.woff \
   node_modules/@fontsource/source-sans-3/files/source-sans-3-latin-600-normal.woff
```

Expected: all three listed. If a filename differs, correct the constants in Step 4 rather than guessing.

- [ ] **Step 3: Write the failing tests**

Create `tools/images/render.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderCard, fontFingerprint } from "./render.mjs";

const entry = {
  url: "/whiskies/ardbeg-10-year-old/", card: "/og/whiskies/ardbeg-10-year-old.png",
  kind: "page", section: "whiskies", title: "Ardbeg 10 Year Old",
  abv: 46, age: 10, category: "Single Malt Scotch Whisky", founded: 0,
  spirit: "", count: 0, region: "Islay", country: "Scotland",
  flavours: ["Peat smoke", "Iodine"],
};

const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

/* PNG IHDR: 8-byte signature, 4-byte length, 4-byte "IHDR", then width and
   height as big-endian uint32 at offsets 16 and 20. */
const dimensions = (png) => ({ width: png.readUInt32BE(16), height: png.readUInt32BE(20) });

test("renders a PNG at exactly 1200x630", async () => {
  const png = await renderCard(entry);
  assert.ok(png.subarray(0, 8).equals(PNG_MAGIC), "not a PNG");
  assert.deepEqual(dimensions(png), { width: 1200, height: 630 });
});

test("rendering is deterministic, so the cache can trust its key", async () => {
  const [a, b] = [await renderCard(entry), await renderCard(entry)];
  assert.ok(a.equals(b), "same input produced different bytes");
});

test("different content produces different pixels", async () => {
  const other = await renderCard({ ...entry, title: "Lagavulin 16 Year Old" });
  const base = await renderCard(entry);
  assert.ok(!base.equals(other), "different titles produced identical cards");
});

test("a very long title still renders at the right size", async () => {
  const png = await renderCard({
    ...entry,
    title: "An Extraordinarily Long Bottling Name That Runs Well Past Three Lines Of Display Type",
  });
  assert.deepEqual(dimensions(png), { width: 1200, height: 630 });
});

test("every page kind renders", async () => {
  for (const kind of ["home", "page", "section", "taxonomy", "term"]) {
    const png = await renderCard({ ...entry, kind });
    assert.deepEqual(dimensions(png), { width: 1200, height: 630 }, `kind ${kind} failed`);
  }
});

test("fontFingerprint is a stable hex digest", async () => {
  const fp = await fontFingerprint();
  assert.match(fp, /^[0-9a-f]{64}$/);
  assert.equal(fp, await fontFingerprint());
});
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `npm test`
Expected: FAIL — `Cannot find module './render.mjs'`

- [ ] **Step 5: Write the implementation**

Create `tools/images/render.mjs`:

```js
/*
 * Card tree -> PNG bytes. The only module that knows about fonts, satori or
 * resvg.
 *
 * Font paths are resolved relative to this file rather than through
 * require.resolve, because fontsource's exports map is not guaranteed to
 * expose individual files and a private repo always installs at the root.
 */
import satori from "satori";
import { Resvg } from "@resvg/resvg-js";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { cardTree } from "./card.mjs";

const FONT_DIR = new URL("../../node_modules/@fontsource/", import.meta.url);

const FONT_FILES = [
  { name: "Source Serif 4", weight: 700, style: "normal", file: "source-serif-4/files/source-serif-4-latin-700-normal.woff" },
  { name: "Source Sans 3", weight: 400, style: "normal", file: "source-sans-3/files/source-sans-3-latin-400-normal.woff" },
  { name: "Source Sans 3", weight: 600, style: "normal", file: "source-sans-3/files/source-sans-3-latin-600-normal.woff" },
];

let fontsPromise;

function loadFonts() {
  fontsPromise ??= Promise.all(
    FONT_FILES.map(async ({ name, weight, style, file }) => ({
      name,
      weight,
      style,
      data: await readFile(fileURLToPath(new URL(file, FONT_DIR))),
    }))
  );
  return fontsPromise;
}

/* Part of the cache key: a font upgrade changes every card. */
export async function fontFingerprint() {
  const fonts = await loadFonts();
  const hash = createHash("sha256");
  for (const font of fonts) hash.update(font.data);
  return hash.digest("hex");
}

export async function renderCard(entry) {
  const fonts = await loadFonts();
  const svg = await satori(cardTree(entry), { width: 1200, height: 630, fonts });
  return new Resvg(svg, { fitTo: { mode: "width", value: 1200 } }).render().asPng();
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `npm test`
Expected: PASS — 13 tests total.

- [ ] **Step 7: Eyeball one card**

The tests prove it is a valid 1200×630 PNG. They cannot prove it looks right.

```bash
node -e "import('./tools/images/render.mjs').then(async m => { \
  const fs = await import('node:fs/promises'); \
  await fs.writeFile('/tmp/card.png', await m.renderCard({ \
    kind:'page', section:'whiskies', title:'Ardbeg 10 Year Old', abv:46, age:10, \
    category:'Single Malt Scotch Whisky', founded:0, spirit:'', count:0, \
    region:'Islay', country:'Scotland', flavours:['Peat smoke','Iodine'] })); \
  console.log('wrote /tmp/card.png'); })"
```

Open it. Confirm: wordmark and eyebrow on one row at the top, title large and legible at thumbnail size, fact line and flavour tags below an accent rule, warm paper ground. Adjust `card.mjs` if it does not read well — this is the one step where taste beats assertions.

- [ ] **Step 8: Commit**

```bash
git add package.json package-lock.json tools/images/render.mjs tools/images/render.test.mjs
git commit -m "Render social cards to PNG with satori and resvg"
```

---

### Task 3: Hugo card-URL partial and manifest

The single definition of where a card lives. `head.html` (Task 5) and the manifest both call the same partial, so the URL cannot drift between them.

**Files:**
- Create: `layouts/partials/og-image.html`
- Create: `layouts/home.ogmanifest.json`
- Modify: `hugo.toml` (add `outputFormats.ogmanifest`, extend `outputs.home`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `public/og-manifest.json` — a JSON array of manifest entries in the shape Task 1 defined. Also `partial "og-image.html" $page` returning a root-relative card path such as `/og/whiskies/ardbeg-10-year-old.png`.

- [ ] **Step 1: Write the card-URL partial**

Create `layouts/partials/og-image.html`. The `{{-` / `-}}` trimming on every line matters — a stray newline ends up inside a `content` attribute.

```
{{- /* The one definition of a card's URL. head.html and the manifest both
       call this, so the path cannot drift between the tag and the file. */ -}}
{{- $slug := strings.TrimSuffix "/" (strings.TrimPrefix "/" .RelPermalink) -}}
{{- if eq $slug "" -}}/og/home.png{{- else -}}/og/{{ $slug }}.png{{- end -}}
```

Mapping this produces:

| RelPermalink | Card |
|---|---|
| `/` | `/og/home.png` |
| `/whiskies/` | `/og/whiskies.png` |
| `/whiskies/ardbeg-10-year-old/` | `/og/whiskies/ardbeg-10-year-old.png` |
| `/flavours/peat-smoke/` | `/og/flavours/peat-smoke.png` |
| `/explore/` | `/og/explore.png` |

A file `og/whiskies.png` and a directory `og/whiskies/` coexist without collision.

- [ ] **Step 2: Register the output format**

In `hugo.toml`, add above `[outputs]`:

```toml
[outputFormats]
  [outputFormats.ogmanifest]
    mediaType = "application/json"
    baseName = "og-manifest"
    isPlainText = true
    notAlternative = true
```

and change `[outputs]` to:

```toml
[outputs]
  home = ["html", "rss", "sitemap", "json", "ogmanifest"]
```

- [ ] **Step 3: Write the manifest template**

Create `layouts/home.ogmanifest.json`. `site.Pages` yields exactly the canonical set — home, regular pages, sections, the taxonomy and its terms — and excludes paginated URLs and `404.html`, which is precisely the set that needs cards.

```
{{- $items := slice -}}
{{- range site.Pages -}}
  {{- $page := . -}}
  {{- $region := "" -}}
  {{- with $page.Params.region -}}
    {{- with site.GetPage (printf "/regions/%s" .) -}}{{- $region = .Title -}}{{- end -}}
  {{- end -}}
  {{- $country := "" -}}
  {{- with $page.Params.country -}}
    {{- with site.GetPage (printf "/countries/%s" .) -}}{{- $country = .Title -}}{{- end -}}
  {{- end -}}
  {{- $flavours := slice -}}
  {{- range $page.Params.flavours -}}
    {{- with site.GetPage (printf "/flavours/%s" .) -}}{{- $flavours = $flavours | append .Title -}}{{- end -}}
  {{- end -}}
  {{- $items = $items | append (dict
      "url"      $page.RelPermalink
      "card"     (partial "og-image.html" $page)
      "kind"     $page.Kind
      "section"  $page.Section
      "title"    (cond (eq $page.Kind "home") "Whiskies of the World" $page.Title)
      "abv"      ($page.Params.abv | default 0)
      "age"      ($page.Params.age_statement | default 0)
      "category" ($page.Params.category | default "")
      "founded"  ($page.Params.founded | default 0)
      "spirit"   ($page.Params.spirit_name | default "")
      "count"    ($page.Params.distilleries_count_approx | default 0)
      "region"   $region
      "country"  $country
      "flavours" $flavours
    ) -}}
{{- end -}}
{{- $items | jsonify -}}
```

References are resolved to titles here, not in Node: Hugo owns the content model, Node owns pixels. A reference that does not resolve yields `""` rather than a broken card — the same discipline as `partials/href.html`.

- [ ] **Step 4: Build and verify the manifest**

```bash
npm run build && node -e "
const m = require('./public/og-manifest.json');
console.log('entries:', m.length);
console.log('kinds:', [...new Set(m.map(e => e.kind))].sort().join(', '));
console.log(JSON.stringify(m.find(e => e.url === '/whiskies/ardbeg-10-year-old/'), null, 2));
console.log('home card:', m.find(e => e.kind === 'home').card);
console.log('section card:', m.find(e => e.url === '/whiskies/').card);
"
```

Expected: `entries: 38`; kinds `home, page, section, taxonomy, term`; the Ardbeg entry carrying `"card": "/og/whiskies/ardbeg-10-year-old.png"`, `"region": "Islay"`, `"country": "Scotland"` and a non-empty `flavours` array; home card `/og/home.png`; section card `/og/whiskies.png`.

If `entries` is not 38, the count has legitimately changed with content — confirm it matches `site.Pages` rather than assuming a bug.

- [ ] **Step 5: Commit**

```bash
git add hugo.toml layouts/partials/og-image.html layouts/home.ogmanifest.json
git commit -m "Emit an OG card manifest from Hugo"
```

---

### Task 4: Cache and the card CLI

**Files:**
- Create: `tools/images/cache.mjs`
- Create: `tools/images/cache.test.mjs`
- Create: `tools/images/cards.mjs`
- Modify: `package.json` (`images:cards` script, `build` script)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `renderCard(entry)` and `fontFingerprint()` from `render.mjs`; `TEMPLATE_VERSION` from `card.mjs`; `public/og-manifest.json` from Task 3.
- Produces: `cacheKey(entry, fontprint) -> string` (64-char hex); `readCache(key) -> Promise<Buffer|null>`; `writeCache(key, buffer) -> Promise<void>`; and the CLI `node tools/images/cards.mjs`, which writes every card under `public/og/`.

- [ ] **Step 1: Ignore the cache directory**

Add to `.gitignore`, after `resources/_gen/`:

```
.cache/
```

- [ ] **Step 2: Write the failing cache tests**

Create `tools/images/cache.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { cacheKey } from "./cache.mjs";

const entry = { url: "/a/", card: "/og/a.png", kind: "page", section: "whiskies", title: "A", abv: 46, age: 10, category: "x", founded: 0, spirit: "", count: 0, region: "Islay", country: "Scotland", flavours: ["Peat smoke"] };
const fp = "a".repeat(64);

test("same entry and fingerprint give the same key", () => {
  assert.equal(cacheKey(entry, fp), cacheKey(entry, fp));
  assert.match(cacheKey(entry, fp), /^[0-9a-f]{64}$/);
});

test("key order in the entry does not change the key", () => {
  const reordered = Object.fromEntries(Object.entries(entry).reverse());
  assert.equal(cacheKey(entry, fp), cacheKey(reordered, fp));
});

test("any content change changes the key", () => {
  assert.notEqual(cacheKey(entry, fp), cacheKey({ ...entry, title: "B" }, fp));
  assert.notEqual(cacheKey(entry, fp), cacheKey({ ...entry, abv: 40 }, fp));
  assert.notEqual(cacheKey(entry, fp), cacheKey({ ...entry, flavours: ["Sherry"] }, fp));
});

test("a font change changes the key", () => {
  assert.notEqual(cacheKey(entry, fp), cacheKey(entry, "b".repeat(64)));
});
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `npm test`
Expected: FAIL — `Cannot find module './cache.mjs'`

- [ ] **Step 4: Write the cache module**

Create `tools/images/cache.mjs`:

```js
/*
 * Content-hash cache for rendered cards.
 *
 * The key covers the template version, the fonts and every field the card
 * draws from, so a design change invalidates everything and an unchanged page
 * never re-renders.
 */
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { TEMPLATE_VERSION } from "./card.mjs";

const CACHE_DIR = join(process.cwd(), ".cache", "og");

/* JSON.stringify is key-order dependent; the manifest's order is stable today
   but the cache must not silently miss if the template reorders a dict. */
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${stable(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function cacheKey(entry, fontprint) {
  return createHash("sha256")
    .update(stable({ v: TEMPLATE_VERSION, f: fontprint, e: entry }))
    .digest("hex");
}

export async function readCache(key) {
  try {
    return await readFile(join(CACHE_DIR, `${key}.png`));
  } catch (err) {
    if (err.code === "ENOENT") return null;
    throw err;
  }
}

export async function writeCache(key, buffer) {
  await mkdir(CACHE_DIR, { recursive: true });
  await writeFile(join(CACHE_DIR, `${key}.png`), buffer);
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `npm test`
Expected: PASS — 17 tests total.

- [ ] **Step 6: Write the CLI**

Create `tools/images/cards.mjs`:

```js
#!/usr/bin/env node
/*
 * Renders one social card per manifest entry into public/og/.
 *
 * Runs after Hugo, so the cards land in the finished build and linkcheck can
 * resolve them. Never touches the network.
 */
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { renderCard, fontFingerprint } from "./render.mjs";
import { cacheKey, readCache, writeCache } from "./cache.mjs";

const ROOT = process.cwd();
const PUBLIC = join(ROOT, "public");
const MANIFEST = join(PUBLIC, "og-manifest.json");

if (!existsSync(MANIFEST)) {
  console.error("public/og-manifest.json does not exist — run the Hugo build first.");
  process.exit(1);
}

const entries = JSON.parse(await readFile(MANIFEST, "utf8"));

/* A generator that generates nothing is broken, not finished. */
if (!Array.isArray(entries) || entries.length === 0) {
  console.error("the OG manifest is empty — the template is broken, not the site");
  process.exit(1);
}

const fontprint = await fontFingerprint();
let rendered = 0;
let cached = 0;

for (const entry of entries) {
  if (!entry.card || !entry.card.startsWith("/og/")) {
    console.error(`  BAD  ${entry.url} has card path ${JSON.stringify(entry.card)}`);
    process.exit(1);
  }

  const key = cacheKey(entry, fontprint);
  let png = await readCache(key);
  if (png) {
    cached++;
  } else {
    png = await renderCard(entry);
    await writeCache(key, png);
    rendered++;
  }

  const out = join(PUBLIC, entry.card.replace(/^\//, ""));
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, png);
}

console.log(`\n${entries.length} cards · ${rendered} rendered · ${cached} from cache`);
```

- [ ] **Step 7: Wire it into the build**

In `package.json`, add the script and extend `build`:

```json
"images:cards": "node tools/images/cards.mjs",
"build": "npm run validate && hugo --minify --destination public && npm run images:cards",
```

Order matters: Hugo writes the manifest, then the cards land in the finished `public/`.

- [ ] **Step 8: Verify end to end**

```bash
rm -rf .cache public && npm run build
ls public/og public/og/whiskies
file public/og/home.png public/og/whiskies/ardbeg-10-year-old.png
npm run build
```

Expected: the first build reports `38 cards · 38 rendered · 0 from cache`; `file` reports `PNG image data, 1200 x 630` for both; the second build reports `38 cards · 0 rendered · 38 from cache`.

- [ ] **Step 9: Commit**

```bash
git add .gitignore package.json tools/images/cache.mjs tools/images/cache.test.mjs tools/images/cards.mjs
git commit -m "Generate social cards into the build, hash-cached"
```

---

### Task 5: Meta tags

**Files:**
- Modify: `layouts/partials/head.html:11` (the `twitter:card` line)

**Interfaces:**
- Consumes: `partial "og-image.html" .` from Task 3.
- Produces: an absolute `og:image` on every page except `404.html`.

- [ ] **Step 1: Replace the twitter:card line**

In `layouts/partials/head.html`, replace this single line:

```
<meta name="twitter:card" content="summary">
```

with:

```
{{ if ne .Kind "404" }}
<meta property="og:image" content="{{ partial "og-image.html" . | absURL }}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{{ if .IsHome }}{{ .Site.Title }} — Whiskies of the World{{ else }}{{ .Title }} · {{ .Site.Title }}{{ end }}">
<meta name="twitter:card" content="summary_large_image">
{{ else }}
<meta name="twitter:card" content="summary">
{{ end }}
```

The 404 page has no card: its `RelPermalink` is `/404.html`, not a directory, so the slug rule would produce a nonsense path. It is also never deliberately shared.

- [ ] **Step 2: Build and verify the tags**

```bash
npm run build
grep -o 'og:image[^>]*' public/whiskies/ardbeg-10-year-old/index.html
grep -o 'twitter:card[^>]*' public/whiskies/ardbeg-10-year-old/index.html
grep -c 'og:image' public/404.html
grep -o 'og:image content=[^ >]*' public/index.html public/whiskies/index.html
```

Expected: the Ardbeg page carries `og:image content=https://peaty.scot/og/whiskies/ardbeg-10-year-old.png` plus width, height and alt; `twitter:card content=summary_large_image`; `404.html` reports `0`; home reports `/og/home.png` and the section `/og/whiskies.png`.

- [ ] **Step 3: Confirm the referenced files exist**

```bash
node -e "
const {readFileSync,existsSync}=require('node:fs');
const html=readFileSync('public/whiskies/ardbeg-10-year-old/index.html','utf8');
const m=html.match(/og:image content=([^ >]+)/);
const p='public'+new URL(m[1]).pathname;
console.log(p, existsSync(p) ? 'EXISTS' : 'MISSING');
"
```

Expected: `public/og/whiskies/ardbeg-10-year-old.png EXISTS`

- [ ] **Step 4: Commit**

```bash
git add layouts/partials/head.html
git commit -m "Point og:image at the generated card"
```

---

### Task 6: Invariant 7, and documentation

The tag and the file are produced by two different tools. Nothing yet proves they agree — this is the guard that does, and it is the only thing standing between a template typo and an `og:image` pointing at nothing.

**Files:**
- Modify: `tools/linkcheck/index.mjs`
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the built `public/` from Tasks 3–5.
- Produces: a non-zero exit from `npm run linkcheck` when any page lacks a resolving `og:image`.

- [ ] **Step 1: Add the og:image check to linkcheck**

In `tools/linkcheck/index.mjs`, add after the `ATTR` constant:

```js
/* Invariant 7: every page carries exactly one absolute og:image resolving to a
   real file. The tag comes from Hugo and the file from tools/images — nothing
   else proves the two agree. */
const META = /<meta\s+([^>]*?)\/?>/gi;
const ATTR_PAIR = /([a-zA-Z:_-]+)=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g;

function ogImages(html) {
  const found = [];
  for (const tag of html.matchAll(META)) {
    const attrs = {};
    for (const a of tag[1].matchAll(ATTR_PAIR)) {
      attrs[a[1].toLowerCase()] = a[2] ?? a[3] ?? a[4] ?? "";
    }
    if (attrs.property === "og:image") found.push(attrs.content ?? "");
  }
  return found;
}
```

Then declare the counters beside `const broken = []`:

```js
const ogProblems = [];
let ogChecked = 0;
```

Inside the `for (const file of htmlFiles)` loop, after the `ATTR` loop, add:

```js
  /* 404 is never deliberately shared and has no card. */
  if (src !== "404.html") {
    const images = ogImages(html);
    ogChecked++;
    if (images.length !== 1) {
      ogProblems.push({ src, msg: `${images.length} og:image tags, expected exactly 1` });
    } else {
      const url = images[0];
      let path;
      try {
        path = new URL(url).pathname;
      } catch {
        ogProblems.push({ src, msg: `og:image is not absolute: ${url}` });
      }
      if (path && !resolves(path)) {
        ogProblems.push({ src, msg: `og:image does not resolve: ${url}` });
      }
    }
  }
```

Replace the reporting and exit block at the end of the file with:

```js
for (const b of broken) {
  console.error(`  BROKEN  ${b.url}\n          linked from /${b.src}`);
}
for (const o of ogProblems) {
  console.error(`  NO CARD /${o.src}\n          ${o.msg}`);
}

console.log(
  `\n${htmlFiles.length} pages · ${checked} internal references · ${broken.length} broken` +
  `\n${ogChecked} pages checked for og:image · ${ogProblems.length} without a valid card`
);

/* A checker that finds nothing to check is a broken checker, not a clean site. */
if (checked === 0) {
  console.error("no internal references found at all — the extractor is broken, not the site");
  process.exit(1);
}
if (ogChecked === 0) {
  console.error("no pages checked for og:image — the extractor is broken, not the site");
  process.exit(1);
}
process.exit(broken.length || ogProblems.length ? 1 : 0);
```

- [ ] **Step 2: Verify it passes on a good build**

```bash
npm run check
```

Expected: `50 pages checked for og:image · 0 without a valid card`, exit 0.

(50, not 38: the paginated `page/1/` duplicates carry their section's tag, which resolves to the same card. That is correct — they canonicalise to the section URL.)

- [ ] **Step 3: Verify it actually catches a missing card**

A guard nobody has seen fail is a guard nobody should trust.

```bash
mv public/og/whiskies/ardbeg-10-year-old.png /tmp/ && npm run linkcheck; echo "exit: $?"
mv /tmp/ardbeg-10-year-old.png public/og/whiskies/
```

Expected: `NO CARD /whiskies/ardbeg-10-year-old/index.html` with `og:image does not resolve`, and `exit: 1`.

- [ ] **Step 4: Verify it catches a missing tag**

```bash
sed -i 's|<meta property=og:image [^>]*>||' public/index.html && npm run linkcheck; echo "exit: $?"
npm run build
```

Expected: `NO CARD /index.html` with `0 og:image tags, expected exactly 1`, and `exit: 1`. The rebuild restores it.

- [ ] **Step 5: Document the invariant**

In `CLAUDE.md`, add to the **Invariants** list:

```markdown
7. **Every page has a social card.** `og:image` is absolute, unique, and resolves to
   a real file under `public/og/`. Enforced in `tools/linkcheck`. The tag comes from
   Hugo and the file from `tools/images` — this check is the only thing proving the
   two agree. `404.html` is the sole exemption.
```

Add to the **Commands** block:

```sh
npm test           # unit tests for the card generator (node --test)
npm run images:cards  # render social cards into public/og/ (run by build)
```

Add a subsection after **Two link systems, two guards**:

```markdown
## Card URLs have one definition

`layouts/partials/og-image.html` is the only place a card's URL is derived.
`head.html` and `layouts/home.ogmanifest.json` both call it, and the Node
generator never computes a path — it consumes `card` from the manifest. If you
need to change where cards live, change that partial and nothing else.

The generator runs *after* Hugo, writing into the finished `public/`. Bump
`TEMPLATE_VERSION` in `tools/images/card.mjs` whenever the card design changes,
or the cache will happily serve the old design forever.
```

- [ ] **Step 6: Document the layout**

In `README.md`, add to the **Layout** block after the `tools/linkcheck/` line:

```
tools/images/    social card generation: design, rendering, cache
```

- [ ] **Step 7: Final verification**

```bash
rm -rf .cache public && npm test && npm run check
```

Expected: all tests pass; `38 cards · 38 rendered · 0 from cache`; `0 broken`; `50 pages checked for og:image · 0 without a valid card`; exit 0.

- [ ] **Step 8: Commit**

```bash
git add tools/linkcheck/index.mjs CLAUDE.md README.md
git commit -m "Require a resolving og:image on every page"
```

---

## Done when

- `npm run check` passes from a clean tree with no `.cache/` and no `public/`.
- Every one of the 38 canonical pages has a distinct card under `public/og/`.
- Removing any card, or any `og:image` tag, fails the build — demonstrated, not assumed.
- A repeat build renders zero cards.
- Sharing `https://peaty.scot/whiskies/ardbeg-10-year-old/` previews as a full-bleed card. Verify after deploy with a live debugger; `summary_large_image` cannot be checked offline.

## Deferred to phases 2 and 3

Page-bundle migration, `npm run images:fetch`, the licence allowlist and `image:` schema, `sharp` and the `.jpg` card variant, the hero and thumbnail partials, and `/about/image-credits/`. None of the above should appear in this phase.
