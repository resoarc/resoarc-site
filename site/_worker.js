// Cloudflare Pages Functions advanced mode: /api/scorecard only.
// Public, read-only upstream with fixed URL; no user-supplied targets or credentials.
const SCORECARD_URL = "https://api.securityscorecards.dev/projects/github.com/resoarc/resoarc-site";
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/scorecard") {
      return env.ASSETS.fetch(request);
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
