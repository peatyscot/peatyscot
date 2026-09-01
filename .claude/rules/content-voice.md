---
paths:
  - "content/**"
---

# Content voice

**Experimental.** This voice is being trialled on the `voice-documentary` branch. It is a
uniform register for every editorial page on the site. If it does not survive the trial,
this file goes and the prose reverts.

## The register

Write as a veteran natural-history broadcaster narrates a landscape film: unhurried,
present-tense, quietly astonished by an ordinary process observed closely enough.

Whisky-making is treated as a natural phenomenon rather than an industrial one. A bog is a
place that has been accumulating for eight thousand years. A still is a habitat with its
own conditions. A phenolic compound is an organism that must survive fermentation,
distillation and sixteen years in oak to reach the glass — and most of them do not.

Never name the broadcaster, and never write pastiche. No catchphrases, no borrowed
sign-offs, no "Sir". The register is reproduced through technique alone; anything that
reads as impersonation of a specific person has failed.

## The devices

**Place the reader before explaining anything.** Open on a location, a moment, or a
condition — not on a definition.

> Here, on two miles of the south coast of Islay, sit two distilleries.

**Present tense for process**, including processes that are centuries old, wherever they
are still happening.

**Hold the reveal.** Describe what a thing does, then name it.

> A device sits between the still and the condenser, turning the heaviest vapours back for
> a second passage through the copper. It is called a purifier.

**`And so…` as the hinge** between a cause and its consequence. Used once per page at
most; twice is a tic.

**The long sentence answered by a very short one.** Accumulate, then stop.

> The compounds bind to the wet grain, survive the mash, survive fermentation, survive the
> still, and survive sixteen years in oak. Peat cannot be added later.

**Understatement carries the feeling.** Never announce the emotion — let the short sentence
do it. `The whisky pays for it.` Not `tragically, the whisky suffers.`

**Scale and deep time**, wherever the facts genuinely supply them: a bog older than
farming, a cask losing spirit every year for sixteen years, a method abandoned everywhere
else on earth.

**`you` is permitted for the reader as observer** — what they can see, what the label will
not tell them. Never for the reader as taster.

## Hard limits

These are not stylistic preferences. Each one exists because this register's stock moves
collide with a rule the site is built on.

1. **The wonder points at process, place, time and chemistry — never at the act of
   tasting.** `And then, on the tongue, something extraordinary` is a personal tasting note
   in costume, and the site does not publish those. Marvel at what the compound survived to
   get there; go quiet at the moment of drinking.

2. **No first person, ever — and `we` least of all.** `We` invites the reader into a shared
   tasting that never happened. There is no narrator on this site, only a narration.

3. **Atmosphere never fills a gap in sourcing.** Where the facts run out, the voice stops.
   A cadence that wants one more clause does not get to invent it.

4. **Numbers, dates and disclosure states are never dramatised or softened.** `55 ppm` is
   `55 ppm`. `undisclosed` is `undisclosed` — never "a silence the distillery keeps", which
   turns a recorded non-answer into an insinuation. Where sources disagree, the
   disagreement is still stated plainly.

5. **The tasting-note disclaimer stays plain prose** and keeps the phrase
   `not a personal tasting note` verbatim. It is an honesty statement, not narration.
   Do not restyle it. The validator greps for it.

6. **Never let cadence displace a fact.** If a sentence reads better without the ppm figure,
   the figure stays and the sentence changes.

## Where the voice does not apply

- **Front-matter `description`.** It is the search-result snippet. Plain, informative,
  50–200 characters.
- **The Nose / Palate / Finish bullets.** These are the aggregated data itself, clipped and
  factual. The narration goes in the prose around them.
- **Source titles** and any quoted regulatory text.
- **Everything under `content/about/`, plus `content/explore.md`.** Legal, safety and
  interface text — privacy, terms, affiliate disclosure, responsible drinking, methodology,
  the filter page.
  Precision is the entire job on those pages, and a methodology page that promises plain
  sourcing should be written plainly. This matches `UTILITY_SECTIONS` in
  `tools/validate/index.mjs`.
- **Headings** stay short and scannable. The voice may touch them; it may not make them
  hard to skim.

## Worked examples

**Explanatory prose** — `content/whiskies/ardbeg-10-year-old.md`:

> *Before:* Chill filtration removes fatty acids and esters that cause a whisky to go
> cloudy when cold or diluted. It is cosmetic, and it also removes compounds that carry
> texture and aroma.

> *After:* Here, as the temperature falls, something begins to happen in the bottle. The
> fatty acids and esters — the very compounds that carry texture and aroma — gather, and
> the spirit clouds. And so they are taken out before they ever reach the glass. It is a
> decision made entirely for appearance. The whisky pays for it.

**The collision to avoid** — same register, aimed at the wrong target:

> *Wrong:* And then, at last, it reaches the tongue, and the smoke arrives — extraordinary,
> unmistakable, quite unlike anything else on earth.

> *Right:* The smoke that arrives in the glass set out from a kiln floor a decade ago. Most
> of it did not survive the journey.

The first invents an experience. The second marvels at a documented process, and states a
fact about phenol loss.

## Before committing

- Read it aloud. If a sentence has no beat, it is not in the voice yet.
- Search the diff for `we `, `I `, `on the tongue`, `on the palate`, `in the mouth`.
- Confirm every number, date and `undisclosed` survived the rewrite intact.
- `npm run check` still passes.
