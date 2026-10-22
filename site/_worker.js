/** ResoArc Pages Worker.
 * Static files are served unchanged. Public SWWW API is read-only and sourced
 * exclusively from an approved, sanitized, versioned daily catalog.
 * No network connections to the internal ResoArc database are exposed.
 */
const HISTORICAL_SCORECARD = Object.freeze({
  score: 5.9,
  date: "2026-10-16T19:51:20Z",
  repository: "historical-source",
  source: "Past OpenSSF Scorecard measurement, not current Codeberg",
  cached: true,
  historical: true,
});
const API_PREFIX = "/api/v1/swww/";
const API_ROUTES = new Set([
  "/api/v1/swww/advisories",
  "/api/v1/swww/summary",
  "/api/v1/swww/technologies",
]);
const API_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "public, max-age=300, stale-while-revalidate=60",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Allow-Headers": "Accept, Content-Type",
  "X-Content-Type-Options": "nosniff",
  "Content-Security-Policy": "default-src 'none'",
};
function jsonResponse(body, status, method) {
  return new Response(method === "HEAD" ? null : JSON.stringify(body), {
    status, headers: API_HEADERS,
  });
}
function validatedInteger(raw, fallback, min, max) {
  if (raw === null) return fallback;
  if (!/^[1-9]\d{0,3}$/.test(raw)) return null;
  const value = Number(raw);
  return value >= min && value <= max ? value : null;
}
function allowedDate(value) {
  return !value || /^\d{4}-\d{2}-\d{2}$/.test(value);
}
function normalize(text) {
  return String(text ?? "").toLocaleLowerCase("en-US");
}
async function securityWeatherRequest(request, env, url) {
  const method = request.method;
  if (method === "OPTIONS") return new Response(null, { status: 204, headers: API_HEADERS });
  if (method !== "GET" && method !== "HEAD") {
    return jsonResponse({ error: "method_not_allowed" }, 405, method);
  }
  try {
    const catalogURL = new URL("/api/v1/swww/catalog.json", url);
    const source = await env.ASSETS.fetch(new Request(catalogURL.toString(), { method: "GET" }));
    if (!source.ok) throw new Error("catalog_unavailable");
    const catalog = await source.json();
    if (catalog.schema_version !== "1.0" || !Array.isArray(catalog.advisories)) {
      throw new Error("catalog_incompatible");
    }
    if (url.pathname === "/api/v1/swww/summary") {
      const { advisories, ...meta } = catalog;
      return jsonResponse({
        ...meta,
        available_technologies: [...new Set(advisories.flatMap(r =>
          (r.technologies || []).map(t => t.id)))].sort(),
        note: "Advisory technology labels do not establish ResoArc system exposure.",
      }, 200, method);
    }
    if (url.pathname === "/api/v1/swww/technologies") {
      const tags = new Map();
      for (const row of catalog.advisories) {
        for (const t of row.technologies || []) {
          if (!tags.has(t.id)) tags.set(t.id, { id:t.id, label:t.label, group:t.group, count:0 });
          tags.get(t.id).count += 1;
        }
      }
      return jsonResponse({
        report_date: catalog.report_date,
        generated_at: catalog.generated_at,
        technologies: [...tags.values()].sort((a,b) => b.count - a.count || a.id.localeCompare(b.id)),
        semantics: "Tags indicate explicit references in public advisories; they do not confirm ResoArc exposure.",
      }, 200, method);
    }
    const p = url.searchParams;
    if ([...p.keys()].some(k => !["q","technology","severity","source","date","exploited","page","limit"].includes(k))) {
      return jsonResponse({ error:"invalid_parameter" }, 400, method);
    }
    const page = validatedInteger(p.get("page"), 1, 1, 100);
    const limit = validatedInteger(p.get("limit"), 20, 1, 100);
    const q = (p.get("q") || "").trim();
    const technology = normalize((p.get("technology") || "").trim());
    const severity = (p.get("severity") || "").trim().toUpperCase();
    const sourceName = normalize((p.get("source") || "").trim());
    const date = (p.get("date") || "").trim();
    const exploited = p.get("exploited");
    if (page === null || limit === null || q.length > 120 || technology.length > 48 ||
        sourceName.length > 80 || !allowedDate(date) ||
        (severity && !["CRITICAL","HIGH","MEDIUM","LOW","UNKNOWN"].includes(severity)) ||
        (exploited !== null && !["true","false"].includes(exploited))) {
      return jsonResponse({ error: "invalid_parameter_value" }, 400, method);
    }
    const qlow = normalize(q);
    const matches = catalog.advisories.filter(row => {
      if (severity && row.severity !== severity) return false;
      if (technology && !(row.technologies || []).some(t => t.id === technology)) return false;
      if (sourceName && ![row.source,...(row.sources || [])].some(x => normalize(x).includes(sourceName))) return false;
      if (date && row.published_date !== date) return false;
      if (exploited !== null && Boolean(row.known_exploited) !== (exploited === "true")) return false;
      if (qlow && ![row.id,row.title,row.summary,...(row.technologies || []).map(t => t.label)]
        .some(x => normalize(x).includes(qlow))) return false;
      return true;
    });
    const start = (page - 1) * limit;
    return jsonResponse({
      schema_version: "1.0",
      report_date: catalog.report_date,
      generated_at: catalog.generated_at,
      quality: catalog.quality,
      source_count: catalog.source_count,
      observed_total: catalog.observed_total,
      catalog_total: catalog.available_records,
      filtered_total: matches.length,
      page, limit,
      has_next: start + limit < matches.length,
      items: matches.slice(start, start + limit),
      caution: catalog.collection_limit_notice,
    }, 200, method);
  } catch {
    return jsonResponse({ error: "daily_public_feed_unavailable",
      message: "The published daily snapshot cannot be read; try again later." }, 503, method);
  }
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (API_ROUTES.has(url.pathname)) {
      return securityWeatherRequest(request, env, url);
    }
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