# peaty.scot — working instructions

Static Hugo site on Cloudflare Workers. Read `README.md` first for the stack rationale;
this file is the operating manual.

## Commands

```sh
npm run validate    # schema + referential integrity + link graph over content/
npm run build       # validate, then hugo --minify into public/
npm run linkcheck   # offline link check over public/ (needs a build first)
npm run check       # build + linkcheck — run this before every deploy
npm run dev         # hugo server -D
npx wrangler dev    # serve public/ through the real Worker (headers, redirects)
```

`npm run check` must pass before any deploy. It is not advisory.

## Invariants

Enforced by tooling. Do not weaken any of these to make a build pass:

1. **A broken internal link fails the build.** `refLinksErrorLevel = "ERROR"` in
   `hugo.toml`. If a `relref` fails, add the missing page — never downgrade the setting.
2. **Every entity page cites at least one source.** Enforced in `tools/validate/schema.mjs`.
3. **Non-utility pages carry at least 5 outbound internal links.** This is what makes the
   site a wiki rather than a pile of pages. Utility and legal pages (`about/`, `/explore`)
   are exempt — see `UTILITY_SECTIONS` in `tools/validate/index.mjs`.
4. **Disclosure fields are tri-state.** `chill_filtered` and `colouring_added` are `true`,
   `false`, or `"undisclosed"`. Never infer a producer's silence into a boolean.
5. **Tasting notes are aggregated and labelled.** A whisky page with a flavour profile must
   carry the line disclaiming it as a personal tasting note. The validator checks for it.
6. **URLs are permanent.** `/whiskies/`, `/distilleries/`, `/regions/`, `/countries/`,
   `/flavours/`, `/glossary/`, `/guides/`. Changing a published URL needs a redirect.

## Two link systems, two guards

`relref` covers links written in prose and fails the Hugo build. Hrefs built in templates
(`printf "/regions/%s"`) bypass it entirely — that class of bug ships silently, so
`tools/linkcheck` resolves every href in the built HTML against real files.

When a template builds a link, route it through `partials/href.html`, which returns `""`
when the target does not exist.

Note that `linkcheck` must handle unquoted attributes: `hugo --minify` strips quotes, and
an extractor that only matches `href="..."` will report a clean site while checking
nothing. It fails loudly if it finds zero references.

## Performance trap

Do not compute backlinks by scanning every page from inside a page template. That is
O(n²) and exceeded 120s at 5,000 pages during the stack spike.
`partials/backlink-index.html` builds one inverted index behind `partialCached` — same
result, ~8s. Any future cross-page aggregate should follow that pattern.

## Content model

| Kind | Location | Layout |
|---|---|---|
| Bottling (SKU) | `content/whiskies/<slug>.md` | `layouts/whiskies/page.html` |
| Distillery | `content/distilleries/<slug>.md` | `layouts/distilleries/page.html` |
| Region | `content/regions/<slug>.md` | `layouts/regions/page.html` |
| Country | `content/countries/<slug>.md` | `layouts/countries/page.html` |
| Flavour (taxonomy) | `content/flavours/<slug>/_index.md` | `layouts/term.html` |
| Glossary, Guides | `content/<section>/<slug>.md` | `layouts/page.html` |

`region`, `country`, `distillery` and `flavours` front-matter values are references. The
validator fails if the referenced page does not exist.

## Sourcing rules

- **Wikidata is CC0** — import structured facts directly and record the `wikidata:` Q-ID.
- Producer sites and regulatory texts are authoritative for what they state plainly.
- Wikipedia and journalism are **research leads only**. Write the prose fresh.
- Verify a URL resolves before citing it. A 403 usually means bot-blocking rather than a
  dead link; a 404 means the path is wrong.
- Where sources disagree (Ardbeg's 1794 vs 1815 founding), state the disagreement rather
  than silently picking one.

## Ads

`params.ads` in `hugo.toml`, currently `enabled = false`. Slots render empty and collapse
via `.ad-slot:empty`. Enabling ads needs a publisher ID, a privacy-policy update, and a
certified consent CMP for EEA/UK traffic. Do not enable without all three.

## Never

- Never invent a tasting note, or present an aggregated note as personal experience.
- Never copy prose from another whisky site.
- Never weaken a validator rule to get a build green — fix the content instead.
- Never deploy without `npm run check` passing.
