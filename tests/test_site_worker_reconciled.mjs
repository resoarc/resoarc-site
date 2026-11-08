import {test} from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
const site=path.resolve("site");
const js=fs.readFileSync(path.join(site,"_worker.js"),"utf8");
const worker=(await import("data:text/javascript;base64,"+Buffer.from(js).toString("base64"))).default;
const catalog=fs.readFileSync(path.join(site,"api/v1/swww/catalog.json"));
let staticCount=0;
const events=[];
const env={
  ASSETS:{async fetch(request){
    staticCount++;
    const p=new URL(request.url).pathname;
    if(p==="/api/v1/swww/catalog.json")return new Response(catalog,{status:200,headers:{"Content-Type":"application/json"}});
    if(p==="/")return new Response("<html><body>ResoArc</body></html>",{status:200,headers:{"Content-Type":"text/html"}});
    if(p==="/downloads/resoarcos-pc-v0.1.0-dev-source.zip")return new Response("zip-bytes",{status:200,headers:{"Content-Type":"application/zip"}});
    return new Response("not found",{status:404});
  }},
  RESOARC_ACTIVITY:{writeDataPoint(data){events.push(data);}}
};
const wait=[];
const ctx={waitUntil(p){wait.push(p)}};
globalThis.fetch=async (url)=>{
  if(String(url).startsWith("https://api.securityscorecards.dev/"))
    return new Response(JSON.stringify({score:6.2,date:"2026-11-08T00:00:00Z"}),{status:200,headers:{"Content-Type":"application/json"}});
  throw new Error("no external network in tests");
};
const request=(route,init={})=>new Request("https://resoarc.com"+route,init);

test("SWWW API remains routed through the actual worker, not static fallback",async()=>{
  const n=staticCount;
  const r=await worker.fetch(request("/api/v1/swww/summary"),env,ctx);
  assert.equal(r.status,200);
  const data=await r.json();
  assert.ok(data.schema_version);
  assert.equal(staticCount,n+1); // approved public catalog via ASSETS, not endpoint fallback
});
test("SWWW technology filter endpoint",async()=>{
  const r=await worker.fetch(request("/api/v1/swww/technologies"),env,ctx);
  assert.equal(r.status,200);
  assert.ok(Array.isArray((await r.json()).technologies));
});
test("Scorecard is live when upstream is healthy",async()=>{
  const r=await worker.fetch(request("/api/scorecard"),env,ctx);
  assert.equal(r.status,200);
  assert.equal((await r.json()).score,6.2);
});
test("Scorecard only allows safe read methods",async()=>{
  const r=await worker.fetch(request("/api/scorecard",{method:"POST"}),env,ctx);
  assert.equal(r.status,405);
});
test("Privacy-safe tracking is opt-in and excludes full referrer",async()=>{
  const r=await worker.fetch(request("/",{headers:{"Referer":"https://note.com/private/path?id=123"}}),env,ctx);
  assert.equal(r.status,200);
  await Promise.all(wait);
  assert.ok(events.length);
  assert.equal(events.at(-1).blobs[3],"note.com");
  assert.ok(!JSON.stringify(events).includes("private/path"));
});
test("Published ZIP download requests are counted as requests, not completions",async()=>{
  const r=await worker.fetch(request("/downloads/resoarcos-pc-v0.1.0-dev-source.zip"),env,ctx);
  assert.equal(r.status,200);
  await Promise.all(wait);
  assert.equal(events.at(-1).blobs[1],"download_request");
});
test("Outage Radar dynamic routes remain defined in the worker",()=>{
  for(const route of ["/api/v1/outages/discovery","/api/v1/outages/hourly","/api/v1/outages/php","/api/v1/outages"]){
    assert.ok(js.includes('url.pathname === "'+route+'"'),route);
  }
});
