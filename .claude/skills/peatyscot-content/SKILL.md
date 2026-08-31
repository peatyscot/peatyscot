---
name: peatyscot-content
description: Use when adding or editing any whisky content on peaty.scot — a distillery, bottling/SKU, region, country, flavour or glossary term. Covers sourcing from Wikidata, required front matter, citation format, the interlinking floor, and the validation loop.
---

# Adding content to peaty.scot

Follow this in order. Do not skip the research step and write from memory — whisky facts
are widely misreported and the site's whole proposition is that its facts are traceable.

## 1. Research before writing

Get structured facts from **Wikidata** first. It is CC0, so it can be used directly.

```sh
# Find the entity
curl -sS -G "https://www.wikidata.org/w/api.php" \
  --data-urlencode "action=wbsearchentities" \
  --data-urlencode "search=<name> distillery" \
  --data-urlencode "language=en" --data-urlencode "format=json"

# Pull its claims: P571 inception, P127 owner, P17 country,
# P625 coordinates, P856 official site, P131 admin area
curl -sS "https://www.wikidata.org/w/api.php?action=wbgetentities&ids=<QID>&props=claims|labels&languages=en&format=json"
```

Owner and location come back as Q-IDs; resolve them with a second `wbgetentities` call.

Then verify every URL you intend to cite actually resolves:

```sh
curl -sS -o /dev/null -L -m 20 -w '%{http_code}  %{url_effective}\n' "<url>"
```

`403` normally means bot-blocking, so the page is real — keep the citation. `404` or `500`
means the path is wrong; find the right one or drop it.

## 2. Write the page

Copy the shape of an existing page in the same section rather than inventing one.

Required front matter by section is defined in `tools/validate/schema.mjs` — read it, it
is the contract. Points that are easy to get wrong:

- `region`, `country`, `distillery` and every entry in `flavours` are **references**. The
  target page must already exist or validation fails. Add the referenced page first.
- `chill_filtered` / `colouring_added` are `true`, `false`, or `"undisclosed"`. If the
  producer does not state it, the value is `"undisclosed"`. Do not infer.
- `age_statement` is `null` for a no-age-statement bottling, not `0` and not omitted.
- `description` is the meta description: 50–200 characters, written for a search result.
- `sources` needs at least one entry with `title`, `url` and `accessed`.

## 3. Tasting notes

Only ever aggregated, and always labelled. Use the established form:

```markdown
## Aggregated flavour profile

Synthesized from published producer notes and widely reported descriptions. This is a
consensus summary, not a personal tasting note.

- **Nose** — …
- **Palate** — …
- **Finish** — …
```

The validator fails a whisky page that has a flavour profile without that disclaimer.
Never write a first-person tasting experience.

## 4. Interlink it

Every non-utility page needs **at least 5 outbound internal links**, written as
`{{< relref "/section/slug" >}}`. This is a hard failure, not a warning.

Make the links earn their place. A link should be where a reader would actually want to
follow the thought — a distillery mentioning its region, a bottling explaining a term.
Padding a page with a "Related" dump to clear the threshold defeats the point.

Also check the new page has something linking **to** it. The validator warns on orphans;
a page nothing links to will not be found.

## 5. Validate, build, check

```sh
npm run validate    # fix every error before continuing
npm run check       # build + offline link check
```

If validation fails, fix the content. Never relax a rule in `tools/validate/` to get
green — the rules encode the site's editorial standard.

## Adding a whole new region or country

A new `region` or `country` value needs its page to exist before any distillery can
reference it. The Yoichi page originally referenced `region: hokkaido` with no such page —
Hugo built it happily and the facts table linked to a 404, because template-built hrefs
bypass `relref`. Create the parent page first.
