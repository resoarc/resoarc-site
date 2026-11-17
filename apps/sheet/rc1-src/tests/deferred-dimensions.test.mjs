import test from 'node:test';
import assert from 'node:assert/strict';
import {scheduleDimensionUpdate} from '../src/deferred-dimensions.mjs';
import {escapeClipboardFormula,formatTsv} from '../src/sheet-operations.mjs';

function scheduler(){
 const jobs=[];
 return {enqueue:(fn)=>jobs.push(fn),run:(max=100)=>{let i=0;while(jobs.length&&i++<max)jobs.shift()();},pending:()=>jobs.length};
}
test('dimension updates once sheet becomes ready',()=>{
 const q=scheduler(),applied=[];let sheets=[];
 scheduleDimensionUpdate({getEngine:()=>({getAllSheets:()=>sheets,setColumnWidth:(...args)=>applied.push(args)}),
  isCurrent:()=>true,method:'setColumnWidth',dimensions:{'0':130},options:{id:'a'},
  schedule:q.enqueue,maxAttempts:8,onExhausted:()=>assert.fail('unexpected failure')});
 q.run(2);sheets=[{id:'a'}];q.run();
 assert.equal(applied.length,1);
 assert.deepEqual(applied[0],[{'0':130},{id:'a'}]);
 assert.equal(q.pending(),0);
});
test('missing dimension target reports a failure exactly once',()=>{
 const q=scheduler(),failures=[];
 scheduleDimensionUpdate({getEngine:()=>({getAllSheets:()=>[]}),isCurrent:()=>true,
  method:'setRowHeight',dimensions:{'1':32},options:{id:'missing'},schedule:q.enqueue,
  maxAttempts:4,onExhausted:v=>failures.push(v)});
 q.run();
 assert.deepEqual(failures,[{method:'setRowHeight',sheetId:'missing',attempts:4}]);
 assert.equal(q.pending(),0);
});
test('cancelled generation neither changes dimensions nor reports a stale failure',()=>{
 const q=scheduler();let current=true,applied=0,failed=0;
 scheduleDimensionUpdate({getEngine:()=>({getAllSheets:()=>[{id:'a'}],setColumnWidth:()=>applied++}),isCurrent:()=>current,
  method:'setColumnWidth',options:{id:'a'},dimensions:{},schedule:q.enqueue,onExhausted:()=>failed++});
 current=false;q.run();assert.equal(applied,0);assert.equal(failed,0);
});
test('temporary rejection is retried',()=>{
 const q=scheduler();let calls=0;
 scheduleDimensionUpdate({getEngine:()=>({getAllSheets:()=>[{id:'a'}],setRowHeight:()=>{if(++calls<3)throw Error('mounting');}}),
  isCurrent:()=>true,method:'setRowHeight',options:{id:'a'},dimensions:{},
  schedule:q.enqueue,maxAttempts:5,onExhausted:()=>assert.fail('unexpected failure')});
 q.run();assert.equal(calls,3);
});
test('formula-looking clipboard text is escaped; numeric values remain numeric',()=>{
 for(const input of ['=SUM(1,2)','+cmd','-quoted','@foo','  =D1','\t=5','\n+2']) {
  assert.equal(escapeClipboardFormula(input),"'"+input);
 }
 for(const value of ['Tokyo','0007','  ordinary',42,-9,0])
  assert.equal(escapeClipboardFormula(value),value);
 const output=formatTsv([[escapeClipboardFormula('=HYPERLINK("a","b")'),42]]);
 assert.ok(output.includes("'=HYPERLINK"));
 assert.ok(output.endsWith('\t42'));
});

test('dimension scheduler signals applied exactly once and permits release of pending gate',()=>{
 const q=scheduler(),settled=[];let available=false;
 scheduleDimensionUpdate({
  getEngine:()=>({getAllSheets:()=>available?[{id:'x'}]:[],setColumnWidth:()=>{}}),
  isCurrent:()=>true,method:'setColumnWidth',dimensions:{'0':85},options:{id:'x'},
  schedule:q.enqueue,maxAttempts:6,onSettled:r=>settled.push(r),
 });
 q.run(2);assert.deepEqual(settled,[]);
 available=true;q.run();assert.equal(settled.length,1);assert.equal(settled[0].status,'applied');
});
test('dimension scheduler reports cancellation or terminal failure exactly once',()=>{
 const q=scheduler(),settled=[],failed=[];let current=true;
 scheduleDimensionUpdate({getEngine:()=>({getAllSheets:()=>[]}),isCurrent:()=>current,
  method:'setRowHeight',dimensions:{},options:{id:'x'},
  schedule:q.enqueue,maxAttempts:3,onSettled:r=>settled.push(r),onExhausted:r=>failed.push(r)});
 q.run(2);current=false;q.run();
 assert.deepEqual(settled.map(x=>x.status),['cancelled']);assert.equal(failed.length,0);
 const q2=scheduler();
 scheduleDimensionUpdate({getEngine:()=>({getAllSheets:()=>[]}),isCurrent:()=>true,
  method:'setRowHeight',dimensions:{},options:{id:'x'},
  schedule:q2.enqueue,maxAttempts:2,onSettled:r=>settled.push(r),onExhausted:r=>failed.push(r)});
 q2.run();
 assert.deepEqual(settled.map(x=>x.status),['cancelled','exhausted']);assert.equal(failed.length,1);
});
