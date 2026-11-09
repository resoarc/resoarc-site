// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
(async()=>{
 const source=fs.readFileSync("site/_worker.js","utf8").replace("export default {","this.worker={");
 let got=0;
 const d={schema_version:"1.0",type:"security_service_incidents",incidents:[{id:"gmo-20261020"}]};
 const context=vm.createContext({URL,Request,Response,AbortSignal,Date,JSON,Object,Array,Map,Set,Boolean,Number,String,
 fetch:async u=>{got++;assert.equal(String(u),"https://outage-feed.resoarc.com/v1/security-alerts");return new Response(JSON.stringify(d),{status:200});}});
 vm.runInContext(source,context);
 const req=(method,path)=>new Request("https://resoarc.com"+path,{method});
 let r=await context.worker.fetch(req("GET","/api/v1/outages/security"),{},{});
 assert.equal(r.status,200);
 assert.equal((await r.json()).type,"security_service_incidents");
 assert.equal((await context.worker.fetch(req("POST","/api/v1/outages/security"),{},{})).status,405);
 assert.equal((await context.worker.fetch(req("GET","/api/v1/outages/security?x=1"),{},{})).status,400);
 assert.equal(got,1);
 console.log("GMO_STATUS_PUBLIC_PROXY_PASS 5 checks");
})().catch(e=>{console.error(e);process.exit(1)});
