// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
(async()=>{
 const script=fs.readFileSync("site/_worker.js","utf8").replace("export default {","this.worker={");
 let requests=0;
 const feed={schema_version:"1.0",type:"cross_sector_outage_discovery",items:[{title:"Public advisory"}],total:1,
  source_breakdown:[{category:"cyber",source:"bing",success:true,found:1}]};
 const ctx=vm.createContext({URL,Request,Response,AbortSignal,Date,JSON,Array,Map,Set,Boolean,Number,String,RegExp,
 fetch:async url=>{requests++;assert.equal(String(url),"https://outage-feed.resoarc.com/v1/discovery");
    return new Response(JSON.stringify(feed),{status:200});}});
 vm.runInContext(script,ctx);
 const req=(method,url)=>new Request("https://resoarc.com"+url,{method});
 const result=await ctx.worker.fetch(req("GET","/api/v1/outages/discovery"),{},{});
 assert.equal(result.status,200);
 assert.equal((await result.json()).total,1);
 assert.equal((await ctx.worker.fetch(req("POST","/api/v1/outages/discovery"),{},{})).status,405);
 assert.equal((await ctx.worker.fetch(req("GET","/api/v1/outages/discovery?x=1"),{},{})).status,400);
 assert.equal(requests,1);
 console.log("WIDE_PROXY_TEST_PASS 5 checks");
})().catch(e=>{console.error(e);process.exit(1)});
