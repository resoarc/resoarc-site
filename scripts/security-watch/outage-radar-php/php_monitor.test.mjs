// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import vm from "node:vm";
import fs from "node:fs";
const script=fs.readFileSync(new URL("../src/worker.js",import.meta.url),"utf8").replace("export default {","this.worker={");
const base=new Map();
const env={OUTAGES:{
  async get(k,format){const v=base.get(k);return v?JSON.parse(v):null;},
  async put(k,v){base.set(k,v);}
}};
let webResponse=503;
const feed={schema_version:"1.0",checked_count:12,failed_sources:0,quality:"OK",services:[],incidents:[]};
const fetch=async(url,opts={})=> {
 if(String(url).includes("/api/v2/summary.json"))
   return new Response(JSON.stringify({status:{indicator:"none"},incidents:[]}),{status:200});
 if(String(url).includes("/api/v1/outages"))
   return new Response(JSON.stringify(feed),{status:200});
 return new Response(null,{status:webResponse});
};
const context=vm.createContext({URL,Request,Response,AbortSignal,Date,JSON,Object,Array,Promise,Map,Set,Boolean,Number,String,RegExp,console,fetch});
vm.runInContext(script,context);
const w=context.worker;
let p=await w.fetch(new Request("https://outage-feed.resoarc.com/v1/php"),env,{});
assert.equal(p.status,200);
let data=await p.json();
assert.equal(data.cases_total,59);
assert.equal(data.provider_total,4);
assert.equal(data.stats.published_suspended,15);
assert.equal(data.stats.published_partial,14);
assert.equal(data.stats.published_restored,30);
assert.equal(data.stats.suspected_unavailable,0);
assert.equal(data.stats.probe_unverified,59);
const sampled=data.companies.find(x=>x.website_check.reachability==="possible_issue");
assert(sampled,"At least one website HEAD probe must run");
await w.scheduled({},env,{waitUntil:v=>{globalThis.run=v;}});
await globalThis.run;
data=await (await w.fetch(new Request("https://outage-feed.resoarc.com/v1/php"),env,{})).json();
assert.equal(data.companies.find(x=>x.id===sampled.id).website_check.reachability,"suspected_unavailable");
webResponse=403;
await w.scheduled({},env,{waitUntil:v=>{globalThis.run=v;}});await globalThis.run;
data=await(await w.fetch(new Request("https://outage-feed.resoarc.com/v1/php"),env,{})).json();
assert.equal(data.companies.find(x=>x.id===sampled.id).website_check.reachability,"unverified_access");
assert.equal(data.companies.find(x=>x.id==="tkc").official_status,"partial");
assert.equal((await w.fetch(new Request("https://outage-feed.resoarc.com/v1/php/abc"),env,{})).status,404);
console.log("PHP_MONITOR_TEST_PASS 12 assertions");
