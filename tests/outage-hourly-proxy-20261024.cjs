// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
(async()=>{
 const source=fs.readFileSync("site/_worker.js","utf8").replace("export default {","this.worker={");
 const data={schema_version:"1.0",collection_mode:"hourly_cron",services:[{id:"test"}],
   incidents:[{id:"a"}],collected_at:new Date().toISOString()};
 let called=0;
 const context=vm.createContext({URL,Request,Response,AbortSignal,Date,JSON,Map,Set,Array,Number,String,Boolean,
  fetch:async u=>{called++;assert.equal(u,"https://resoarc-outage-hourly.zin1985.workers.dev/v1/outages");return new Response(JSON.stringify(data),{status:200});}});
 vm.runInContext(source,context);
 const req=(method,path)=>new Request("https://resoarc.com"+path,{method});
 const answer=await context.worker.fetch(req("GET","/api/v1/outages/hourly"),{},{});
 assert.equal(answer.status,200);
 assert.equal((await answer.json()).collection_mode,"hourly_cron");
 assert.equal((await context.worker.fetch(req("POST","/api/v1/outages/hourly"),{},{})).status,405);
 assert.equal((await context.worker.fetch(req("GET","/api/v1/outages/hourly?x=1"),{},{})).status,400);
 assert.equal(called,1);
 console.log("OUTAGE_HOURLY_PROXY_PASS 5 checks");
})().catch(e=>{console.error(e);process.exit(1)});
