/* SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project */
/* SPDX-License-Identifier: MIT */
(() => {
"use strict";
const $ = id => document.getElementById(id);
const state={data:null,mode:"active",search:""};
const datetime= v=>{
 if(!v)return "不明";
 const t=Date.parse(v);
 if(!Number.isFinite(t))return "不明";
 return new Intl.DateTimeFormat("ja-JP",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}).format(new Date(t))+" JST";
};
const elem=(tag,cls,txt)=>{
 const node=document.createElement(tag);
 if(cls)node.className=cls;
 if(txt!==undefined)node.textContent=String(txt);
 return node;
};
const statusLabel= id=>({
 suspended:["停止を公表","php-stop"],
 partial:["一部停止を公表","php-partial"],
 restored:["復旧を公表","php-restored"]
})[id]||["未分類","php-unverified"];
const probeLabel= id=>({
 http_responding:"HTTP応答あり（業務サービス稼働は未確認）",
 unverified_access:"HTTPアクセス制限等で未判定",
 possible_issue:"サイト接続異常 1回目（要再確認）",
 suspected_unavailable:"サイト不達の疑い（連続2回）",
 not_applicable:"外形監視対象外"
})[id]||"外形監視不明";
function card(item) {
 const article=elem("article","php-observation");
 const top=elem("div","php-observation-head");
 const company=elem("strong","php-company",item.name);
 const s=statusLabel(item.official_status);
 top.append(company,elem("span","php-status "+s[1],s[0]));
 article.append(top,elem("p","php-target",item.service));
 article.append(elem("div","php-check",probeLabel(item.website_check?.reachability)));
 if(item.note)article.append(elem("p","php-description",item.note));
 if(item.auto_status_updated)article.append(elem("div","php-auto-update",
   "公式告知の再確認によって公表状態を更新しました。元の分類："+statusLabel(item.declared_status)[0]));
 if(item.official_review?.review_note){
   article.append(elem("p","php-review",
     item.official_review.review_note+"（確認："+datetime(item.official_review.checked_at)+"）"));
 }

 const meta=elem("div","php-meta");
 meta.append(elem("span","","公表日："+item.source_date),
   elem("span","","外形確認："+datetime(item.website_check?.checked_at)));
 const link=elem("a","","一次情報・更新状況 ↗");
 link.href=item.source_url;link.rel="noopener noreferrer";link.target="_blank";
 meta.append(link);article.append(meta);
 return article;
}
function render() {
 const {data,mode,search}=state;
 if(!data)return;
 const ordered=[...data.companies].sort((a,b)=>{
   const rank={suspended:0,partial:1,restored:2};
   return (rank[a.official_status]??3)-(rank[b.official_status]??3)
     || (b.source_date||"").localeCompare(a.source_date||"") || a.name.localeCompare(b.name,"ja");
 });
 const result=ordered.filter(item=>(mode==="all" || (mode==="active"?item.official_status!=="restored":item.official_status===mode))
  && (!search || [item.name,item.service,item.note].join(" ").toLocaleLowerCase().includes(search)));
 const container=$("php-records");container.replaceChildren();
 $("php-results").textContent=result.length+" / "+data.cases_total+" 件";
 result.forEach(item=>container.append(card(item)));
 if(!result.length)container.append(elem("p","outage-message","一致する公表情報はありません。"));
}
function discoveries(data) {
 const container=$("php-discovery-items");
 if(!container)return;
 const candidates=(data.discovery?.items||[]).filter(entry=>{
   if(state.search&&!String(entry.title+" "+entry.publisher).toLocaleLowerCase().includes(state.search))return false;
   return true;
 });
 $("php-discovery-count").textContent=String(candidates.length);
 $("php-discovery-time").textContent="最終探索："+datetime(data.discovery?.checked_at);
 const notice=$("php-discovery-notice");
 const failure=data.discovery?.quality!=="OK";
 notice.textContent=failure?"ニュースRSSの一部を取得できませんでした。候補は部分的です。":
   "ニュース検索で自動発見した候補です。公式本文と個別サービスの状態は未照合のため、確定一覧には含めません。";
 notice.className="php-feed-info"+(failure?" php-info-warning":"");
 container.replaceChildren();
 candidates.slice(0,55).forEach(item=>{
   const article=elem("article","php-discovery-card");
   article.append(elem("span","php-unverified-tag","未照合の発見候補"));
   article.append(elem("strong","",item.title));
   article.append(elem("p","",item.publisher+"　／　"+datetime(item.published_at)));
   const link=elem("a","","ニュース原文を確認 ↗");
   link.href=item.link;link.target="_blank";link.rel="noopener noreferrer";
   article.append(link);container.append(article);
 });
 if(!candidates.length)container.append(elem("p","outage-message","現在の検索条件に一致する新規候補はありません。"));
}
function providers(data) {
 const out=$("php-providers");out.replaceChildren();
 (data.providers||[]).forEach(provider=>{
   const box=elem("div","php-provider");
   const title=elem("div","php-provider-top");
   title.append(elem("strong","",provider.name),
      elem("span","php-provider-availability",provider.source_access==="ok"?"公式情報取得済":"情報取得失敗"));
   box.append(title);
   const incidents=(provider.incidents||[]).filter(x=>x.is_php_related);
   if(incidents.length) {
     incidents.slice(0,4).forEach(incident=>{
       const info=elem("p","",incident.name+"  ／ "+incident.status);
       box.append(info);
     });
   }else{
     box.append(elem("p","",provider.source_access==="ok"
       ?"PHP関連の公表事案は対象一覧内で検出されませんでした"
       :"状況不明（正常とは判定しません）"));
   }
   const source=elem("a","","公式ステータス ↗");
   source.href=provider.source_url;source.target="_blank";source.rel="noopener noreferrer";
   box.append(source);out.append(box);
 });
}
async function retrieve(){
 const message=$("php-feed-info");
 try{
   const response=await fetch("/api/v1/outages/php",{headers:{"Accept":"application/json"},cache:"no-store"});
   if(!response.ok)throw new Error("API HTTP "+response.status);
   const doc=await response.json();
   if(doc.type!=="corporate_php_outages"||!Array.isArray(doc.companies))throw Error("不正な応答形式");
   state.data=doc;
   $("php-count-suspended").textContent=doc.stats.published_suspended;
   $("php-count-partial").textContent=doc.stats.published_partial;
   $("php-count-restored").textContent=doc.stats.published_restored;
   $("php-last-updated").textContent="最終収集："+datetime(doc.collected_at);
   message.className="php-feed-info"+(doc.stale||doc.last_attempt_status==="failed"?" php-info-warning":"");
   message.textContent=doc.stale?"定期収集が90分以上更新されていません。掲載状況は最新ではありません。"
      :doc.last_attempt_status==="failed"?"前回収集に失敗したため、最後に保存した情報を表示しています。"
      :"公式告知は公表日時点の情報です。HTTP応答は個別サービスの復旧を意味しません。";
   render();providers(doc);discoveries(doc);
 }catch(ex){
   message.className="php-feed-info php-info-warning";
   message.textContent="PHP関連の情報取得に失敗しました。前回表示がある場合も最新とは限りません。"+String(ex.message||ex);
 }
}
document.addEventListener("DOMContentLoaded",()=>{
 document.querySelectorAll("[data-php-filter]").forEach(button=>button.addEventListener("click",()=>{
   state.mode=button.dataset.phpFilter;
   document.querySelectorAll("[data-php-filter]").forEach(btn=>btn.setAttribute("aria-pressed",String(btn===button)));
   render();discoveries(state.data);
 }));
 $("php-search").addEventListener("input",e=>{state.search=e.target.value.trim().toLocaleLowerCase();render();discoveries(state.data);});
 $("php-fetch").addEventListener("click",retrieve);
 retrieve();
 setInterval(()=>{if(!document.hidden)retrieve();},180000);
});
})();
