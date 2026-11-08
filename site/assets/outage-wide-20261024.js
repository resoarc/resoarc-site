/* SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project */
/* SPDX-License-Identifier: MIT */
(()=>{"use strict";
const q=id=>document.getElementById(id);
const data={feed:null,category:"all",query:"",visible:24};
const cat={all:"すべて",cyber:"サイバー攻撃",leak:"情報漏えい",cloud:"クラウド",telecom:"通信",payments:"金融・決済",public:"公共・教育",general:"その他の停止"};
function d(iso){
 if(!iso)return "日時不明";
 let x=new Date(iso);if(!Number.isFinite(x.getTime()))return "日時不明";
 return new Intl.DateTimeFormat("ja-JP",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}).format(x);
}
function make(tag,cls,content){
 const el=document.createElement(tag);
 if(cls)el.className=cls;
 if(content!==undefined)el.textContent=String(content);
 return el;
}
function filtered(){
 const items=data.feed?.items||[];
 return items.filter(i=>(data.category==="all"||i.category===data.category)&&
   (!data.query||(i.title+" "+i.publisher+" "+i.category_label).toLocaleLowerCase().includes(data.query)));
}
function render(){
 if(!data.feed)return;
 const items=filtered(),list=q("wide-news-list");list.replaceChildren();
 q("wide-news-count").textContent=String(items.length)+" / "+data.feed.total+" 件";
 for(const i of items.slice(0,data.visible)){
   const card=make("article","wide-news-card");
   const row=make("div","wide-news-row");
   row.append(make("span","wide-news-category",i.category_label||cat[i.category]||"その他"));
   row.append(make("span","wide-news-unverified","未確認の報道"));
   card.append(row);
   const link=make("a","wide-news-title",i.title);
   try{
     const url=new URL(i.link,location.href);
     if(url.protocol==="https:"){link.href=url.href;link.rel="noopener noreferrer";link.target="_blank";}
   }catch{}
   card.append(link);
   const meta=make("div","wide-news-meta");
   meta.append(make("span","",i.publisher||"情報元未確認"));
   meta.append(make("time","",d(i.published_at)));
   card.append(meta);
   if(i.reported_state==="recovery_mentioned")
     card.append(make("p","wide-news-detected","見出しに復旧・再開の表現あり。実際の稼働状態は未確認です。"));
   list.append(card);
 }
 if(!items.length)list.append(make("p","wide-news-empty","この条件に一致する報道候補はありません。"));
 q("wide-news-more").hidden=items.length<=data.visible;
}
async function update(){
 const status=q("wide-news-status");
 try{
  const resp=await fetch("/api/v1/outages/discovery",{cache:"no-store",headers:{"Accept":"application/json"}});
  if(!resp.ok)throw Error("情報取得に失敗しました（HTTP "+resp.status+"）");
  const doc=await resp.json();
  if(doc.type!=="cross_sector_outage_discovery"||!Array.isArray(doc.items))throw Error("情報形式が異なります");
  data.feed=doc;
  q("wide-news-updated").textContent="最終収集："+d(doc.collected_at)+" JST";
  q("wide-news-source-count").textContent=String(doc.successful_queries||0)+" / "+String(doc.query_count||0)+" 検索成功";
  status.className="wide-news-status"+(doc.quality!=="OK"||doc.stale||doc.last_attempt_status==="failed"?" wide-news-warning":"");
  status.textContent=doc.last_attempt_status==="failed"?
    "最新収集は失敗。最後に保存した結果を表示しています。":
    doc.quality==="PARTIAL"?
    "一部の検索に失敗しました。表示は取得できた範囲の結果です。":
    doc.stale?"収集から時間が経過しています。最新とは限りません。":
    "自動収集は稼働中。ただし掲載するのは未確認の報道候補で、現在の停止・復旧が確定した情報ではありません。";
  for(const button of document.querySelectorAll("[data-wide-category]")){
    const c=button.dataset.wideCategory;
    button.textContent=cat[c]+(c!=="all"?" "+(doc.category_totals?.[c]||0):"");
  }
  render();
 }catch(e){
  status.className="wide-news-status wide-news-warning";
  status.textContent="ニュース候補を取得できません。稼働状況は不明です。"+String(e.message||e);
 }
}
document.addEventListener("DOMContentLoaded",()=>{
 if(!q("wide-news-list"))return;
 document.querySelectorAll("[data-wide-category]").forEach(btn=>{
   btn.addEventListener("click",()=>{
     data.category=btn.dataset.wideCategory;data.visible=24;
     document.querySelectorAll("[data-wide-category]").forEach(el=>
       el.setAttribute("aria-pressed",String(el===btn)));
     render();
   });
 });
 q("wide-news-search").addEventListener("input",ev=>{data.query=ev.target.value.trim().toLocaleLowerCase();data.visible=24;render();});
 q("wide-news-more").addEventListener("click",()=>{data.visible+=24;render();});
 q("wide-news-reload").addEventListener("click",update);
 update();
 setInterval(()=>{if(!document.hidden)update();},180000);
});
})();
