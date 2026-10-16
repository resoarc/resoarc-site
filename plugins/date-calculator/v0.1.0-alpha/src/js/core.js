/* ResoArc date and period arithmetic: portable pure core / MIT */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.ResoArcDates=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const DAY=86400000;
function isoToTime(raw){
 if(typeof raw!=='string'||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(raw))throw Error('日付はYYYY-MM-DD形式で指定してください');
 const parts=raw.split('-').map(Number), ms=Date.UTC(parts[0],parts[1]-1,parts[2]);
 const d=new Date(ms);
 if(d.getUTCFullYear()!==parts[0]||d.getUTCMonth()!==parts[1]-1||d.getUTCDate()!==parts[2])throw Error('存在しない日付です: '+raw);
 return ms;
}
function calculate(start,end,mode,holidays){
 const first=isoToTime(start),last=isoToTime(end),diff=Math.round((last-first)/DAY);
 if(Math.abs(diff)>36525)throw Error('100年を超える期間は扱えません');
 if(mode==='calendar')return diff;
 if(mode!=='business')throw Error('集計方法が不正です');
 const set=new Set((holidays||[]).map(v=>isoToTime(v)));
 const dir=diff<0?-1:1;
 let result=0;
 for(let n=1;n<=Math.abs(diff);n++){
  const day=first+n*dir*DAY,weekday=new Date(day).getUTCDay();
  if(weekday!==0&&weekday!==6&&!set.has(day))result+=dir;
 }
 return result;
}
function normalize(raw){
 let rules;
 try{rules=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return null;}
 if(!Array.isArray(rules)||rules.length<1||rules.length>30)return null;
 const seen=new Set(),out=[];
 for(const r of rules){
  if(!r||typeof r!=='object'||Array.isArray(r))return null;
  const start=String(r.start||''),end=String(r.end||''),target=String(r.target||''),mode=r.mode||'calendar';
  if(!start||!end||!target||start===end||start===target||end===target||[start,end,target].some(v=>v.length>128||/[\u0000-\u001f]/.test(v))||!['calendar','business'].includes(mode)||seen.has(target))return null;
  const holidays=r.holidays||[];
  if(!Array.isArray(holidays)||holidays.length>400)return null;
  try{holidays.forEach(isoToTime);}catch(_){return null;}
  seen.add(target);out.push({start,end,target,mode,holidays});
 }
 return out;
}
function evaluate(rules,record){
 const checked=normalize(rules);
 if(!checked||!record||typeof record!=='object')throw Error('計算ルールまたはレコードが不正です');
 return checked.map(r=>{
  const start=record[r.start],end=record[r.end],target=record[r.target];
  if(!start||!end||!target)return {target:r.target,missing:true};
  if(!start.value||!end.value)return {target:r.target,missing:false,skip:true};
  try{return {target:r.target,missing:false,skip:false,value:String(calculate(start.value,end.value,r.mode,r.holidays))};}
  catch(error){return {target:r.target,missing:false,skip:true,error:error.message};}
 });
}
return {isoToTime,calculate,normalize,evaluate};
});
