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
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/v1/outages") return outageRadarRequest(request, ctx);
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

/* Outage Radar: only provider-owned public status APIs. No arbitrary fetch URL or internal endpoint. */
const OUTAGE_PROVIDERS = Object.freeze([
  { id:"kintone", name:"kintone", host:"https://status.kintone.com", category:"業務SaaS", area:"日本" },
  { id:"cloudflare", name:"Cloudflare", host:"https://www.cloudflarestatus.com", category:"クラウド・基盤", area:"グローバル" },
  { id:"github", name:"GitHub", host:"https://www.githubstatus.com", category:"開発・クラウド", area:"グローバル" },
  { id:"openai", name:"OpenAI / ChatGPT API", host:"https://status.openai.com", category:"AI", area:"グローバル" },
  { id:"atlassian", name:"Atlassian", host:"https://status.atlassian.com", category:"業務SaaS", area:"グローバル" },
  { id:"vercel", name:"Vercel", host:"https://www.vercel-status.com", category:"開発・クラウド", area:"グローバル" },
  { id:"netlify", name:"Netlify", host:"https://www.netlifystatus.com", category:"開発・クラウド", area:"グローバル" },
  { id:"zoom", name:"Zoom", host:"https://status.zoom.us", category:"業務SaaS", area:"グローバル" },
  { id:"discord", name:"Discord", host:"https://www.discordstatus.com", category:"コミュニケーション", area:"グローバル" },
  { id:"twilio", name:"Twilio", host:"https://status.twilio.com", category:"コミュニケーション", area:"グローバル" },
  { id:"figma", name:"Figma", host:"https://status.figma.com", category:"業務SaaS", area:"グローバル" },
  { id:"shopify", name:"Shopify", host:"https://status.shopify.com", category:"EC・決済", area:"グローバル" },
]);
const OUTAGE_API_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "public, max-age=180",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "X-Content-Type-Options": "nosniff",
  "Content-Security-Policy": "default-src 'none'",
};
const outageText = (value, max = 250) => String(value == null ? "" : value).slice(0, max);
const outageDate = value => {
  const ms = Date.parse(value || "");
  return Number.isFinite(ms) ? new Date(ms).toISOString() : null;
};
async function outageFetchJSON(url) {
  const response = await fetch(url, {
    headers: {"Accept":"application/json", "User-Agent":"ResoArc-Outage-Radar/1.0 (+https://resoarc.com/status/)"},
    signal: AbortSignal.timeout(6500),
    cf: {cacheEverything:true, cacheTtl:180}
  });
  if (!response.ok) throw new Error("http_" + response.status);
  const data = await response.json();
  if (!data || typeof data !== "object") throw new Error("invalid_json");
  return data;
}
function outageIncident(provider, incident) {
  const state = outageText(incident.status || "unknown", 24).toLowerCase();
  const updatedAt = outageDate(incident.updated_at || incident.created_at);
  const startedAt = outageDate(incident.started_at || incident.created_at);
  const active = ["investigating","identified","monitoring"].includes(state);
  const impact = ["critical","major","minor"].includes(incident.impact) ? incident.impact : "unknown";
  const rawId = outageText(incident.id, 90);
  const sourceUrl = /^[a-zA-Z0-9]+$/.test(rawId) ? provider.host + "/incidents/" + rawId : provider.host;
  const updates = Array.isArray(incident.incident_updates) ? incident.incident_updates : [];
  const lastUpdate = updates[0] && updates[0].body ? outageText(updates[0].body, 600) : "";
  const components = Array.isArray(incident.components)
    ? incident.components.map(c => outageText(c.name, 70)).filter(Boolean).slice(0, 8) : [];
  return {
    id: provider.id + ":" + rawId,
    service_id:provider.id, service:provider.name, category:provider.category, area:provider.area,
    title:outageText(incident.name || "障害情報", 200), status:state, active,
    impact, started_at:startedAt, updated_at:updatedAt, detail:lastUpdate,
    components, source_url:sourceUrl, verified:"provider_api"
  };
}
async function outageCollect(provider, cutoffMs) {
  const [summaryResult, historyResult] = await Promise.allSettled([
    outageFetchJSON(provider.host + "/api/v2/summary.json"),
    outageFetchJSON(provider.host + "/api/v2/incidents.json")
  ]);
  if (summaryResult.status !== "fulfilled") {
    return {service:{id:provider.id, name:provider.name, category:provider.category, area:provider.area,
      source_url:provider.host, availability:"unknown", overall:"unknown", active_count:null,
      note:"公式APIを取得できませんでした"}, incidents:[], error:true};
  }
  const summary = summaryResult.value;
  const providerIncidents = historyResult.status === "fulfilled" &&
    Array.isArray(historyResult.value.incidents) ? historyResult.value.incidents : [];
  const summaryIncidents = Array.isArray(summary.incidents) ? summary.incidents : [];
  const byId = new Map();
  for (const raw of [...summaryIncidents, ...providerIncidents]) {
    if (raw && raw.id) byId.set(String(raw.id), raw);
  }
  const recent = [...byId.values()].map(row => outageIncident(provider,row))
    .filter(row => row.active || (row.updated_at && Date.parse(row.updated_at) >= cutoffMs));
  const active = recent.filter(row => row.active);
  const overall = outageText(summary.status && summary.status.indicator || "unknown",20);
  if (!active.length && ["minor","major","critical"].includes(overall)) {
    recent.unshift({
      id:provider.id+":summary", service_id:provider.id, service:provider.name,
      category:provider.category, area:provider.area, title:"公式ステータスでサービスの異常を公表",
      status:"identified", active:true, impact:overall,
      started_at:null, updated_at:outageDate(summary.page && summary.page.updated_at),
      detail:outageText(summary.status && summary.status.description, 400), components:[],
      source_url:provider.host, verified:"provider_status"
    });
  }
  const currentCount = recent.filter(row => row.active).length;
  return {service:{id:provider.id, name:provider.name, category:provider.category, area:provider.area,
    source_url:provider.host, availability:"reported", overall, active_count:currentCount,
    note:historyResult.status !== "fulfilled" ? "過去履歴の取得に失敗しました" : ""}, incidents:recent,
    error:false, history_error:historyResult.status !== "fulfilled"};
}
async function outageRadarRequest(request, ctx) {
  if (request.method === "OPTIONS") return new Response(null,{status:204,headers:OUTAGE_API_HEADERS});
  if (request.method !== "GET" && request.method !== "HEAD")
    return new Response(JSON.stringify({error:"method_not_allowed"}),{status:405,headers:OUTAGE_API_HEADERS});
  const url = new URL(request.url);
  if ([...url.searchParams.keys()].length)
    return new Response(JSON.stringify({error:"unsupported_query"}),{status:400,headers:OUTAGE_API_HEADERS});
  const cacheKey = new Request(url.origin + "/api/v1/outages", {method:"GET"});
  const cache = typeof caches !== "undefined" ? caches.default : null;
  if (cache) {
    try {
      const cached = await cache.match(cacheKey);
      if (cached) return request.method === "HEAD"
        ? new Response(null,{status:cached.status, headers:cached.headers}) : cached;
    } catch { /* fall through and refresh */ }
  }
  const checked = new Date().toISOString();
  const cutoff = Date.now() - 7 * 86400000;
  const results = await Promise.all(OUTAGE_PROVIDERS.map(p => outageCollect(p, cutoff)));
  const services = results.map(row => row.service);
  const records = results.flatMap(row => row.incidents).sort((a,b) =>
    Number(b.active) - Number(a.active) || Date.parse(b.updated_at || "1970-01-01") -
    Date.parse(a.updated_at || "1970-01-01")).slice(0, 250);
  const failures = results.filter(row => row.error).length;
  const body = {
    schema_version:"1.0", generated_at:checked, collection:"on_request_cached_180s",
    quality:failures ? "PARTIAL" : "OK", checked_count:services.length,
    failed_sources:failures, history_partial:results.filter(r => r.history_error).length,
    active_incidents:records.filter(r => r.active).length, recent_incidents:records.length,
    period_days:7, services, incidents:records,
    semantics:"公式発表の集約です。障害情報がないことは稼働保証を意味しません。未取得は正常扱いしません。",
    limitation:"オンデマンド取得・約3分キャッシュ。独自の外形監視、24時間常駐収集、DB永続保管は未実施。"
  };
  const response = new Response(JSON.stringify(body),{status:200,headers:OUTAGE_API_HEADERS});
  if (cache && ctx && ctx.waitUntil) {
    try { ctx.waitUntil(cache.put(cacheKey,response.clone())); } catch { /* optional cache */ }
  }
  return request.method === "HEAD" ? new Response(null,{status:200,headers:OUTAGE_API_HEADERS}) : response;
}
