// SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFileSync} from "node:fs";
const source=readFileSync(new URL("../src/worker.js",import.meta.url),"utf8").replace("export default {","this.worker = {");
const now=new Date().toUTCString();
const title="PHPの重大脆弱性で新企業がWebサイト停止 - 新企業公式";
const xml='<?xml version="1.0"?><rss><channel><item><title>'+title+
'</title><link>https://news.google.com/rss/articles/CBMiaBc123?oc=5</link><pubDate>'+now+
'</pubDate><source url="https://www.new-example.jp">新企業公式</source></item></channel></rss>';
let notice=0,news=0,head=0;
const fakeFetch=async (target,opt={})=>{
  const url=String(target);
  if(url.includes("news.google.com/rss/search")){news++;return new Response(xml,{status:200});}
  if(url.includes("/api/v2/summary.json"))
    return new Response(JSON.stringify({status:{indicator:"none"},incidents:[]}),{status:200});
  if(url.includes("/api/v1/outages"))
    return new Response(JSON.stringify({schema_version:"1.0",checked_count:12,
      failed_sources:0,quality:"OK",services:[],incidents:[]}),{status:200});
  if(opt.method==="HEAD"){head++;return new Response(null,{status:200});}
  if(opt.redirect==="manual"){notice++;return new Response(
    "<html><body>PHPの脆弱性対応のため一時停止しておりましたが、すべてのサービスを再開いたしました。</body></html>",
    {status:200,headers:{"content-type":"text/html"}});}
  throw Error("Bad URL "+url);
};
const db=new Map();
const env={OUTAGES:{
 async get(k,format){const x=db.get(k);return x?JSON.parse(x):null;},
 async put(k,v){db.set(k,v);}
}};
const context=vm.createContext({URL,Request,Response,AbortSignal,Date,JSON,Object,Array,Promise,Map,Set,Boolean,Number,String,RegExp,console,fetch:fakeFetch});
vm.runInContext(source,context);
const parsed=context.phpRssParse(xml);
assert.equal(parsed.length,1,"RSS parser should recognize one relevant article");
assert.equal(parsed[0].publisher,"新企業公式");
assert.equal(parsed[0].status,"discovery_unverified");
assert.equal(context.phpOfficialState("PHP 影響調査。引き続き停止。サービスを順次再開"),"partial");
assert.equal(context.phpOfficialState("PHP一時停止しておりましたが、すべてのサービスを再開いたしました。"),"restored");
assert.equal(context.phpOfficialState("PHP 安全性の確認中のため一部機能を停止します"),null);
const doc=await context.worker.fetch(new Request("https://outage-feed.resoarc.com/v1/php"),env,{});
assert.equal(doc.status,200);
const data=await doc.json();
assert.equal(data.cases_total,59);
assert(data.discovery.items.length>=1);
assert.equal(data.discovery.items[0].status,"discovery_unverified");
assert.equal(data.discovery.quality,"OK");
assert(head<=24,"Avoid large number of HTTP probes");
assert(notice<=8,"Official rechecks bounded");
assert(news===3,"Exactly 3 search requests");
console.log("PHP_AUTO_DISCOVERY_TEST_PASS 13 checks. head="+head+" notices="+notice+" rss="+news);
