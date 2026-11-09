// SPDX-FileCopyrightText: 2026 ResoArc
// SPDX-License-Identifier: MIT
"use strict";
const $=id=>document.getElementById(id);
const fmt=value=>Number(value).toLocaleString("ja-JP");
const packageFile=name=>/\.(zip|iso)$/i.test(name);
const names=[
"attachment-count","auto-number","backup-migration","conditional-format","conditional","csv-export","date-calculator","field-help","grid-editor","input-template","kanban","list-aggregate","list-search","lookup-suggest","mail-compose","qr-code","record-toc","related-links","reuse-reset","save-navigation","tabs","text-normalizer","web8","site"
].sort((a,b)=>b.length-a.length);
function productFor(name){
  if(/^resoarcos[-.]/i.test(name))return "ResoArcOS";
  const low=name.toLowerCase();
  for(const slug of names)if(low.startsWith("resoarc-"+slug+"-")||low==="resoarc-"+slug+".zip")return slug;
  return packageFile(name)?"その他のZIP/ISO":"付属ファイル";
}
function cell(tr,text,number=false){
  const td=document.createElement("td");td.textContent=text;if(number)td.className="num";tr.append(td);
}
function rows(tbody,records,callback){
  tbody.replaceChildren();
  if(!records.length){const tr=document.createElement("tr");const td=document.createElement("td");td.colSpan=callback===renderProduct?4:3;td.textContent="該当データはまだありません";tr.append(td);tbody.append(tr);return;}
  for(const r of records){const tr=document.createElement("tr");callback(tr,r);tbody.append(tr);}
}
function renderProduct(tr,r){cell(tr,r.name);cell(tr,fmt(r.gh),true);cell(tr,fmt(r.site),true);cell(tr,fmt(r.gh+r.site),true);}
function renderFile(tr,r){cell(tr,r.name);cell(tr,fmt(r.gh),true);cell(tr,fmt(r.site),true);}
function renderChart(days){
  const wrap=$("chart");wrap.replaceChildren();
  const map=new Map(days.map(r=>[r.day,Number(r.downloads)]));
  const end=new Date();end.setUTCHours(0,0,0,0);
  const entries=Array.from({length:14},(_,i)=>{
    const d=new Date(end.getTime()-(13-i)*86400000);return {day:d.toISOString().slice(0,10),count:map.get(d.toISOString().slice(0,10))||0};
  });
  const max=Math.max(1,...entries.map(r=>r.count));
  for(const e of entries){
    const node=document.createElement("div");node.className="bar-item";node.title=e.day+" "+e.count+"件";
    const number=document.createElement("span");number.className="bar-number";number.textContent=e.count;
    const bar=document.createElement("div");bar.className="bar";bar.style.height=(Math.max(2,110*e.count/max))+"px";
    const label=document.createElement("span");label.className="bar-label";label.textContent=e.day.slice(5);
    node.append(number,bar,label);wrap.append(node);
  }
}
(async()=>{
try{
  const res=await fetch("/api/v1/downloads/summary",{cache:"no-store"});
  if(!res.ok)throw new Error("HTTP "+res.status);
  const d=await res.json();
  const gh=d.github?.available?d.github.assets:null;
  const site=d.site?.available?d.site.assets:null;
  $("gh-all").textContent=gh?fmt(gh.reduce((a,r)=>a+Number(r.downloads),0)):"未取得";
  $("gh-packages").textContent=gh?fmt(gh.filter(r=>packageFile(r.name)).reduce((a,r)=>a+Number(r.downloads),0)):"未取得";
  $("site-all").textContent=site?fmt(site.reduce((a,r)=>a+Number(r.downloads),0)):"未接続";
  const daily=d.site?.daily||[];
  const recent=new Date();recent.setUTCHours(0,0,0,0);recent.setUTCDate(recent.getUTCDate()-6);
  $("site-7days").textContent=site?fmt(daily.filter(r=>r.day>=recent.toISOString().slice(0,10)).reduce((a,r)=>a+Number(r.downloads),0)):"未接続";
  const fileMap=new Map();
  for(const x of gh||[]){const r=fileMap.get(x.name)||{name:x.name,gh:0,site:0};r.gh+=Number(x.downloads)||0;fileMap.set(x.name,r);}
  for(const x of site||[]){const r=fileMap.get(x.name)||{name:x.name,gh:0,site:0};r.site+=Number(x.downloads)||0;fileMap.set(x.name,r);}
  const files=[...fileMap.values()].sort((a,b)=>(b.gh+b.site)-(a.gh+a.site)||a.name.localeCompare(b.name));
  rows($("files"),files,renderFile);
  const grouped=new Map();
  for(const file of files.filter(x=>packageFile(x.name))){
    const name=productFor(file.name);const r=grouped.get(name)||{name,gh:0,site:0};
    r.gh+=file.gh;r.site+=file.site;grouped.set(name,r);
  }
  rows($("products"),[...grouped.values()].sort((a,b)=>(b.gh+b.site)-(a.gh+a.site)),renderProduct);
  renderChart(daily);
  $("updated").textContent="取得時刻："+new Date(d.updated_at).toLocaleString("ja-JP",{timeZone:"Asia/Tokyo"})+" JST";
  const warnings=[];
  if(!gh)warnings.push("GitHub APIの集計を取得できませんでした");
  if(!site)warnings.push("サイト直接配布の計測データベースを参照できません");
  $("state").textContent=warnings.length?warnings.join("。")+"。表示可能な経路のみ掲載します。":"両配布経路の集計を取得できました。";
}catch(err){$("state").textContent="集計を取得できませんでした。しばらくしてから再読み込みしてください。";$("gh-all").textContent=$("gh-packages").textContent=$("site-all").textContent=$("site-7days").textContent="未取得";}
})();
