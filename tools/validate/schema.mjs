import { z } from "zod";

/* Tri-state disclosure: producers often decline to say. "undisclosed" is a
   first-class value — never inferred into a true/false. */
export const disclosure = z.union([z.boolean(), z.literal("undisclosed")]);

const source = z.object({
  title: z.string().min(3),
  url: z.string().url(),
  accessed: z.union([z.string(), z.date()]),
});

const slug = z.string().regex(/^[a-z0-9]+(-[a-z0-9]+)*$/, "must be a lowercase kebab-case slug");

/* Free licences only, and the jurisdiction ports Commons still carries
   ("CC BY-SA 2.0 de"). A licence outside this list is skipped, never guessed:
   the same rule as the tri-state disclosure fields, applied to provenance.
   Enforced here as well as at fetch time, so a hand-added photograph cannot
   smuggle in an unlicensed file. */
const LICENCE_ALLOWLIST =
  /^(CC0( 1\.0)?|Public domain|CC BY(-SA)? [1-4]\.0( [a-z]{2})?)$/i;

/* Provenance for a bundle's photo.* resource. The photograph itself is a page
   resource; this records only who took it and under what terms. Every field is
   required: a photograph whose licence is half-recorded is one nobody can
   review, which is the situation this exists to prevent. */
export const image = z.object({
  alt: z.string().min(15, "alt text must describe the photograph, not merely name it"),
  credit: z.string().min(2),
  source_url: z.string().url(),
  license: z.string().regex(
    LICENCE_ALLOWLIST,
    "licence is not on the free-licence allowlist — never guess one, and never infer it from silence"
  ),
  license_url: z.string().url(),
});

/* Every page needs a title and a description: the description is the meta
   description, and Google truncates around 160 characters. */
const base = z.object({
  title: z.string().min(2),
  description: z.string()
    .min(50, "meta description is too short to be useful in search results")
    .max(200, "meta description will be truncated in search results"),
  date: z.union([z.string(), z.date()]).optional(),
  lastmod: z.union([z.string(), z.date()]).optional(),
  flavours: z.array(slug).optional(),
  sources: z.array(source).optional(),
  image: image.optional(),
});

const peatLevel = z.enum(["unpeated", "light", "medium", "heavy"]);

export const schemas = {
  whiskies: base.extend({
    distillery: slug,
    region: slug,
    country: slug,
    category: z.string().min(3),
    age_statement: z.number().int().positive().nullable().optional(),
    abv: z.number().min(0).max(100),
    size_ml: z.number().int().positive().optional(),
    cask_types: z.array(z.string()).optional(),
    chill_filtered: disclosure.optional(),
    colouring_added: disclosure.optional(),
    peat_level: peatLevel.optional(),
    offers: z.array(z.object({
      retailer: z.string(),
      url: z.string().url(),
      price: z.number(),
      currency: z.string().length(3),
    })).optional(),
    sources: z.array(source).min(1, "a bottling page must cite at least one source"),
  }),

  distilleries: base.extend({
    country: slug,
    region: slug,
    founded: z.number().int().min(1400).max(2100),
    owner: z.string().min(2),
    status: z.enum(["operating", "mothballed", "closed", "demolished"]),
    latitude: z.number().min(-90).max(90).optional(),
    longitude: z.number().min(-180).max(180).optional(),
    wikidata: z.string().regex(/^Q\d+$/).optional(),
    website: z.string().url().optional(),
    peat_level: peatLevel.optional(),
    phenol_ppm_malt: z.number().positive().optional(),
    sources: z.array(source).min(1, "a distillery page must cite at least one source"),
  }),

  regions: base.extend({
    country: slug,
    region_type: z.string().min(3),
    distilleries_count_approx: z.number().int().positive().optional(),
    typical_peat_level: z.string().optional(),
    sources: z.array(source).min(1, "a region page must cite at least one source"),
  }),

  countries: base.extend({
    country_code: z.string().length(2),
    spirit_name: z.string().min(3),
    min_maturation_years: z.number().positive(),
    min_bottling_abv: z.number().min(0).max(100),
    colouring_permitted: disclosure.optional(),
    distilleries_count_approx: z.number().int().positive().optional(),
    sources: z.array(source).min(1, "a country page must cite at least one source"),
  }),

  glossary: base.extend({ term_type: z.string().optional() }),
  guides: base,
  flavours: base,
  about: base,
  _root: base,
};
