/** ResoArc Pages Worker.
 * Static files are served unchanged. Public SWWW API is read-only and sourced
 * exclusively from an approved, sanitized, versioned daily catalog.
 * No network connections to the internal ResoArc database are exposed.
 * Privacy-first request aggregates require an optional Analytics Engine binding.
 */
const HISTORICAL_SCORECARD = Object.freeze({
  score: 5.9,
  date: "2026-10-16T19:51:20Z",
  repository: "historical-source",
  source: "Past OpenSSF Scorecard measurement, not current Codeberg",
  cached: true,
  historical: true,
});
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
    if (url.pathname === "/api/v1/outages/discovery") return outageWideNewsProxy(request);
    if (url.pathname === "/api/v1/outages/security") return outageSecurityProxy(request);
    if (url.pathname === "/api/v1/outages/php") return outagePhpProxy(request);
    if (url.pathname === "/api/v1/outages/hourly") return outageHourlyProxy(request);
    if (url.pathname === "/api/v1/outages") return outageRadarRequest(request, ctx);
    if (API_ROUTES.has(url.pathname)) return securityWeatherRequest(request, env, url);
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
      return new Response(request.method === "HEAD" ? null : JSON.stringify({...HISTORICAL_SCORECARD, live_status: "temporarily_unavailable"}), {
        status: 200,
        headers: {...headers, "Cache-Control": "no-store"},
      });
    }
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

/* Public read-only proxy to the standalone hourly Cloudflare Cron/KV collector. */
async function outageHourlyProxy(request) {
  const method=request.method;
  if (method==="OPTIONS") return new Response(null,{status:204,headers:OUTAGE_API_HEADERS});
  if (method!=="GET" && method!=="HEAD")
    return new Response(JSON.stringify({error:"method_not_allowed"}),{status:405,headers:OUTAGE_API_HEADERS});
  if (new URL(request.url).search)
    return new Response(JSON.stringify({error:"unsupported_query"}),{status:400,headers:OUTAGE_API_HEADERS});
  try {
    const remote=await fetch("https://outage-feed.resoarc.com/v1/outages",{
      signal:AbortSignal.timeout(14000), headers:{"Accept":"application/json"},
      cf:{cacheTtl:60}
    });
    if(!remote.ok) throw new Error("status_"+remote.status);
    const data=await remote.json();
    if(data.schema_version!=="1.0" || data.collection_mode!=="hourly_cron" ||
       !Array.isArray(data.services) || !Array.isArray(data.incidents))
      throw new Error("hourly_schema_mismatch");
    return new Response(method==="HEAD"?null:JSON.stringify(data),{
      status:200,headers:{...OUTAGE_API_HEADERS,"Cache-Control":"public, max-age=120"}});
  }catch{
    return new Response(method==="HEAD"?null:JSON.stringify({
      error:"hourly_collection_unavailable",
      message:"Hourly snapshot was not available. Use /api/v1/outages for the live feed."
    }),{status:503,headers:{...OUTAGE_API_HEADERS,"Cache-Control":"no-store"}});
  }
}

/* Read-only access to official PHP service interruption notices and hourly HTTP observations. */
async function outagePhpProxy(request) {
  const method=request.method;
  if(method==="OPTIONS") return new Response(null,{status:204,headers:OUTAGE_API_HEADERS});
  if(method!=="GET" && method!=="HEAD")
    return new Response(JSON.stringify({error:"method_not_allowed"}),{status:405,headers:OUTAGE_API_HEADERS});
  if(new URL(request.url).search)
    return new Response(JSON.stringify({error:"unsupported_query"}),{status:400,headers:OUTAGE_API_HEADERS});
  try {
    const res=await fetch("https://outage-feed.resoarc.com/v1/php",{
      headers:{"Accept":"application/json"},signal:AbortSignal.timeout(14500),
      cf:{cacheTtl:75}
    });
    if(!res.ok)throw new Error("provider_response");
    const data=await res.json();
    if(data.schema_version!=="1.0" || data.type!=="corporate_php_outages" ||
       !Array.isArray(data.companies) || !Array.isArray(data.providers) ||
       data.companies.length>200 || data.providers.length>30)
      throw new Error("feed_schema");
    return new Response(method==="HEAD"?null:JSON.stringify(data),{
      status:200,headers:{...OUTAGE_API_HEADERS,"Cache-Control":"public, max-age=120"}});
  }catch{
    return new Response(method==="HEAD"?null:JSON.stringify({
      error:"php_status_feed_unavailable",
      message:"PHP incident updates are temporarily unavailable; no healthy-status inference is made."
    }),{status:503,headers:{...OUTAGE_API_HEADERS,"Cache-Control":"no-store"}});
  }
}

/* Separate access-controlled-free, read-only public proxy for official security incident notices. */
async function outageSecurityProxy(request) {
  const method=request.method;
  if(method==="OPTIONS")return new Response(null,{status:204,headers:OUTAGE_API_HEADERS});
  if(method!=="GET"&&method!=="HEAD")
    return new Response(JSON.stringify({error:"method_not_allowed"}),{status:405,headers:OUTAGE_API_HEADERS});
  if(new URL(request.url).search)
    return new Response(JSON.stringify({error:"unsupported_query"}),{status:400,headers:OUTAGE_API_HEADERS});
  try{
    const resp=await fetch("https://outage-feed.resoarc.com/v1/security-alerts",{
      headers:{"Accept":"application/json"},signal:AbortSignal.timeout(14000),cf:{cacheTtl:60}});
    if(!resp.ok)throw Error("upstream");
    const d=await resp.json();
    if(d.schema_version!=="1.0"||d.type!=="security_service_incidents"||
       !Array.isArray(d.incidents)||d.incidents.length>15)
      throw Error("schema");
    return new Response(method==="HEAD"?null:JSON.stringify(d),{
      status:200,headers:{...OUTAGE_API_HEADERS,"Cache-Control":"public, max-age=120"}});
  }catch{
    return new Response(method==="HEAD"?null:JSON.stringify({
      error:"official_security_incident_feed_unavailable",
      note:"No availability conclusion should be inferred"
    }),{status:503,headers:{...OUTAGE_API_HEADERS,"Cache-Control":"no-store"}});
  }
}

/* Read-only public proxy: UNVERIFIED news mentions, not live operational status. */
async function outageWideNewsProxy(request) {
  const method=request.method;
  if(method==="OPTIONS")
    return new Response(null,{status:204,headers:OUTAGE_API_HEADERS});
  if(method!=="GET"&&method!=="HEAD")
    return new Response(JSON.stringify({error:"method_not_allowed"}),{status:405,headers:OUTAGE_API_HEADERS});
  if(new URL(request.url).search)
    return new Response(JSON.stringify({error:"unsupported_query"}),{status:400,headers:OUTAGE_API_HEADERS});
  try{
    const response=await fetch("https://outage-feed.resoarc.com/v1/discovery",{
      headers:{"Accept":"application/json"},signal:AbortSignal.timeout(19000),
      cf:{cacheTtl:90}
    });
    if(!response.ok)throw Error("upstream_unavailable");
    const result=await response.json();
    if(result.schema_version!=="1.0"||result.type!=="cross_sector_outage_discovery"||
       !Array.isArray(result.items)||result.items.length>200||
       typeof result.total!=="number"||result.total>200||
       !Array.isArray(result.source_breakdown) || result.source_breakdown.length>20)
      throw Error("unexpected_discovery_schema");
    return new Response(method==="HEAD"?null:JSON.stringify(result),{
      status:200,headers:{...OUTAGE_API_HEADERS,"Cache-Control":"public, max-age=90"}
    });
  }catch{
    return new Response(method==="HEAD"?null:JSON.stringify({
      error:"wide_news_discovery_unavailable",
      note:"Do not infer that no service outages exist when discovery is unavailable."
    }),{status:503,headers:{...OUTAGE_API_HEADERS,"Cache-Control":"no-store"}});
  }
}
