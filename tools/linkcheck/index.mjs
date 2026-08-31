#!/usr/bin/env node
/*
 * Offline link check over the built site.
 *
 * relref covers links written in prose, but hrefs built in templates bypass it
 * entirely — that class of bug ships silently. This resolves every internal
 * href and asset reference against the actual build output.
 */
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, relative, sep } from "node:path";

const ROOT = process.cwd();
const PUBLIC = join(ROOT, "public");

if (!existsSync(PUBLIC)) {
  console.error("public/ does not exist — run the build first.");
  process.exit(1);
}

function walk(dir, ext) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) out.push(...walk(p, ext));
    else if (!ext || entry.endsWith(ext)) out.push(p);
  }
  return out;
}

const htmlFiles = walk(PUBLIC, ".html");
/* Minified output drops attribute quotes, so all three forms must be handled.
   An earlier version matched only the quoted form and cheerfully reported
   "0 broken" while checking nothing at all. */
const ATTR = /(?:href|src)=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g;

const broken = [];
let checked = 0;

function resolves(url) {
  const clean = url.split("#")[0].split("?")[0];
  if (clean === "" || clean === "/") return existsSync(join(PUBLIC, "index.html"));

  const rel = clean.replace(/^\//, "");
  const asFile = join(PUBLIC, rel);
  if (existsSync(asFile) && statSync(asFile).isFile()) return true;
  if (existsSync(join(PUBLIC, rel, "index.html"))) return true;
  if (existsSync(join(PUBLIC, rel.replace(/\/$/, "") + ".html"))) return true;
  return false;
}

for (const file of htmlFiles) {
  const src = relative(PUBLIC, file).split(sep).join("/");
  const html = readFileSync(file, "utf8");
  const seen = new Set();

  for (const m of html.matchAll(ATTR)) {
    const url = m[1] ?? m[2] ?? m[3] ?? "";
    if (!url.startsWith("/") || url.startsWith("//")) continue;
    if (seen.has(url)) continue;
    seen.add(url);
    checked++;
    if (!resolves(url)) broken.push({ src, url });
  }
}

for (const b of broken) {
  console.error(`  BROKEN  ${b.url}\n          linked from /${b.src}`);
}

console.log(
  `\n${htmlFiles.length} pages · ${checked} internal references · ${broken.length} broken`
);

/* A checker that finds nothing to check is a broken checker, not a clean site. */
if (checked === 0) {
  console.error("no internal references found at all — the extractor is broken, not the site");
  process.exit(1);
}
process.exit(broken.length ? 1 : 0);
