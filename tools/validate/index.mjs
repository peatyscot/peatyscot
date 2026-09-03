#!/usr/bin/env node
/*
 * Content validation for peaty.scot.
 *
 * Hugo will happily build `abv: fourty`, or a bottling naming a distillery that
 * does not exist. This is the guard rail: schema, referential integrity, link
 * density and orphan detection, all as hard failures.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import matter from "gray-matter";
import { schemas } from "./schema.mjs";

const ROOT = process.cwd();
const CONTENT = join(ROOT, "content");
const MIN_INTERNAL_LINKS = 5;

/* Pages that are navigational rather than editorial: they list their children,
   so a link-density floor and an inbound-link requirement do not apply. */
const INDEX_FILE = /(^|\/)_index\.md$/;

/* A leaf bundle: content/whiskies/<slug>/index.md, carrying photo.* beside it.
   It is an ordinary content page — unlike _index.md it is not a listing, so the
   link-density and orphan rules still apply. Only its URL is derived
   differently, from the directory rather than the filename. */
const BUNDLE_FILE = /(^|\/)index\.md$/;
const PHOTO_FILE = /^photo\.(jpe?g|png|webp)$/i;

/* Utility and legal pages are not part of the wiki graph. Forcing five
   cross-links into a privacy policy would produce padding, not navigation. */
const UTILITY_SECTIONS = new Set(["about"]);
const UTILITY_PATHS = new Set(["/explore"]);

/* Reachable from the site chrome on every page, so never truly orphaned. */
const NAV_PATHS = new Set([
  "/explore", "/whiskies", "/distilleries", "/regions", "/flavours", "/guides",
]);

const errors = [];
const warnings = [];
const fail = (file, msg) => errors.push({ file, msg });
const warn = (file, msg) => warnings.push({ file, msg });

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (entry.endsWith(".md")) out.push(p);
  }
  return out;
}

const files = walk(CONTENT);
const pages = [];

for (const abs of files) {
  const rel = relative(ROOT, abs).split(sep).join("/");
  let fm, body;
  try {
    const parsed = matter(readFileSync(abs, "utf8"));
    fm = parsed.data;
    body = parsed.content;
  } catch (e) {
    fail(rel, `front matter will not parse: ${e.message}`);
    continue;
  }

  const parts = relative(CONTENT, abs).split(sep);
  const section = parts.length > 1 ? parts[0] : "_root";
  const isIndex = INDEX_FILE.test(rel);
  const isBundle = BUNDLE_FILE.test(rel);

  // Logical URL path, matching Hugo's own. Both _index.md and a bundle's
  // index.md take their URL from the containing directory.
  let urlPath;
  if (isIndex || isBundle) {
    urlPath = "/" + parts.slice(0, -1).join("/");
  } else {
    urlPath = "/" + parts.join("/").replace(/\.md$/, "");
  }
  if (urlPath === "/") urlPath = "/";

  pages.push({ rel, section, isIndex, isBundle, urlPath, fm, body });
}

const byPath = new Map(pages.map((p) => [p.urlPath, p]));

/* ---------- 1. schema ---------- */
for (const p of pages) {
  // Section _index pages are listings; validate them against the loose base.
  const schema = p.isIndex ? schemas.about : (schemas[p.section] ?? schemas._root);
  const res = schema.safeParse(p.fm);
  if (!res.success) {
    for (const issue of res.error.issues) {
      const at = issue.path.length ? issue.path.join(".") : "(root)";
      fail(p.rel, `${at}: ${issue.message}`);
    }
  }
}

/* ---------- 2. duplicate URLs ---------- */
const seen = new Map();
for (const p of pages) {
  if (seen.has(p.urlPath)) fail(p.rel, `duplicate URL ${p.urlPath}, also from ${seen.get(p.urlPath)}`);
  else seen.set(p.urlPath, p.rel);
}

/* ---------- 3. referential integrity of front-matter refs ---------- */
const refFields = [
  ["distillery", "/distilleries/"],
  ["region", "/regions/"],
  ["country", "/countries/"],
];
for (const p of pages) {
  for (const [field, prefix] of refFields) {
    const v = p.fm[field];
    if (!v) continue;
    if (!byPath.has(prefix + v)) {
      fail(p.rel, `${field}: "${v}" has no page at ${prefix}${v}`);
    }
  }
  for (const f of p.fm.flavours ?? []) {
    if (!byPath.has("/flavours/" + f)) {
      fail(p.rel, `flavours: "${f}" has no page at /flavours/${f}`);
    }
  }
}

/* ---------- 4. link graph: density and orphans ---------- */
const REF = /\{\{<\s*relref\s+"([^"]+)"\s*>\}\}/g;
const inbound = new Map(pages.map((p) => [p.urlPath, 0]));

for (const p of pages) {
  const targets = new Set();
  for (const m of p.body.matchAll(REF)) {
    const t = m[1].replace(/\/$/, "");
    targets.add(t);
    if (!byPath.has(t)) {
      // Hugo also catches this, but failing here gives a better message sooner.
      fail(p.rel, `relref to "${t}" which does not exist`);
    }
  }
  p.outbound = targets;
  for (const t of targets) {
    if (t !== p.urlPath && inbound.has(t)) inbound.set(t, inbound.get(t) + 1);
  }
}

for (const p of pages) {
  if (p.isIndex) continue;
  const utility = UTILITY_SECTIONS.has(p.section) || UTILITY_PATHS.has(p.urlPath);
  if (!utility && p.outbound.size < MIN_INTERNAL_LINKS) {
    fail(p.rel, `only ${p.outbound.size} outbound internal links, needs ${MIN_INTERNAL_LINKS} — the site is a wiki, pages must connect`);
  }
  if (inbound.get(p.urlPath) === 0 && !NAV_PATHS.has(p.urlPath) && !utility) {
    warn(p.rel, `orphan: nothing links to ${p.urlPath}`);
  }
}

/* ---------- 5. aggregated tasting notes must be labelled ---------- */
for (const p of pages) {
  if (p.section !== "whiskies" || p.isIndex) continue;
  if (/##\s*Aggregated flavour profile/i.test(p.body) &&
      !/not a personal tasting note/i.test(p.body)) {
    fail(p.rel, "has a flavour profile but no line disclaiming it as a personal tasting note");
  }
}

/* ---------- 6. photographs and their provenance travel together ---------- */
/* A photo.* with no image: block is a file nobody can attribute; an image:
   block with no photo.* is provenance for something that is not there. Either
   alone is an error, so the licence cannot drift away from the bytes. */
for (const p of pages) {
  const photos = p.isBundle
    ? readdirSync(dirname(join(ROOT, p.rel))).filter((f) => PHOTO_FILE.test(f))
    : [];

  if (photos.length && !p.fm.image) {
    fail(p.rel, `bundle contains ${photos[0]} but no image: block — a photograph with no recorded licence is one nobody can review`);
  }
  if (p.fm.image && !photos.length) {
    fail(p.rel, "has an image: block but no photo.* beside it");
  }
  if (photos.length > 1) {
    fail(p.rel, `bundle contains ${photos.length} photo files (${photos.join(", ")}); exactly one is expected`);
  }
}

/* ---------- report ---------- */
const pad = (s) => s.padEnd(52);
for (const w of warnings) console.warn(`  warn  ${pad(w.file)} ${w.msg}`);
for (const e of errors) console.error(`  FAIL  ${pad(e.file)} ${e.msg}`);

console.log(
  `\n${pages.length} pages checked · ${errors.length} error(s) · ${warnings.length} warning(s)`
);
process.exit(errors.length ? 1 : 0);
