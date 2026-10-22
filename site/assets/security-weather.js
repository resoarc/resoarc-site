/* ResoArc SWWW daily forecast renderer. No inline code. */
(()=>{
'use strict';
const d=JSON.parse(document.getElementById('swww-data').textContent);
const $=id=>document.getElementById(id);
const set=(id,val)=>{$(id).textContent=String(val)};
const displayDay=new Date(Date.now()+9*60*60*1000).toISOString().slice(0,10);
const snapshotOld=(displayDay!==d.date);
const wd=d.today.weather;
set('date-head',new Date(d.date+'T12:00:00+09:00').toLocaleDateString('ja-JP',{year:'numeric',month:'long',day:'numeric',weekday:'long'}));
set('checked-head','最終取得: '+(d.checked_at?new Date(d.checked_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false}):'不明'));
$('weather').classList.add(wd.code);
set('weather-label',wd.label);set('weather-icon',wd.icon);set('weather-sub',wd.subtitle);
set('weather-note',d.coverage_note);if(d.quality==='PARTIAL'){$('weather-sub').textContent+='（一部情報源が未取得）'}
set('yesterday-label',d.yesterday_summary.weather.label);
set('yesterday-icon',d.yesterday_summary.weather.icon);
set('yesterday-info','新着 '+d.yesterday_summary.new+' 件 ／ 悪用確認 '+d.yesterday_summary.kev+' 件');
set('quality',d.quality==='OK'?'観測中 / 正常':d.quality==='PARTIAL'?'一部欠測 / 参考値':'観測不能');
$('status-alert').hidden=d.quality==='OK'&&!snapshotOld;
if(snapshotOld){
 $('status-alert').textContent='この予報は '+d.date+' 時点の記録です。新しい日付の公開更新を確認するまで、現在の安全状態とは判断しないでください。';
 $('weather-label').textContent='前回の観測：'+wd.label;
 $('quality').textContent='掲載更新待ち / '+d.date;
}
for(const [source,status] of Object.entries(d.source_status)){const node=document.createElement('span');node.className='source-pill'+(status==='OK'?'':' bad');node.textContent=source+' '+(status==='OK'?'✓':'! '+status);$('sources').appendChild(node)}
set('new-count',d.today.new);set('critical-count',d.today.critical);set('kev-count',d.today.kev);
set('difficulty-count',d.today.difficulty.unknown===d.today.new?'要調査 '+d.today.difficulty.unknown+'件':'評価済 '+(d.today.new-d.today.difficulty.unknown)+'件');
set('damage-count',d.today.confirmed_victims===null?'確認情報なし':d.today.confirmed_victims+' 人');
const chart=$('chart'), labels=$('chart-labels');const max=Math.max(1,...d.trend.map(x=>x.count));
for(let i=0;i<d.trend.length;i++){const rec=d.trend[i],wrap=document.createElement('div'),num=document.createElement('span'),bar=document.createElement('div'),lbl=document.createElement('span');wrap.className='chart-day'+(i===6?' today':'');num.className='qty';num.textContent=rec.count;bar.className='bar swww-bar-h-'+Math.round(Math.max(3,rec.count/max*130));bar.title=rec.date+': '+rec.count+'件';wrap.append(num,bar);chart.appendChild(wrap);lbl.textContent=rec.date.slice(5).replace('-','/');labels.appendChild(lbl)}
for(const [key,label] of [['easy','軽微'],['moderate','中程度'],['hard','難しい'],['unknown','要調査']]){const count=d.today.difficulty[key]||0,outer=document.createElement('div');outer.className='diff-row';const name=document.createElement('span'),track=document.createElement('div'),fill=document.createElement('div'),num=document.createElement('b');name.textContent=label;track.className='diff-track';fill.className='diff-fill swww-diff-w-'+Math.round(d.today.new?count/d.today.new*100:0);num.textContent=count;track.appendChild(fill);outer.append(name,track,num);$('difficulty-chart').appendChild(outer)}

const r=d.resoarc_review||{};
const imp=r.impact||{},rsp=r.response||{};
set('ra-affected',(imp.affected||0)+'件');
set('ra-not-affected',(imp.not_affected||0)+'件');
set('ra-unreviewed',(imp.unreviewed??d.today.new)+'件');
set('ra-remediated',(rsp.REMEDIATED||0)+'件');
set('ra-unreviewed-response','未審査 '+(rsp.UNREVIEWED??d.today.new)+'件');
set('ra-investigating-response','調査中 '+(rsp.INVESTIGATING||0)+'件');
set('ra-active-response','対策予定・実施中 '+((rsp.PLANNED||0)+(rsp.MITIGATING||0))+'件');

const tbody=$('advisory-rows');let filter='today';
function cell(text,cls){const t=document.createElement('td');if(cls)t.className=cls;t.textContent=text;return t}
function renderRows(){const query=$('search').value.toLowerCase().trim();tbody.replaceChildren();const todayDate=new Date(d.date+'T12:00:00+09:00');const weekDate=new Date(todayDate.getTime()-6*864e5).toISOString().slice(0,10);const matches=d.items.filter(x=>(filter==='all'||(filter==='today'?x.date===d.date||x.kev_date===d.date:x.date>=weekDate||x.kev_date>=weekDate))&&(!query||[x.id,x.title,x.source,x.package].join(' ').toLowerCase().includes(query)));for(const x of matches){const tr=document.createElement('tr'),primary=document.createElement('td'),lnk=document.createElement('a'),meta=document.createElement('small'),sev=document.createElement('td'),tag=document.createElement('span');lnk.textContent=x.id+' · '+x.title;lnk.href=x.url==='\x23'?'\x23':x.url;lnk.target='_blank';lnk.rel='noopener noreferrer';meta.textContent=x.date+' / '+(x.source_refs||[x.source]).join('・');primary.append(lnk,meta);tag.className='tag '+x.severity.toLowerCase();tag.textContent=x.severity;sev.append(tag);tr.append(primary,sev,cell(x.epss===null?'未収集':(x.epss*100).toFixed(1)+'%'),cell(x.exploited_in_wild?'既知の悪用':'確認情報なし'),cell(x.difficulty_label),cell(x.impact_level),cell(x.resoarc_impact==='AFFECTED'?'影響確認':x.resoarc_impact==='NOT_AFFECTED'?'対象外と審査済':'未判定'),cell(x.response_status_label||'未審査'));tbody.appendChild(tr)}set('listed-count','表示 '+matches.length+' / 統合 '+d.observed.total+' 件');$('empty').hidden=matches.length>0}
for(const b of document.querySelectorAll('[data-filter]')){b.addEventListener('click',()=>{filter=b.dataset.filter;for(const o of document.querySelectorAll('[data-filter]'))o.classList.toggle('active',o===b);renderRows()})}
$('search').addEventListener('input',renderRows);renderRows();
set('bulletin-count', '注意喚起 '+(d.bulletin_count||0)+' 件（CVE件数とは別集計）');
const bullets=(d.bulletins||[]).filter(x=>x.url&&x.url.startsWith('https://')).slice(0,18);
for(const b of bullets){const node=document.createElement('article');node.className='bulletin';const meta=document.createElement('div');meta.className='meta';meta.textContent=b.source+' / '+(b.published||'日付未確認').slice(0,10);const a=document.createElement('a');a.href=b.url;a.target='_blank';a.rel='noopener noreferrer';const title=document.createElement('b');title.textContent=b.title||b.id;a.appendChild(title);node.append(meta,a);$('bulletin-list').appendChild(node)}
if(!bullets.length){const msg=document.createElement('p');msg.className='micro';msg.textContent='確認できる注意喚起はありません。取得状態をご確認ください。';$('bulletin-list').appendChild(msg)}
})();
