// SPDX-FileCopyrightText: 2026 ResoArc
// SPDX-License-Identifier: MIT
import { test } from "node:test";
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const worker = (await import(pathToFileURL(new URL("../site/_worker.js", import.meta.url).pathname.replace(/^\/(?=[A-Za-z]:)/, "")).href)).default;
function fakeEnvironment(status=200){
  const saved=[];
  const db={
    prepare(sql){
      if(sql.startsWith("INSERT"))return {bind(day,asset){return {run:async()=>{saved.push({day,asset});}}}};
      if(sql.startsWith("SELECT asset"))return {all:async()=>({results:saved.map(x=>({asset:x.asset,hits:1}))})};
      if(sql.startsWith("SELECT date_utc"))return {all:async()=>({results:saved.map(x=>({day:x.day,hits:1}))})};
      throw Error("unexpected statement");
    }
  };
  return {env:{ASSETS:{fetch:async()=>new Response("test", {status})},DOWNLOAD_DB:db},saved};
}
test("GET /downloads/*.zip records one successful full response only",async()=>{
 const {env,saved}=fakeEnvironment();
 const wait=[];
 const ctx={waitUntil:x=>wait.push(x)};
 const fetchPath=(method,headers={})=>worker.fetch(new Request("https://resoarc.com/downloads/resoarc-tabs-signed-qa.zip",{method,headers}),env,ctx);
 assert.equal((await fetchPath("GET")).status,200);
 await Promise.all(wait);
 assert.equal(saved.length,1);
 assert.equal(saved[0].asset,"resoarc-tabs-signed-qa.zip");
 await fetchPath("HEAD");
 await fetchPath("GET",{Range:"bytes=0-9"});
 assert.equal(saved.length,1,"HEAD and range requests must not increase counts");
 await worker.fetch(new Request("https://resoarc.com/downloads/unrelated.zip"),env,ctx);
 assert.equal(saved.length,1,"unknown filenames not counted");
});
test("non-200 responses cannot increment",async()=>{
 const {env,saved}=fakeEnvironment(404);
 await worker.fetch(new Request("https://resoarc.com/downloads/resoarc-tabs-signed-qa.zip"),env,{waitUntil:()=>{}});
 assert.equal(saved.length,0);
});
test("summary distinguishes unbound D1 from zero downloads",async()=>{
 const oldFetch=globalThis.fetch;
 globalThis.fetch=async()=>new Response(JSON.stringify([{tag_name:"demo",assets:[{name:"test.zip",download_count:3}]}]),{status:200});
 try{
   const env={ASSETS:{fetch:async()=>new Response("not used")}};
   const res=await worker.fetch(new Request("https://resoarc.com/api/v1/downloads/summary"),env,{});
   assert.equal(res.status,200);
   const d=await res.json();
   assert.equal(d.site.available,false);
   assert.equal(d.site.error,"database_not_bound");
   assert.equal(d.github.assets[0].downloads,3);
   assert.equal(d.github.available,true);
   const post=await worker.fetch(new Request("https://resoarc.com/api/v1/downloads/summary",{method:"POST"}),env,{});
   assert.equal(post.status,405);
 } finally {globalThis.fetch=oldFetch;}
});
