import assert from "node:assert/strict";
import { readFile,copyFile,mkdtemp,rm } from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,resolve} from "node:path";
import {pathToFileURL} from "node:url";
const site=resolve(import.meta.dirname,"../../site");
const temp=await mkdtemp(join(tmpdir(),"swww-public-worker-"));
const src=join(site,"_worker.js");
const target=join(temp,"worker.mjs");
await copyFile(src,target);
const worker=(await import(pathToFileURL(target).href)).default;
let counts={static:0,secret:0};
const env={ASSETS:{fetch:async req=>{
  const path=new URL(req.url).pathname;
  if(path==="/api/v1/swww/catalog.json"){
    counts.static++;
    return new Response(await readFile(join(site,"api/v1/swww/catalog.json")),{
      status:200,headers:{"Content-Type":"application/json; charset=utf-8"}
    });
  }
  if(path.includes("security-weather-private")||path.includes("weather-assessments")){
    counts.secret++; return new Response("not found",{status:404});
  }
  return new Response("STATIC:"+path,{status:200});
}}};
async function hit(path,method="GET"){
 const request=new Request("https://resoarc.com"+path,{method});
 const response=await worker.fetch(request,env);
 const body=method==="HEAD"?"":await response.text();
 let value=null;try{value=JSON.parse(body)}catch{}
 return {response,body,value};
}
try{
 let r=await hit("/api/v1/swww/summary");
 assert.equal(r.response.status,200);
 assert.equal(r.value.available_records,250);
 assert.equal(r.value.source_count,13);
 assert(!("advisories" in r.value));
 assert.equal(r.response.headers.get("Access-Control-Allow-Origin"),"*");
 assert.equal(r.response.headers.get("Content-Type"),"application/json; charset=utf-8");
 console.log("PASS /summary 250 records, metadata, CORS");
 r=await hit("/api/v1/swww/advisories?technology=java&limit=1&page=1");
 assert.equal(r.response.status,200);
 assert(r.value.filtered_total>=1 && r.value.filtered_total<30);
 assert.equal(r.value.items.length,1);
 assert.equal(r.value.items[0].technologies.some(t=>t.id==="java"),true);
 assert.equal(r.value.has_next,r.value.filtered_total>1);
 const next=await hit("/api/v1/swww/advisories?technology=java&limit=1&page=2");
 assert.equal(next.value.items.length,1);
 assert.notEqual(next.value.items[0].id,r.value.items[0].id);
 console.log("PASS Java technology filter and pagination");
 r=await hit("/api/v1/swww/advisories?severity=CRITICAL&limit=100");
 assert.equal(r.response.status,200);
 assert(r.value.filtered_total>0);
 assert(r.value.items.every(i=>i.severity==="CRITICAL"));
 r=await hit("/api/v1/swww/advisories?q=GitLab&limit=50");
 assert(r.value.filtered_total>0);
 r=await hit("/api/v1/swww/advisories?exploited=true");
 assert(r.value.items.every(i=>i.known_exploited));
 console.log("PASS severity, keyword and exploited filters");
 r=await hit("/api/v1/swww/technologies");
 assert.equal(r.response.status,200);
 assert(r.value.technologies.some(t=>t.id==="oracle"));
 assert(r.value.technologies.some(t=>t.id==="java"));
 r=await hit("/api/v1/swww/advisories?limit=999");
 assert.equal(r.response.status,400);
 r=await hit("/api/v1/swww/advisories?unexpected=foo");
 assert.equal(r.response.status,400);
 r=await hit("/api/v1/swww/advisories", "POST");
 assert.equal(r.response.status,405);
 console.log("PASS taxonomy and input/method rejection");
 r=await hit("/api/v1/swww/advisories","HEAD");
 assert.equal(r.response.status,200);
 assert.equal(r.body,"");
 r=await hit("/api/v1/swww/advisories","OPTIONS");
 assert.equal(r.response.status,204);
 assert.equal(r.response.headers.get("Access-Control-Allow-Origin"),"*");
 console.log("PASS HEAD and CORS preflight");
 r=await hit("/api/scorecard");
 assert.equal(r.response.status,200);
 assert.equal(r.value.historical,true);
 r=await hit("/os/");
 assert.equal(r.body,"STATIC:/os/");
 assert.equal(counts.secret,0);
 console.log("PASS existing scorecard and static route unchanged");
 assert.equal(counts.static>4,true);
 console.log("SWWW_PUBLIC_API_WORKER_TESTS 6/6 PASS");
}finally{
 await rm(temp,{recursive:true,force:true});
}
