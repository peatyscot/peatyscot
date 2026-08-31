# Google AdSense — setup procedure and record

Operating document for monetising peaty.scot with Google AdSense. It is both the
instructions for switching ads on and the permanent record of what was done, so
**update the ledgers in this file in the same commit as the change they describe.**

Read `CLAUDE.md` § Ads first — it holds the hard rule this document implements:
enabling ads needs a publisher ID, a privacy-policy update, and a certified consent
CMP. All three, or none.

---

## Status

| | |
|---|---|
| **Current state** | **Publisher ID issued.** An AdSense account exists and `ca-pub-9724395993136863` has been recorded. Review status not yet confirmed in this record — see the open question below. |
| Code path | Built and inert. `params.ads.enabled = false` in `hugo.toml`. Publisher ID is set, which on its own renders nothing: both `head.html` and `ad-slot.html` gate on `enabled`. |
| Ads served | None, in any region. |
| Blocking before serving | Ad unit slot IDs (gap 1), contact route (gap 2), certified CMP (Phase 3), privacy rewrite (gap 4). |
| Last reviewed | 2026-08-31 |

**Open question, to be answered in this record:** the publisher ID alone does not say
whether the site has been *submitted* for review or *approved* — AdSense issues the ID at
signup, before either. Fill in the submission and approval dates in the changelog when
known; do not infer approval from the ID existing.

The site makes a written promise in `content/about/privacy.md` that this page will be
updated *before* ads run, not afterwards. That constrains the order of operations in
Phase 4 and is not negotiable.

---

## Record: Google-supplied data

Everything in the first table is public by construction — it ships in the HTML of every
page, or in a file Google requires be world-readable at the site root. Recording it here
is safe and is the point of this document. Fill each row in as it arrives; leave it
blank rather than guessing.

### Non-sensitive — record here

| Field | Format / example | Value | Where it is consumed |
|---|---|---|---|
| Publisher ID | `ca-pub-` + 16 digits | **`ca-pub-9724395993136863`** *(recorded 2026-08-31)* | `hugo.toml` → `params.ads.publisherId`; emitted in `head.html` and `ad-slot.html` |
| ads.txt seller line | `google.com, pub-<16 digits>, DIRECT, f08c47fec0942fa0` | **`google.com, pub-9724395993136863, DIRECT, f08c47fec0942fa0`** *(recorded 2026-08-31)* | `static/ads.txt` |
| TAG certification authority ID | `f08c47fec0942fa0` | `f08c47fec0942fa0` | ads.txt. This is Google's own ID and is **identical for every publisher** — it is not a secret and not per-account. |
| Ad unit name — in-article | free text, chosen by us | *(not yet created)* | AdSense UI only |
| Ad unit slot ID — in-article | 10 digits | *(not yet issued)* | `data-ad-slot` in `ad-slot.html` |
| Ad unit name — sidebar | free text, chosen by us | *(not yet created)* | AdSense UI only |
| Ad unit slot ID — sidebar | 10 digits | *(not yet issued)* | `data-ad-slot` in `ad-slot.html` |
| AdSense site name | hostname as registered | *(not yet added)* | AdSense UI only |
| Search Console verification token | `meta name="google-site-verification"` | *(not yet issued)* | `head.html`, if Search Console is linked |
| CMP vendor | name of chosen certified CMP | *(not yet chosen)* | — |
| IAB TCF CMP ID | integer, assigned by IAB | *(not yet known)* | Recorded here only; the CMP emits it itself |
| Privacy & messaging message ID | AdSense UI identifier | *(not yet created)* | Recorded here only |

**The `ca-` prefix is not decorative.** The same account number appears in two forms and
they are not interchangeable: `ca-pub-9724395993136863` in `hugo.toml` and in the
`data-ad-client` attribute, but bare `pub-9724395993136863` in `ads.txt`. Writing
`ca-pub-` into ads.txt makes the record invalid and Google will report the site as having
no authorised seller.

### Sensitive — never record here, never commit

These arrive through the same signup flow and must stay out of the repository, out of
this file, and out of commit messages. None of them is needed to make ads work.

- The Google account email and password used to sign in to AdSense.
- Payments profile: payee legal name, postal address, phone number.
- Bank account, IBAN/SWIFT, or any payment instrument detail.
- Tax identity forms (W-8BEN, W-9) and any tax ID.
- The address-verification PIN Google posts on paper once earnings pass the threshold.
- Any AdSense Management API OAuth client secret or refresh token.

If a value would let someone take money out of the account or impersonate the account
holder, it is sensitive. If it is already visible in the page source of the live site,
it is not.

---

## Record: what has been done

| Date | Change | Commit |
|---|---|---|
| 2026-08-31 | Ad slot partial, page-level script tag, CSS reservation, and `params.ads` switch built in the inert state. No Google account, no publisher ID, nothing served. | `16b97b0` |
| 2026-08-31 | This document written. Audit of the existing wiring found the gaps in the next section. | *(this commit)* |
| 2026-08-31 | Publisher ID `ca-pub-9724395993136863` recorded in `hugo.toml`. `static/ads.txt` created with the seller line. `enabled` left `false` — nothing is served. Closes gap 3. | *(this commit)* |
| | AdSense review submitted | *(date to be recorded)* |
| | AdSense approval / policy status | *(date to be recorded)* |

Concretely, what exists today:

- `layouts/partials/ad-slot.html` — renders an `<aside class="ad-slot">` on every page
  type. The Google markup inside it is gated on `Site.Params.ads.enabled`, so today the
  element is empty.
- `layouts/partials/head.html:22-24` — the page-level `adsbygoogle.js` tag, same gate.
- `assets/css/main.css:158-163` — `.ad-slot:empty { display: none }` collapses the
  container while inert; the non-empty rule reserves `min-height: 280px` so that
  switching ads on causes no layout shift.
- Call sites: `home.html`, `page.html`, `section.html`, `explore.html`, `term.html`,
  and the four entity layouts (`whiskies`, `distilleries`, `regions`, `countries`).
- `content/about/privacy.md` and `content/about/affiliate-disclosure.md` — the policy
  is on record ahead of the money, which is the right way round.

---

## Gaps that must close before ads can serve

Found by auditing the above against Google's current documentation. Numbers 1–4 are
blocking; 5 and 6 are traps for later.

**1. The ad markup has no `data-ad-slot`.** `ad-slot.html:11-15` emits `data-ad-client`
but no slot ID. Google's documented unit code carries both — the slot ID is what binds a
placement to an ad unit, and therefore to reporting. Without it the placement cannot be
reported on and will not reliably fill.

Two ways out, and the choice matters:

- **Named ad units (recommended).** Create one ad unit per slot in AdSense, record the
  slot IDs in the ledger above, and thread them through the partial.
- **Auto ads.** Delete the `<ins>` entirely and let the page-level script inject
  placements. Rejected: `content/about/affiliate-disclosure.md` commits in writing to ads
  that are "limited in number, never placed above the main content of a page, and never
  in interstitial or full-screen formats". Auto ads decide placement and density
  themselves and will not honour that. Choosing Auto ads means either breaking a
  published promise or rewriting it.

**2. There is no contact route.** `content/about/terms.md:43` sends readers to `/about`
for contact; `content/about/_index.md` gives no address. That is a circular dead end.
AdSense review looks for a way to reach the publisher, and a reader who spots an error
currently has none either. Add a real address to `/about`.

**3. ~~There is no `ads.txt`.~~ Closed 2026-08-31.** `static/ads.txt` now carries the
seller line. Hugo copies `static/` to `public/` verbatim and the Worker serves it from the
`ASSETS` binding with no extra routing, so it needs no template or route. It is not yet
live — it reaches `https://peaty.scot/ads.txt` on the next deploy, and Google can only
see it once deployed.

**4. The privacy page is written in the future tense.** `content/about/privacy.md` says
"No advertising is currently served" and undertakes to update the page *before* ads run.
The rewrite must therefore land in the same commit that flips `enabled = true`, never in
a follow-up.

**5. CSP is a silent trap, but not one today.** `worker/index.ts:29` sets
`Content-Security-Policy: frame-ancestors 'none'` and nothing else. That governs who may
embed *this* page and does not restrict what the page may load, so it will not block
AdSense. The danger is additive: anyone who later adds `script-src` or `frame-src`
without allowing Google's ad origins breaks ad serving with no console error on the
Worker side and no build failure. The comment at `worker/index.ts:26-28` already flags
this — leave it there.

**6. `Permissions-Policy: interest-cohort=()` is inert.** `worker/index.ts:25` opts out
of FLoC, a proposal that was withdrawn. It neither helps nor harms. `browsing-topics` is
not set, so the Topics API is permitted by default, which is what ad serving wants.
Recorded here so nobody "tidies" it into a directive that does block ads.

**Not a gap:** `npm run linkcheck` ignores absolute URLs (`tools/linkcheck/index.mjs:58`
skips anything not starting with a single `/`), so the Google script and ad iframes do
not affect it. `npm run check` stays green with ads on.

---

## Procedure

### Phase 0 — before applying (no Google account needed)

Close gaps 2 and 3's repo-side work, and get the corpus to a defensible size.

1. Add a contact address to `content/about/_index.md` so `/about/terms/` resolves to
   something real.
2. Grow the corpus. Google publishes **no minimum page count and no minimum site age**;
   the widely repeated "15–25 posts of 800+ words" figure is community folklore, not
   policy. What Google does require is original high-quality content, ownership of the
   site, an operator aged 18+, HTTPS, and compliance with the AdSense Program Policies.
   The `README.md` roadmap already targets ~250 pages before applying — keep that. At 38
   source pages the site is thin for a reference work, and thin content is the most
   common rejection reason.
3. Confirm the alcohol angle. AdSense treats alcohol as restricted rather than
   prohibited: ads may be limited or non-personalised in some markets. The
   age-affirmation banner and `/about/responsible-drinking/` already argue the right
   case. Expect reduced fill, not rejection.
4. `npm run check` must pass.

### Phase 1 — create the account and apply

5. Sign up at `adsense.google.com` with the site's own Google account, not a personal
   one shared with unrelated services.
6. Add `peaty.scot` as a site. **Record the publisher ID** in the ledger — it is issued
   immediately, before approval, and everything else depends on it.
7. Create `static/ads.txt` with the single line from the ledger, then build and deploy.
   Verify it is live before submitting for review:

   ```sh
   npm run check && npx wrangler deploy
   curl -s https://peaty.scot/ads.txt
   ```

8. Submit for review. Review usually takes days but can take weeks. **Record the
   submission date.**

Do **not** set `enabled = true` yet. The verification snippet AdSense asks you to place
is the same `adsbygoogle.js` tag already in `head.html`; if review requires it before
approval, gate it separately rather than flipping the ads switch, so no `<ins>` slots go
live without a CMP behind them.

### Phase 2 — after approval, wire the units

9. **Record the approval date and policy status.**
10. Create the ad units in AdSense: one `in-article`, one `sidebar` if a sidebar
    placement is wanted. **Record each unit's name and slot ID.**
11. Thread the slot IDs through the partial. Add them to `hugo.toml`:

    ```toml
    [params.ads]
      enabled = false          # still false at this step
      publisherId = "ca-pub-XXXXXXXXXXXXXXXX"
      [params.ads.slots]
        in-article = "XXXXXXXXXX"
        sidebar    = "XXXXXXXXXX"
    ```

    and in `ad-slot.html`, look the slot ID up by the `slot` key the partial already
    receives, emitting `data-ad-slot`. Keep the existing `enabled` gate wrapping it.
    If a key is missing, render nothing — an `<ins>` with an empty slot ID is worse than
    no `<ins>`, because it fails silently.

### Phase 3 — consent, before any EEA/UK traffic sees an ad

Since **16 January 2024** Google has required a Google-certified CMP integrated with the
IAB TCF for ads served to the EEA and the UK (Switzerland from 31 July 2024). Without
one, those users get non-personalised or limited ads, or no ads at all. Given a `.scot`
domain, UK and EEA traffic is the core audience, not an edge case — this phase is the
whole game, not a formality.

12. Choose a certified CMP. Google's own **Privacy & messaging** (formerly Funding
    Choices), configured inside AdSense, is the least-effort option and is certified by
    definition. Third-party options include Usercentrics, Didomi, Sourcepoint and
    OneTrust. **Record the vendor, its IAB TCF CMP ID, and the message ID.**
13. Configure the consent message for the EEA and UK. Verify it actually appears from a
    UK IP before relying on it.
14. Check the CMP against the existing age-affirmation banner. Both are dismissible
    overlays; two stacked modals on first visit is a bad first impression, and the
    consent dialog must not be obscured by the age notice. The age choice is stored in
    `localStorage` and never leaves the device (`content/about/privacy.md`), so it is not
    itself a consent matter — but the interaction between the two is a UX decision that
    needs making deliberately.

### Phase 4 — go live

One commit, containing all of:

15. `hugo.toml` → `enabled = true`.
16. The rewritten Advertising section of `content/about/privacy.md`, in the present
    tense, naming Google as the ad provider, describing the cookies and identifiers used,
    naming the CMP and how to withdraw consent, and updating `lastmod` and the "Last
    updated" line in the body.
17. `content/about/affiliate-disclosure.md` — drop "currently carries no advertising".
18. This file — status table, ledgers, and changelog row.

```sh
npm run check          # must pass; do not deploy otherwise
npx wrangler dev       # confirm the real Worker headers locally first
npm run deploy
```

### Phase 5 — verify on the live site

```sh
curl -s https://peaty.scot/ads.txt
curl -s https://peaty.scot/ | grep -o 'ca-pub-[0-9]\{16\}' | head -1
curl -s https://peaty.scot/ | grep -o 'data-ad-slot=[^ ]*' | head
curl -sI https://peaty.scot/ | grep -i 'content-security-policy'
```

Then in a browser, on a real page rather than the home page:

- An ad renders, and the reserved 280px container is filled rather than blank.
- No layout shift on load — the whole point of the CSS reservation.
- The consent dialog appears from a UK IP, and refusing it still renders the page.
- AdSense reporting shows impressions against the named ad units within ~24h. Zero
  impressions with a filled page means the slot IDs are wrong.
- Ads never appear above the main content, and there are at most two per page — the
  commitments in `content/about/affiliate-disclosure.md`.

### Rollback

`enabled = false` in `hugo.toml`, then `npm run deploy`. Slots collapse via
`.ad-slot:empty` and the page-level script stops being emitted. This is a one-line,
one-deploy kill switch and it is the reason the gate exists — keep it that way, and do
not let ad markup leak outside the `enabled` check.

Reverting the privacy page after ads have run is a separate judgement: it should record
that ads *were* served during a stated period rather than silently reverting to "no
advertising is currently served".

---

## Rules that survive this document

- Never set `enabled = true` without a publisher ID, the privacy rewrite, and a certified
  CMP in place. All three in the same commit or earlier.
- Never commit anything from the sensitive list above.
- Never weaken a validator rule or the CSP to make ads render. Fix the ad code instead.
- Never let ad markup escape the `Site.Params.ads.enabled` gate — it is the kill switch.
- `npm run check` before every deploy, ads or not.

## Sources

Verified against Google's own documentation on 2026-08-31. Third-party "AdSense approval
checklist" articles were consulted and deliberately not relied on; where they assert
minimum word counts or post counts, that is folklore rather than published policy.

- ads.txt line format and root-directory hosting — <https://support.google.com/adsense/answer/12171612>
- Ad unit code and its `data-` attributes — <https://support.google.com/adsense/answer/9183363>
- Certified CMP requirement for the EEA and UK — <https://support.google.com/adsense/answer/13554116>
