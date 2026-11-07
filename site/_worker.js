// Cloudflare Pages Functions advanced mode: /api/scorecard only.
// Public, read-only upstream with fixed URL; no user-supplied targets or credentials.
const SCORECARD_URL = "https://api.securityscorecards.dev/projects/github.com/resoarc/resoarc-site";
// Privacy-first aggregate events. The binding is optional and disabled unless
// RESOARC_ACTIVITY (Cloudflare Analytics Engine) is configured by the operator.
// No IP addresses, cookies, user agents, full referrers, query strings or IDs.
const ACTIVITY_DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
function referrerGroup(requestUrl, referrer) {
  if (!referrer) return "direct";
  try {
    const host = new URL(referrer).hostname.toLowerCase();
    if (host === new URL(requestUrl).hostname.toLowerCase()) return "internal";
    if (host === "note.com" || host.endsWith(".note.com")) return "note.com";
    if (host === "github.com" || host.endsWith(".github.com")) return "github.com";
    if (/^(www\.)?google\.[a-z.]+$/.test(host)) return "google";
    if (host === "bing.com" || host === "www.bing.com") return "bing";
    if (host === "search.yahoo.co.jp") return "yahoo";
    if (host === "duckduckgo.com") return "duckduckgo";
    return "other";
  } catch {
    return "unknown";
  }
}
function recordPrivacySafeActivity(request, response, env, ctx) {
  if (request.method !== "GET" || !response || response.status >= 400) return;
  if (!env.RESOARC_ACTIVITY || typeof env.RESOARC_ACTIVITY.writeDataPoint !== "function") return;
  if (!ctx || typeof ctx.waitUntil !== "function") return;
  const url = new URL(request.url);
  const isDownload = /^\/downloads\/[a-z0-9._-]+\.zip$/i.test(url.pathname);
  const contentType = response.headers.get("Content-Type") || "";
  const isPage = /text\/html/i.test(contentType) && (url.pathname === "/" || /^\/[a-z0-9/_-]*\/?$/i.test(url.pathname));
  if (!isDownload && !isPage) return;
  // Each row counts a request, not a unique visitor or a proven ZIP transfer.
  // Requests returning redirects may be counted as download attempts.
  const path = isDownload ? url.pathname : url.pathname.replace(/\/index\.html$/, "/");
  const kind = isDownload ? "download_request" : "page_request";
  const day = new Date().toISOString().slice(0, 10);
  if (!ACTIVITY_DAY_PATTERN.test(day)) return;
  const data = {
    indexes: [kind],
    blobs: [day, kind, path.slice(0, 160), referrerGroup(request.url, request.headers.get("Referer"))],
    doubles: [1],
  };
  try {
    ctx.waitUntil(Promise.resolve().then(() => env.RESOARC_ACTIVITY.writeDataPoint(data)).catch(() => {}));
  } catch {
    // Site delivery must not depend on analytics.
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/scorecard") {
      // Optional Analytics Engine binding; never block real user requests.
      const response = await env.ASSETS.fetch(request);
      recordPrivacySafeActivity(request, response, env, ctx);
      return response;
    }
    const headers = {
      "Content-Type": "application/json; charset=utf-8",
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "public, max-age=300, s-maxage=600",
    };
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response(JSON.stringify({error: "method_not_allowed"}), {
        status: 405,
        headers: {...headers, Allow: "GET, HEAD"},
      });
    }
    try {
      const upstream = await fetch(SCORECARD_URL, {
        headers: {"Accept": "application/json"},
        signal: AbortSignal.timeout(7000),
        cf: {cacheTtl: 600, cacheEverything: true},
      });
      if (!upstream.ok) throw new Error("scorecard_unavailable");
      const data = await upstream.json();
      const score = Number(data.score);
      if (!Number.isFinite(score) || score < 0 || score > 10) throw new Error("invalid_score");
      const date = data.date;
      if (typeof date !== "string" || !Number.isFinite(Date.parse(date))) throw new Error("invalid_date");
      const result = {
        score: Math.round(score * 10) / 10,
        date,
        repository: "github.com/resoarc/resoarc-site",
        source: "OpenSSF Scorecard official API",
      };
      return new Response(request.method === "HEAD" ? null : JSON.stringify(result), {
        status: 200,
        headers,
      });
    } catch {
      return new Response(request.method === "HEAD" ? null : JSON.stringify({error: "scorecard_temporarily_unavailable"}), {
        status: 502,
        headers: {...headers, "Cache-Control": "no-store"},
      });
    }
  },
};
