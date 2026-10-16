import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {runFromCenter} from '../worker/src/center-runner.mjs';
const require=createRequire(import.meta.url);
const core=require('../src/js/core.js');
const center=require('../control-app/control.js');
const val=value=>({value});
const due=()=>({
  $id:val('9'),$revision:val('10'),BatchName:val('Daily'),
  BatchEnabled:val('有効'),RunState:val('待機'),DailyTime:val('03:00'),
  NextRunAt:val('2026-10-15T18:00:00Z'),RunHistory:val(''),
  Steps:val([{value:{TaskType:val('read'),TargetApp:val('10'),Query:val(''),FieldsJSON:val('')}}])
});
test('next Japanese 03:00 from 02:00 JST is same day',()=>assert.equal(center.nextRunAt('03:00','2026-10-16T17:00:00Z'),'2026-10-16T18:00:00Z'));
test('next Japanese 03:00 from 04:00 JST is next day',()=>assert.equal(center.nextRunAt('03:00','2026-10-16T19:00:00Z'),'2026-10-17T18:00:00Z'));
test('convert control app step table to core flow',()=>{
 const flow=center.parseRecord(due(),core);
 assert.equal(flow.name,'Daily');assert.equal(flow.steps[0].app,10);
});
test('dry-run never claims or writes the control app',async()=>{
 const calls=[],adapter=async(path,method,body)=>{
  calls.push({path,method,body});
  if(method==='GET'&&body.app===99)return{records:[due()]};
  if(method==='GET')return{records:[{$id:val('11')}]};
  throw Error('must not write');
 };
 const result=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'false'},adapter,core,'2026-10-16T00:00:00Z');
 assert.equal(result.length,1);assert.ok(calls.every(x=>x.method==='GET'));
});
test('claim with revision, run and finalize',async()=>{
 const calls=[],adapter=async(path,method,body)=>{
  calls.push({path,method,body});
  if(method==='GET'&&body.app===99)return{records:[due()]};
  if(method==='GET')return{records:[{$id:val('11')}]};
  if(path==='/k/v1/record.json')return{revision:'11'};
  return {};
 };
 const result=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'true'},adapter,core,'2026-10-16T00:00:00Z');
 assert.equal(result[0].ok,true);
 const claims=calls.filter(x=>x.path==='/k/v1/record.json');
 assert.equal(claims.length,2);
 assert.equal(claims[0].body.revision,'10');
 assert.equal(claims[0].body.record.RunState.value,'実行中');
 assert.equal(claims[1].body.record.RunState.value,'正常終了');
 assert.equal(claims[0].body.record.NextRunAt.value,'2026-10-16T18:00:00Z');
});
test('simultaneous claim conflict prevents all business writes',async()=>{
 const calls=[],adapter=async(path,method,body)=>{
  calls.push({path,method,body});
  if(method==='GET')return{records:[due()]};
  throw Object.assign(Error('revision conflict'),{status:409});
 };
 const result=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'true'},adapter,core,'2026-10-16T00:00:00Z');
 assert.equal(result[0].skipped,true);assert.equal(calls.length,2);
});
test('failed business call marks job review required',async()=>{
 let n=0;const calls=[];
 const adapter=async(path,method,body)=>{
  calls.push({path,method,body});
  if(method==='GET'&&body.app===99)return{records:[due()]};
  if(method==='GET')throw Error('kintone 503');
  if(method==='PUT')return{revision:String(11+n++)};
  throw Error('unexpected');
 };
 const result=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'true'},adapter,core,'2026-10-16T00:00:00Z');
 assert.equal(result[0].ok,false);
 const last=calls.at(-1);
 assert.equal(last.body.record.RunState.value,'要確認');
});
test('Japanese task labels map to engine types',()=>{
  const rec=due();
  rec.Steps.value[0].value.TaskType.value='取得';
  assert.equal(center.parseRecord(rec,core).steps[0].type,'read');
});

test('legacy control records default to daily without migration',()=>{
  assert.equal(center.nextScheduledRun(due(),'2026-10-16T17:00:00Z'),'2026-10-16T18:00:00Z');
});
test('interval scheduling preserves cadence after missed ticks',()=>{
  const r=due();
  r.ScheduleType=val('間隔');
  r.IntervalMinutes=val('5');
  r.NextRunAt=val('2026-10-16T00:00:00Z');
  assert.equal(center.nextScheduledRun(r,'2026-10-16T00:17:02Z'),'2026-10-16T00:20:00Z');
  assert.equal(center.nextScheduledRun(r,'2026-10-16T00:17:02Z',{reset:true}),'2026-10-16T00:22:02Z');
});
test('one-minute interval moves to next full minute when previous tick was due',()=>{
  const r=due();
  r.ScheduleType=val('間隔');r.IntervalMinutes=val('1');
  r.NextRunAt=val('2026-10-16T00:00:00Z');
  assert.equal(center.nextScheduledRun(r,'2026-10-16T00:02:30Z'),'2026-10-16T00:03:00Z');
});
test('invalid interval and unknown schedule are rejected',()=>{
  const r=due();r.ScheduleType=val('間隔');r.IntervalMinutes=val('0');
  assert.throws(()=>center.nextScheduledRun(r),/1～10080/);
  r.IntervalMinutes=val('5.5');
  assert.throws(()=>center.nextScheduledRun(r),/1～10080/);
  r.ScheduleType=val('毎月');
  assert.throws(()=>center.nextScheduledRun(r),/スケジュール種別/);
});
test('invalid job is marked 要確認 once when writes are enabled',async()=>{
  const calls=[],record=due();
  record.ScheduleType=val('間隔');record.IntervalMinutes=val('0');
  const adapter=async(path,method,body)=>{
    calls.push({path,method,body});
    if(method==='GET')return {records:[record]};
    if(method==='PUT')return {revision:'11'};
    throw Error('unexpected write');
  };
  const result=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'true'},adapter,core,'2026-10-16T00:00:00Z');
  assert.equal(result[0].ok,false);
  const puts=calls.filter(x=>x.method==='PUT');
  assert.equal(puts.length,1);
  assert.equal(puts[0].body.record.RunState.value,'要確認');
  assert.equal(puts[0].body.revision,'10');
  assert.match(puts[0].body.record.RunHistory.value,/バッチ定義エラー/);
});
test('one minute tick only queries the control app if no job is due',async()=>{
  const calls=[];
  const adapter=async(path,method,body)=>{
    calls.push({path,method,body}); return {records:[]};
  };
  const result=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'true'},adapter,core,'2026-10-16T00:00:00Z');
  assert.deepEqual(result,[]);
  assert.equal(calls.length,1);
  assert.match(calls[0].body.query,/NextRunAt <=/);
  assert.match(calls[0].body.query,/NextRunAt != ""/);
  assert.match(calls[0].body.query,/limit 3/);
});
test('backlog is limited to two jobs per minute without writes on a dry run',async()=>{
  const calls=[],records=Array.from({length:11},(_,i)=>({...due(),$id:val(String(i+1))}));
  const adapter=async(path,method,body)=>{
    calls.push({path,method,body});
    if(body.app===99)return {records};
    return {records:[]};
  };
  const result=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'false'},adapter,core,'2026-10-16T00:00:00Z');
  assert.equal(result.length,2);
  assert.ok(calls.every(x=>x.method==='GET'));
});

test('one-time schedule uses the exact datetime and requires a date',()=>{
  const r=due();r.ScheduleType=val('一回');
  r.OneTimeAt=val('2026-10-22T01:45:00Z');
  assert.equal(center.nextScheduledRun(r,'2026-10-16T00:00:00Z'),'2026-10-22T01:45:00Z');
  delete r.OneTimeAt;
  assert.throws(()=>center.nextScheduledRun(r),/一回実行日時/);
});
test('one-time job automatically disables after a successful run',async()=>{
  const record=due(),calls=[];
  record.ScheduleType=val('一回');
  record.OneTimeAt=val('2026-10-16T00:00:00Z');
  const adapter=async(path,method,body)=>{
    calls.push({path,method,body});
    if(method==='GET'&&body.app===99)return {records:[record]};
    if(method==='GET')return {records:[]};
    if(method==='PUT'&&path==='/k/v1/record.json')return {revision:'11'};
    throw Error('unexpected call');
  };
  const r=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'true'},adapter,core,'2026-10-16T00:00:00Z');
  assert.equal(r[0].ok,true);
  const updates=calls.filter(x=>x.path==='/k/v1/record.json');
  assert.equal(updates[0].body.record.NextRunAt.value,'2026-10-16T00:00:00Z');
  assert.equal(updates[1].body.record.RunState.value,'正常終了');
  assert.equal(updates[1].body.record.BatchEnabled.value,'停止');
});

test('Workers Free worst-case tick uses at most 45 kintone API subrequests',async()=>{
  const records=Array.from({length:3},(_,i)=>{
    const rec=due();
    rec.$id=val(String(100+i));
    rec.Steps=val(Array.from({length:20},()=>({
      value:{TaskType:val('取得'),TargetApp:val('10'),Query:val(''),FieldsJSON:val('')}
    })));
    return rec;
  });
  let calls=0;
  const transport=async(path,method,body)=>{
    calls++;
    if(method==='GET'&&body.app===99)return {records};
    if(method==='GET'&&body.app===10)return {records:[]};
    if(method==='PUT'&&body.app===99)return {revision:'11'};
    throw Error('unexpected '+method+' '+path);
  };
  const results=await runFromCenter({RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'true'},transport,core,'2026-10-16T00:00:00Z');
  assert.equal(results.length,2);
  assert.ok(results.every(x=>x.ok));
  assert.equal(calls,45);
  assert.ok(calls<=50);
});
