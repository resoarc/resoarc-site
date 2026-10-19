/** ResoArc Pages Worker: static assets plus historical OpenSSF Scorecard snapshot.
 * Primary source publication is Codeberg, independent of the old hosting provider.
 * A past Scorecard result must not be presented as a current Codeberg score.
 */
const HISTORICAL_SCORECARD = Object.freeze({
  score: 5.9,
  date: "2026-10-16T19:51:20Z",
  repository: "historical-source",
  source: "Past OpenSSF Scorecard measurement, not current Codeberg",
  cached: true,
  historical: true,
});

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/scorecard") return env.ASSETS.fetch(request);
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response(null, { status: 405, headers: { Allow: "GET, HEAD" } });
    }
    return new Response(request.method === "HEAD" ? null : JSON.stringify(HISTORICAL_SCORECARD), {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, max-age=86400",
        "X-Content-Type-Options": "nosniff",
      },
    });
  },
};
