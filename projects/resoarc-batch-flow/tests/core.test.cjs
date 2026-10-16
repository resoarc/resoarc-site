/* ResoArc Batch Flow unit tests */
const test=require('node:test');
const assert=require('node:assert/strict');
const core=require('../src/js/core.js');
const read={type:'read',app:11,query:'Status = "New"'};
const update={type:'update',fields:{Status:'Done'}};
const copy={type:'copy',app:22,fields:{Destination:'Source'}};
const create={type:'create',app:22,fields:{Title:'hello'}};
const flow=(...steps)=>({id:'batch-main',name:'Batch test',cron:'0 18 * * *',steps});
const record=(id,extra={})=>({$id:{value:String(id)},...extra});
test('read-only flow is valid',()=>assert.equal(core.validateFlow(flow(read)).steps.length,1));
test('update needs a previous read step',()=>assert.throws(()=>core.validateFlow(flow(update)),/前段/));
test('prohibits prototype keys',()=>assert.throws(()=>core.validateFlow(flow(read,{type:'update',fields:JSON.parse('{"__proto__":"1"}')})),/使用できない/));
test('limits task count',()=>assert.throws(()=>core.validateFlow(flow(...Array(21).fill(read))),/20件/));
test('read-only dry-run never writes',async()=>{
  const calls=[];
  const result=await core.runFlow(flow(read,update),async(path,method,body)=>{
    calls.push({method,body});
    if(method==='GET')return {records:[record(5)]};
    throw Error('dry-run must never write');
  });
  assert.equal(result.results.length,2);
  assert.deepEqual(calls.map(c=>c.method),['GET']);
  assert.match(calls[0].body.query,/limit 101$/);
});
test('update uses selected ids and field values',async()=>{
  const calls=[];
  await core.runFlow(flow(read,update),async(path,method,body)=>{
    calls.push({method,body});
    return method==='GET'?{records:[record(1),record(2)]}:{};
  },{dryRun:false});
  assert.equal(calls[1].method,'PUT');
  assert.equal(calls[1].body.app,11);
  assert.deepEqual(calls[1].body.records,[{id:'1',record:{Status:{value:'Done'}}},{id:'2',record:{Status:{value:'Done'}}}]);
});
test('copy maps source to destination fields',async()=>{
  const calls=[];
  await core.runFlow(flow(read,copy),async(path,method,body)=>{
    calls.push({method,body});
    return method==='GET'?{records:[record(1,{Source:{value:'A'}})]}:{};
  },{dryRun:false});
  assert.equal(calls[1].body.app,22);
  assert.deepEqual(calls[1].body.records,[{Destination:{value:'A'}}]);
});
test('101 records cause abort before first write',async()=>{
  const calls=[];
  await assert.rejects(core.runFlow(flow(read,update),async(path,method,body)=>{
    calls.push(method);
    return {records:Array.from({length:101},(_,i)=>record(i+1))};
  },{dryRun:false}),/100件を超えています/);
  assert.deepEqual(calls,['GET']);
});
test('sequential run stops on error without running later tasks',async()=>{
  const calls=[];
  await assert.rejects(core.runFlow(flow(read,update,create),async(path,method)=>{
    calls.push(method);
    if(method==='GET')return {records:[record(1)]};
    throw Error('simulated error');
  },{dryRun:false}),/前のタスクの変更は自動的には取り消されません/);
  assert.deepEqual(calls,['GET','PUT']);
});
test('create uses static literal fields',async()=>{
  const calls=[];
  const result=await core.runFlow(flow(create),async(path,method,body)=>{calls.push({method,body});return{};},{dryRun:false});
  assert.equal(result.results[0].count,1);
  assert.deepEqual(calls[0].body.records,[{Title:{value:'hello'}}]);
});
test('missing source field aborts transfer',async()=>{
  await assert.rejects(core.runFlow(flow(read,copy),async()=>({records:[record(1)]}),{dryRun:false}),/転記元フィールドが見つかりません/);
});
test('updated values are available to the next copy step',async()=>{
  const calls=[];
  await core.runFlow(flow(read,{type:'update',fields:{Source:'Updated'}},copy),async(path,method,body)=>{
    calls.push({method,body});
    return method==='GET'?{records:[record(1,{Source:{value:'Before'}})]}:{};
  },{dryRun:false});
  assert.equal(calls[2].body.records[0].Destination.value,'Updated');
});
