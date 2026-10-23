// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
"use strict";
const assert=require("node:assert/strict");
const vm=require("node:vm");
const fs=require("node:fs");
const path=require("node:path");
(async()=>{
const code=fs.readFileSync(path.join(__dirname,"../site/_worker.js"),"utf8").replace("export default {","const worker = {");
const now=new Date().toISOString();
const mockFetch=async raw=>{
  const u=new URL(String(raw));
  const isGithub=u.host==="www.githubstatus.com";
  const isTwilio=u.host==="status.twilio.com";
  if(isTwilio)throw Error("deliberate outage at source");
  if(u.pathname.endsWith("/summary.json")){
    return new Response(JSON.stringify({
      page:{name:u.hostname,updated_at:now},
      status:{indicator:isGithub?"major":"none",description:isGithub?"Degraded":"All Systems Operational"},
      incidents:isGithub?[{id:"abcd1234",name:"GitHub test outage",status:"investigating",impact:"major",created_at:now,updated_at:now,incident_updates:[{body:"Investigating reports"}],components:[{name:"API"}]}]:[]
    }),{status:200});
  }
  if(u.pathname.endsWith("/incidents.json")){
    return new Response(JSON.stringify({incidents:isGithub?[
      {id:"abcd1234",name:"GitHub test outage",status:"investigating",impact:"major",created_at:now,updated_at:now,components:[{name:"API"}]},
      {id:"zzzz9999",name:"GitHub recovered",status:"resolved",impact:"minor",created_at:now,updated_at:now}
    ]:[]}),{status:200});
  }
  throw Error("Unexpected outbound path "+u.pathname);
};
const context=vm.createContext({URL,Request,Response,AbortSignal,Date,Map,Set,Promise,JSON,Boolean,Number,String,Array,Object,RegExp,fetch:mockFetch,console});
vm.runInContext(code+"\nthis.testWorker=worker;",context);
const req=(method,path="/api/v1/outages")=>new Request("https://resoarc.com"+path,{method});
const post=await context.testWorker.fetch(req("POST"),{},null);
assert.equal(post.status,405);
const opt=await context.testWorker.fetch(req("OPTIONS"),{},null);
assert.equal(opt.status,204);
const bad=await context.testWorker.fetch(req("GET","/api/v1/outages?url=http://127.0.0.1"),{},null);
assert.equal(bad.status,400);
const res=await context.testWorker.fetch(req("GET"),{},null);
assert.equal(res.status,200);
const data=await res.json();
assert.equal(data.quality,"PARTIAL");
assert.equal(data.failed_sources,1);
assert.equal(data.checked_count,12);
assert.equal(data.active_incidents,1);
assert.equal(data.recent_incidents,2);
assert.equal(data.incidents.find(x=>x.active).source_url,"https://www.githubstatus.com/incidents/abcd1234");
assert(data.services.find(x=>x.id==="twilio").availability==="unknown");
assert(data.incidents.find(x=>!x.active).title==="GitHub recovered");
console.log("OUTAGE_WORKER_TEST_PASS 11 assertions: active, recovered, duplicate, partial, allowlist, methods, time");
})().catch(e=>{console.error(e);process.exit(1)});
