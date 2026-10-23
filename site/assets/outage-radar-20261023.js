
/* SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project */
/* SPDX-License-Identifier: MIT */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const state = {data:null, mode:"active", search:"", category:"all", service:"all"};
  const jst = value => {
    if (!value || Number.isNaN(Date.parse(value))) return "時刻未確認";
    return new Intl.DateTimeFormat("ja-JP",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}).format(new Date(value))+" JST";
  };
  const node = (tag, cls, value) => {
    const e=document.createElement(tag);
    if(cls)e.className=cls;
    if(value!==undefined)e.textContent=String(value);
    return e;
  };
  const statusLabel = row => {
    if (!row.active) return ["復旧済み",""];
    if (row.status==="monitoring") return ["経過観察中","monitor"];
    if (row.impact==="critical" || row.impact==="major") return ["重大障害","severe"];
    return ["障害・性能低下","active"];
  };
  const selectService = id => {
    state.service=id;
    const category=$("outage-category"); category.value="all";
    state.category="all"; paintIncidents();
    $("outage-feed").scrollIntoView({behavior:"smooth",block:"start"});
  };
  const summary = data => {
    const active=data.incidents.filter(r=>r.active);
    $("metric-active").textContent=String(active.length);
    $("metric-major").textContent=String(active.filter(r=>["major","critical"].includes(r.impact)).length);
    $("metric-recovered").textContent=String(data.incidents.filter(r=>!r.active).length);
    $("metric-unknown").textContent=String(data.failed_sources);
    $("outage-stamp").textContent="最終確認："+jst(data.generated_at);
    const alert=$("outage-alert");
    if (data.quality !== "OK" || data.history_partial) {
      alert.hidden=false;alert.classList.add("problem");
      alert.textContent="一部の公式ソースを取得できませんでした。未取得を正常扱いしていません。取得失敗："+data.failed_sources+"件、履歴取得不足："+data.history_partial+"件。";
    } else {
      alert.hidden=true;alert.classList.remove("problem");
    }
    const categories=[...new Set(data.services.map(r=>r.category))].sort();
    const dropdown=$("outage-category");const previous=dropdown.value;
    dropdown.replaceChildren(new Option("すべての分野","all"),...categories.map(c=>new Option(c,c)));
    dropdown.value=categories.includes(previous)?previous:"all";
    const grid=$("outage-services");grid.replaceChildren();
    data.services.forEach(service=>{
      const critical=["major","critical"].includes(service.overall);
      const error=service.availability==="unknown";
      const trouble=service.active_count>0 || service.overall==="minor";
      const link=node("a","outage-service "+(error?"unknown":critical?"critical":trouble?"reported":""));
      link.href=service.source_url;link.target="_blank";link.rel="noopener noreferrer";
      const dot=node("span","mark");dot.setAttribute("aria-hidden","true");
      const group=node("div");
      group.append(node("strong","",service.name),
        node("small","",error?"取得失敗":trouble?(service.active_count+"件の公表中の障害"):"現在の障害報告なし"));
      link.append(dot,group,node("span","arrow","↗"));
      link.title="公式ステータスページを開く";
      grid.append(link);
    });
  };
  const paintIncidents = () => {
    if (!state.data)return;
    const list=$("outage-items"), data=state.data;
    let incidents=data.incidents.filter(r => {
      if(state.mode==="active" && !r.active)return false;
      if(state.mode==="major" && !(r.active && ["critical","major"].includes(r.impact)))return false;
      if(state.mode==="recovered" && r.active)return false;
      if(state.category!=="all" && r.category!==state.category)return false;
      if(state.service!=="all" && r.service_id!==state.service)return false;
      const text=[r.service,r.title,r.detail,...r.components].join(" ").toLocaleLowerCase();
      return !state.search || text.includes(state.search);
    });
    list.replaceChildren();
    $("outage-result-count").textContent=incidents.length+"件を表示 / "+data.recent_incidents+"件を収集";
    if (!incidents.length) {
      list.append(node("div","outage-message",state.mode==="active"?
        "対象の公式ステータスページでは、条件に一致する継続中の障害が報告されていません。実際の稼働保証ではありません。":
        "該当する公表事案がありません。"));
      return;
    }
    incidents.slice(0,130).forEach(row=>{
      const item=node("article","outage-item"), head=node("div","outage-item-head");
      const [label,level]=statusLabel(row);
      head.append(node("span","outage-item-service",row.service+" / "+row.category),
        node("span","outage-badge "+level,label));
      item.append(head,node("h3","",row.title));
      if(row.detail) item.append(node("p","",row.detail));
      if(row.components.length)item.append(node("p","", "影響範囲："+row.components.join(" / ")));
      const meta=node("div","outage-item-meta");
      meta.append(node("span","", "公表："+jst(row.started_at)),node("span","", "更新："+jst(row.updated_at)));
      const link=node("a","","公式情報・原文 ↗");link.href=row.source_url;link.target="_blank";link.rel="noopener noreferrer";
      meta.append(link);item.append(meta);list.append(item);
    });
  };
  async function refresh() {
    const btn=$("outage-refresh");btn.disabled=true;btn.textContent="公式情報を取得中…";
    try {
      const response=await fetch("/api/v1/outages",{headers:{"Accept":"application/json"},cache:"no-store"});
      if(!response.ok)throw new Error("HTTP "+response.status);
      const data=await response.json();
      if(!Array.isArray(data.incidents)||!Array.isArray(data.services))throw new Error("応答形式が不正です");
      state.data=data;summary(data);paintIncidents();
    } catch(error) {
      const warning=$("outage-alert");warning.hidden=false;warning.classList.add("problem");
      warning.textContent="障害情報を取得できませんでした。前回の表示がある場合は最新ではありません。 "+String(error.message||error);
      if(!state.data)$("outage-items").replaceChildren(node("div","outage-message problem","データ取得に失敗しました。再取得をお試しください。"));
    } finally{btn.disabled=false;btn.textContent="情報を更新";}
  }
  document.addEventListener("DOMContentLoaded",()=>{
    document.querySelectorAll("[data-outage-mode]").forEach(button=>{
      button.addEventListener("click",()=>{
        state.mode=button.dataset.outageMode;
        document.querySelectorAll("[data-outage-mode]").forEach(b=>b.setAttribute("aria-pressed",String(b===button)));
        paintIncidents();
      });
    });
    $("outage-search").addEventListener("input",e=>{state.search=e.target.value.toLocaleLowerCase().trim();paintIncidents();});
    $("outage-category").addEventListener("change",e=>{state.category=e.target.value;state.service="all";paintIncidents();});
    $("outage-refresh").addEventListener("click",refresh);
    $("outage-clear").addEventListener("click",()=>{state.service="all";state.category="all";$("outage-category").value="all";$("outage-search").value="";state.search="";paintIncidents();});
    refresh();
    setInterval(()=>{if(!document.hidden)refresh();},180000);
  });
})();
