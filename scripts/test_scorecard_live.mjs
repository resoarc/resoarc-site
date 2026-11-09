import assert from "node:assert/strict";
import fs from "node:fs/promises";
import vm from "node:vm";

// The public Scorecard proxy is a fixed, clearly labeled historical snapshot.
// This test forbids accidentally bringing back a live GitHub API dependency.
const root = new URL("../site/", import.meta.url);
const source = await fs.readFile(new URL("_worker.js", root), "utf8");
const moduleData = "data:text/javascript;base64," + Buffer.from(source).toString("base64");
const worker = (await import(moduleData)).default;
const req = (path, options) => new Request("https://resoarc.com" + path, options);
let outboundCalls = 0;
globalThis.fetch = async () => { outboundCalls++; throw new Error("Scorecard must not contact external API"); };
const assets = {fetch: () => new Response("STATIC_OK", {status:200})};

let response = await worker.fetch(req("/api/scorecard"), {ASSETS:assets});
assert.equal(response.status, 200);
assert.equal(response.headers.get("content-type"), "application/json; charset=utf-8");
assert.equal(response.headers.get("cache-control"), "public, max-age=86400");
assert.equal(response.headers.get("x-content-type-options"), "nosniff");
const snapshot = await response.json();
assert.equal(snapshot.score, 5.9);
assert.equal(snapshot.date, "2026-10-16T19:51:20Z");
assert.equal(snapshot.repository, "historical-source");
assert.equal(snapshot.historical, true);
assert.equal(snapshot.cached, true);
assert(snapshot.source.includes("Past OpenSSF Scorecard"));
assert.equal(outboundCalls, 0);

response = await worker.fetch(req("/api/scorecard",{method:"HEAD"}),{ASSETS:assets});
assert.equal(response.status, 200);
assert.equal(await response.text(),"");
assert.equal(outboundCalls,0);

response = await worker.fetch(req("/api/scorecard",{method:"POST"}),{ASSETS:assets});
assert.equal(response.status,405);
assert.equal(response.headers.get("allow"),"GET, HEAD");

response = await worker.fetch(req("/products/"),{ASSETS:assets});
assert.equal(await response.text(),"STATIC_OK");

const js = await fs.readFile(new URL("assets/scorecard-live-20261017.js",root),"utf8");
const status = [{textContent:"確認中"},{textContent:""}];
const values = [{textContent:"5.9"}];
let clientFetchCalls = 0;
const context = {
 document:{querySelectorAll(selector) {
   if (selector === "[data-scorecard-state]") return status;
   if (selector === "[data-scorecard-value]") return values;
   return [];
 }},
 fetch:()=>{clientFetchCalls++;throw new Error("Unexpected client Scorecard fetch");}
};
vm.runInNewContext(js,context);
assert.equal(clientFetchCalls,0);
assert.equal(values[0].textContent,"5.9");
for(const el of status){
 assert(el.textContent.includes("過去の外部評価"));
 assert(el.textContent.includes("現行Codebergソースの評価ではありません"));
}
console.log("SCORECARD_HISTORICAL_PASS: immutable dated 5.9, GET/HEAD/405, static route, zero outbound calls");
