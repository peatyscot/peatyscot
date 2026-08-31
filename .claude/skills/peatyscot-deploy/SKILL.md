---
name: peatyscot-deploy
description: Use when building, previewing, or deploying peaty.scot to Cloudflare Workers — including the first-time custom domain setup for peaty.scot, verification steps, and post-deploy checks.
---

# Deploying peaty.scot

## Preflight — not optional

```sh
npm run check
```

This runs validation, the Hugo build, and the offline link check. All three must pass.
A failing check means broken links or invalid content ship to a live, indexed site.

Then serve it through the real Worker, not just `hugo server` — the Worker adds the
www→apex redirect and the cache and security headers, and `hugo server` exercises none
of that:

```sh
npx wrangler dev --port 8788 --local
```

Verify against the running server:

```sh
curl -sS -D- -o /dev/null http://127.0.0.1:8788/                      # 200, security headers
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8788/no-such/   # 404
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  -H "Host: www.peaty.scot" http://127.0.0.1:8788/                    # 301 -> apex
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8788/index.json  # 200
```

Fingerprinted CSS/JS must return `Cache-Control: public, max-age=31536000, immutable`;
HTML must return `max-age=0, must-revalidate`.

**The www redirect cannot be tested locally once `routes` are configured.** `wrangler dev`
rewrites `request.url` to the first route's hostname regardless of the `Host` header or
`--resolve`, so the Worker always sees `peaty.scot` and never redirects. A 200 there is a
dev artifact, not a regression — verify the redirect against production after deploying.

To stop the dev server, **do not** run `pkill -f "wrangler dev"` — the pattern matches the
killing shell's own command line and kills it. Match on the port or use the job's PID.

## Deploy

```sh
npx wrangler deploy --dry-run   # confirm bindings and asset count
npx wrangler deploy
```

The account is `domains@reinholdings.com` (`68b57dcfe19244896b019119a5291e1e`), already
authenticated via OAuth. The `peaty.scot` zone (`8adeaa78cb7ee656e175f9528f647dfa`) is
active in that account.

## First-time custom domain

`wrangler.jsonc` deliberately ships with `routes` commented out, because uncommenting
them **creates DNS records on the live zone** on the next deploy. Confirm with the site
owner before enabling:

```jsonc
"routes": [
  { "pattern": "peaty.scot", "custom_domain": true },
  { "pattern": "www.peaty.scot", "custom_domain": true }
]
```

Both are needed: `www` must resolve for the Worker's redirect to be reachable at all.

## After deploy

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://peaty.scot/
curl -sS -o /dev/null -w '%{http_code} -> %{redirect_url}\n' https://www.peaty.scot/
curl -sS https://peaty.scot/sitemap.xml | grep -c '<loc>'
curl -sS -I https://peaty.scot/robots.txt | head -1
```

Then submit the sitemap in Google Search Console. Indexing is the point of the
URL-permanence rule in `CLAUDE.md`: once these URLs are crawled, changing them costs
rankings.

## Rollback

```sh
npx wrangler deployments list
npx wrangler rollback [deployment-id]
```
