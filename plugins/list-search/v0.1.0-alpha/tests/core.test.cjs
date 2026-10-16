const test=require('node:test'),a=require('node:assert/strict'),core=require('../src/js/core.js');
test('search config validates supported modes',()=>a.equal(core.normalize([{code:'Name',operator:'contains'}]).length,1));
test('search config rejects unsupported operator',()=>a.equal(core.normalize([{code:'Name',operator:'script'}]),null));
test('search contains and normalization',()=>a.equal(core.filter([{Name:{value:'ＡBC'}},{Name:{value:'zzz'}}],{code:'Name',operator:'contains'},'abc').length,1));
test('search equality',()=>a.equal(core.filter([{Name:{value:'foo'}},{Name:{value:'foobar'}}],{code:'Name',operator:'equals'},'foo').length,1));
test('search prefix',()=>a.equal(core.filter([{Name:{value:'foo bar'}},{Name:{value:'bar foo'}}],{code:'Name',operator:'startsWith'},'foo').length,1));
test('search returns copy and does not mutate input',()=>{const items=[{Name:{value:'x'}}];const out=core.filter(items,{code:'Name'},'');a.notEqual(items,out);a.equal(items.length,1);});
test('search query wraps OR view filter before seek id',()=>{
 a.equal(core.buildQuery('Status = "A" or Status = "B"','500',500),'(Status = "A" or Status = "B") and ($id > 500) order by $id asc limit 500');
 a.equal(core.buildQuery('',null,200),'order by $id asc limit 200');
});
test('search query fails closed if condition missing',()=>a.throws(()=>core.buildQuery(null,null,500)));
test('scan two batches and retain view filter',async()=>{
 const calls=[];
 const fetch=async arg=>{calls.push(arg);return {records:calls.length===1?
  Array.from({length:500},(_,i)=>({$id:{value:String(i+1)},Name:{value:'test'+i}})):
  [{$id:{value:'501'},Name:{value:'target'}}]};};
 const result=await core.scan(fetch,{condition:'Status = "A" or Status = "B"',field:'Name'});
 a.equal(result.scanned,501);a.equal(result.possiblyTruncated,false);a.equal(calls.length,2);
 a.match(calls[1].query,/^\(Status = "A" or Status = "B"\) and \(\$id > 500\)/);
 a.deepEqual(calls[1].fields,['$id','Name']);a.equal(core.filter(result.records,{code:'Name'},'target').length,1);
});
test('scan enforces hard 2000-record cap without requesting 2001st',async()=>{
 let count=0;const result=await core.scan(async({query})=>{
  const n=++count;return {records:Array.from({length:500},(_,i)=>({$id:{value:String((n-1)*500+i+1)},Name:{value:'x'}}))};
 },{condition:'',field:'Name'});a.equal(result.scanned,2000);a.equal(count,4);a.equal(result.possiblyTruncated,true);
});
test('scan rejects duplicate or missing ids',async()=>{
 await a.rejects(core.scan(async()=>({records:[{$id:{value:'1'}},{$id:{value:'1'}}]}),{condition:'',field:'Name'}),/順序/);
});
test('scan cancellation returns no partial dataset',async()=>{
 let cancelled=false;
 await a.rejects(core.scan(async()=>{cancelled=true;return {records:[{$id:{value:'1'}}]};},{
  condition:'',field:'Name',shouldStop:()=>cancelled
 }),/中止/);
});
test('scan rejects malformed API data',async()=>a.rejects(core.scan(async()=>({foo:1}),{condition:'',field:'Name'}),/形式/));
