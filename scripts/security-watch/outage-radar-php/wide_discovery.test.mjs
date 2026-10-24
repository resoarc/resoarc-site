// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFileSync} from "node:fs";
const source=readFileSync(new URL("../src/worker.js",import.meta.url),"utf8").replace("export default {","this.worker={");
const db=new Map();
const env={OUTAGES:{
  async get(k){return db.has(k)?JSON.parse(db.get(k)):null;},
  async put(k,v){db.set(k,v);}
}};
const date=new Date().toUTCString();
const article=(title,link,source="通信ニュース")=>'<item><title>'+title+'</title><link>'+link+'</link><pubDate>'+date+'</pubDate><source url="https://example.org">'+source+'</source></item>';
const fakeXml='<?xml version="1.0"?><rss><channel>'+
 article("GMO お名前.com デスクトップクラウド 不正アクセスでサービス停止","https://example.org/gmo-1")+
 article("通信障害発生 通信サービス利用できない 全国","https://example.org/telecom-2")+
 article("GMO お名前.com デスクトップクラウド 不正アクセスでサービス停止","https://example.org/duplicate-3")+
 article("災害で鉄道運行停止","https://example.org/train-4")+
 '</channel></rss>';
let fail=false,google=0,bing=0;
const get=async(url)=>{
  if(url.includes("news.google.com")){google++;return new Response("forbidden",{status:503});}
  if(url.includes("www.bing.com")){bing++;return fail?new Response("oops",{status:503}):
    new Response(fakeXml,{status:200});}
  throw Error("Unexpected network URL "+url);
};
const context=vm.createContext({URL,Request,Response,AbortSignal,Date,JSON,Object,Array,Promise,Map,Set,Boolean,Number,String,RegExp,console,fetch:get});
vm.runInContext(source,context);
assert.equal(context.wideRelevant("企業クラウドシステム障害、サービス停止"),true);
assert.equal(context.wideRelevant("災害で鉄道運行停止"),false);
assert.equal(context.wideClassify("GMOお名前.com 不正アクセスによる停止","general"),"cyber");
let d=await context.collectWideNews(env,"test");
assert.equal(d.query_count,12);
assert.equal(d.failed_queries,0);
assert.equal(d.bing_queries,12);
assert.equal(d.quality,"OK");
assert.equal(d.total,2,"Dedup by normalized title, filter irrelevant");
assert(d.items.every(x=>x.evidence==="unverified_media_mention"));
assert(d.items.some(x=>x.category==="cyber"));
assert(google===0&&bing===12);
const api=await context.worker.fetch(new Request("https://outage-feed.resoarc.com/v1/discovery"),env,{});
assert.equal(api.status,200);
const output=await api.json();assert.equal(output.total,2);
const trend=await context.worker.fetch(new Request("https://outage-feed.resoarc.com/v1/discovery/history"),env,{});
assert.equal((await trend.json()).history.length,1);
assert.equal((await context.worker.fetch(new Request("https://outage-feed.resoarc.com/v1/discovery?target=evil"),env,{})).status,404);
fail=true;
const old=await context.collectWideNews(env,"simulate_failure");
assert.equal(old.total,2,"Retain previous snapshot when all source queries fail");
const h=await context.readWideNews(env);
assert.equal(h.last_attempt_status,"failed");
assert.equal((await env.OUTAGES.get("wide:discovery:history:v1")).length,1);
console.log("WIDE_NEWS_DISCOVERY_TEST_PASS 17 assertions");
