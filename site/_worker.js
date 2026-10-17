/**
 * ResoArc Cloudflare Pages Worker.
 * Keep all static pages/assets delegated to Cloudflare Pages ASSETS.
 * Restore the publicly visible Scorecard JSON endpoint across direct uploads.
 */
const SCORECARD_URL = "https://api.scorecard.dev/projects/github.com/resoarc/resoarc-site";
const REPO = "github.com/resoarc/resoarc-site";
const LAST_VERIFIED = Object.freeze({
  score: 5.9,
  date: "2026-10-16T19:51:20Z",
  repository: REPO,
  source: "Last verified OpenSSF Scorecard API result",
  cached: true,
});

function isValidScorecard(data) {
  const score = Number(data?.score);
  const date = Date.parse(data?.date || "");
  return (
    Number.isFinite(score) && score >= 0 && score <= 10 &&
    Number.isFinite(date) && data?.repo?.name === REPO
  );
}

export default {
  async fetch(request, env, context) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/scorecard") {
      return env.ASSETS.fetch(request);
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response(null, { status: 405, headers: { Allow: "GET, HEAD" } });
    }

    let result = LAST_VERIFIED;
    try {
      const upstream = await fetch(SCORECARD_URL, {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(7000),
        cf: { cacheEverything: true, cacheTtl: 3600 },
      });
      if (upstream.ok) {
        const data = await upstream.json();
        if (isValidScorecard(data)) {
          result = {
            score: Number(data.score),
            date: data.date,
            repository: REPO,
            source: "OpenSSF Scorecard official API",
            cached: false,
          };
        }
      }
    } catch (_) {
      // A verified, clearly labelled previous score is preferable to an invented value.
    }

    return new Response(request.method === "HEAD" ? null : JSON.stringify(result), {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, max-age=3600",
        "X-Content-Type-Options": "nosniff",
      },
    });
  },
};
