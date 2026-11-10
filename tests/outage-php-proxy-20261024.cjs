// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
(async()=>{
const worker=fs.readFileSync("site/_worker.js","utf8").replace("export default {","this.worker={");
let calls=0;
const payload={schema_version:"1.0",type:"corporate_php_outages",companies:[{id:"x"}],providers:[]};
const context=vm.createContext({URL,Request,Response,AbortSignal,Date,JSON,Map,Set,Boolean,Number,Array,String,RegExp,
fetch:async url=>{calls++;assert.equal(url,"https://outage-feed.resoarc.com/v1/php");return new Response(JSON.stringify(payload),{status:200});}});
vm.runInContext(worker,context);
const req=(method,path)=>new Request("https://resoarc.com"+path,{method});
const res=await context.worker.fetch(req("GET","/api/v1/outages/php"),{},{});
assert.equal(res.status,200);
assert.equal((await res.json()).type,"corporate_php_outages");
assert.equal((await context.worker.fetch(req("POST","/api/v1/outages/php"),{},{})).status,405);
assert.equal((await context.worker.fetch(req("GET","/api/v1/outages/php?url=http://a"),{},{})).status,400);
assert.equal(calls,1);
console.log("PHP_PUBLIC_PROXY_PASS 5 assertions");
})().catch(e=>{console.error(e);process.exit(1)});
