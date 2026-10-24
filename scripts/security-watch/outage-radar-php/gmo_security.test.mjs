// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFileSync} from "node:fs";
const code=readFileSync(new URL("../src/worker.js",import.meta.url),"utf8").replace("export default {","this.worker={");
const store=new Map();
const env={OUTAGES:{
 async get(k){return store.get(k)?JSON.parse(store.get(k)):null;},
 async put(k,v){store.set(k,v);}
}};
let official="<html>お名前.com デスクトップクラウド / 全プランのサーバー停止を継続しております。 サービスの再開時期は未定です。</html>";
const context=vm.createContext({URL,Request,Response,AbortSignal,Date,JSON,Object,Array,Promise,Map,Set,Boolean,Number,String,RegExp,console,
 fetch:async(url)=>{assert.equal(String(url),"https://internet.gmo/news/article/250/");return new Response(official,{status:200,headers:{"content-type":"text/html"}});}});
vm.runInContext(code,context);
const api=url=>new Request("https://outage-feed.resoarc.com"+url);
let res=await context.worker.fetch(api("/v1/security-alerts"),env,{});
assert.equal(res.status,200);
let d=await res.json();
assert.equal(d.type,"security_service_incidents");
assert.equal(d.incidents.length,1);
assert.equal(d.incidents[0].official_status,"suspended");
assert.equal(d.incidents[0].source_access,"verified");
assert.equal(d.incidents[0].php_related,false);
official="<html>お名前.com デスクトップクラウド：全プランのサービスを再開しました。</html>";
await context.collectSecurityIncidents(env,"test");
d=await(await context.worker.fetch(api("/v1/security-alerts"),env,{})).json();
assert.equal(d.incidents[0].official_status,"restored");
assert.equal(d.incidents[0].source_access,"verified");
assert.equal((await context.worker.fetch(api("/v1/security-alerts?foo=evil"),env,{})).status,404);
console.log("GMO_SECURITY_INCIDENT_TEST_PASS 9 checks");
