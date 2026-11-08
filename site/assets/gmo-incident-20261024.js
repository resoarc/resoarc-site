/* SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project */
/* SPDX-License-Identifier: MIT */
(() => {
"use strict";
const $=id=>document.getElementById(id);
const fmt=iso=>{
  if(!iso)return "未確認";
  const d=new Date(iso);
  if(Number.isNaN(d.getTime()))return "未確認";
  return new Intl.DateTimeFormat("ja-JP",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}).format(d)+" JST";
};
const text=(tag,value,klass)=>{
 const n=document.createElement(tag);n.textContent=value;
 if(klass)n.className=klass;return n;
};
async function update(){
 const root=$("security-company-records"),info=$("security-company-info");
 if(!root||!info)return;
 try{
  const res=await fetch("/api/v1/outages/security",{cache:"no-store",headers:{"Accept":"application/json"}});
  if(!res.ok)throw Error("HTTP "+res.status);
  const data=await res.json();
  if(data.type!=="security_service_incidents"||!Array.isArray(data.incidents))throw Error("データ形式不正");
  root.replaceChildren();
  for(const item of data.incidents){
   const card=text("article","", "gmo-incident");
   const top=text("div","","gmo-incident-head");
   top.append(text("strong",item.name));
   const label=item.official_status==="restored"?"再開を公表":item.official_status==="suspended"?"全プラン停止を公表":"状況未確認";
   top.append(text("span",label,"gmo-incident-status"+(item.official_status==="restored"?" restored":"")));
   card.append(top,text("p",item.service,"gmo-incident-service"));
   card.append(text("p",item.summary,"gmo-incident-summary"));
   card.append(text("p",item.impact_note,"gmo-incident-note"));
   const proof=text("p","公式発表："+fmt(item.source_as_of)+" ／ 最終再確認："+fmt(item.last_verified_at),"gmo-incident-date");
   card.append(proof);
   if(item.source_access!=="verified")
    card.append(text("p","公式サイトの最新本文は取得未確認です。掲載する停止状態は最後に確認できた公式発表の内容です。","gmo-security-caution"));
   const link=text("a","GMOの公式発表を読む ↗","gmo-source-link");
   link.href=item.source_url;link.target="_blank";link.rel="noopener noreferrer";
   card.append(link);
   root.append(card);
  }
  if(!data.incidents.length)root.append(text("p","掲載対象はありません。"));
  info.textContent="収集："+fmt(data.collected_at)+" ／ PHP脆弱性の予防停止とは異なる事案";
  info.className="gmo-panel-info"+(data.stale||data.source_quality!=="OK"?" gmo-security-caution":"");
 }catch(e){
  info.textContent="公式情報の取得に失敗しました。最新の稼働状況は未確認です。";
  info.className="gmo-panel-info gmo-security-caution";
  root.replaceChildren(text("p","10月24日15時公表：全プラン停止継続、再開時期未定。最新の状態は公式発表をご確認ください。"));
 }
}
document.addEventListener("DOMContentLoaded",()=>{
 update();
 setInterval(()=>{if(!document.hidden)update();},180000);
});
})();