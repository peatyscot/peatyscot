/**
 * peaty.scot — static site served from Workers Static Assets.
 *
 * The Worker runs ahead of the asset serving so it can normalise the host
 * (www -> apex, which matters for SEO because split hostnames split ranking
 * signals) and attach cache and security headers. Everything it serves comes
 * from the ASSETS binding; there is no dynamic content yet.
 */

interface Env {
  ASSETS: Fetcher;
}

const CANONICAL_HOST = "peaty.scot";

/* Hugo fingerprints CSS and JS filenames, so those are safe to cache forever.
   HTML must revalidate or content edits would not reach readers. */
const IMMUTABLE = /\.[0-9a-f]{16,}\.(css|js)$/;
const CACHEABLE_ASSET = /\.(css|js|svg|png|jpg|jpeg|webp|avif|woff2?|ico)$/;

function securityHeaders(headers: Headers): void {
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  headers.set("Permissions-Policy", "geolocation=(), microphone=(), camera=(), interest-cohort=()");
  /* Only frame-ancestors: a full CSP has to be worked out against whatever the
     ad provider actually loads, and a wrong one fails silently in the browser.
     Revisit when params.ads.enabled is turned on. */
  headers.set("Content-Security-Policy", "frame-ancestors 'none'");
}

function cacheHeaders(pathname: string, headers: Headers): void {
  if (IMMUTABLE.test(pathname)) {
    headers.set("Cache-Control", "public, max-age=31536000, immutable");
  } else if (CACHEABLE_ASSET.test(pathname)) {
    headers.set("Cache-Control", "public, max-age=86400");
  } else {
    headers.set("Cache-Control", "public, max-age=0, must-revalidate");
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Consolidate on the apex host. Skip for local dev and *.workers.dev previews.
    const host = url.hostname;
    if (host.startsWith("www.") && host.endsWith(CANONICAL_HOST)) {
      url.hostname = CANONICAL_HOST;
      return Response.redirect(url.toString(), 301);
    }

    const assetResponse = await env.ASSETS.fetch(request);

    const response = new Response(assetResponse.body, assetResponse);
    securityHeaders(response.headers);
    cacheHeaders(url.pathname, response.headers);
    return response;
  },
} satisfies ExportedHandler<Env>;
