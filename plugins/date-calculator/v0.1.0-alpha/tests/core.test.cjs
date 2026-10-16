const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const core=require('../src/js/core.js');
test('leap year accepted and invalid date rejected',()=>{assert.ok(core.isoToTime('2024-02-29'));assert.throws(()=>core.isoToTime('2025-02-29'));});
test('calendar days exclude start',()=>assert.equal(core.calculate('2026-10-16','2026-10-19','calendar'),3));
test('weekends excluded',()=>assert.equal(core.calculate('2026-10-16','2026-10-19','business'),1));
test('holiday excluded',()=>assert.equal(core.calculate('2026-10-16','2026-10-19','business',['2026-10-19']),0));
test('negative business days',()=>assert.equal(core.calculate('2026-10-19','2026-10-16','business'),-1));
test('same day zero',()=>assert.equal(core.calculate('2026-10-16','2026-10-16','business'),0));
test('invalid and conflicting rule rejected',()=>{assert.equal(core.normalize('[{"start":"x","end":"y","target":"x"}]'),null);assert.equal(core.normalize('bad'),null);});
test('evaluates value without mutating original',()=>{const rec={start:{value:'2026-10-16'},end:{value:'2026-10-19'},days:{value:''}};assert.equal(core.evaluate([{start:'start',end:'end',target:'days',mode:'business'}],rec)[0].value,'1');assert.equal(rec.days.value,'');});
test('incomplete record does not write',()=>assert.equal(core.evaluate([{start:'s',end:'e',target:'t'}],{s:{value:'2026-10-19'}})[0].missing,true));
test('runtime changes only configured target',()=>{const events=[];const cfg={rules:JSON.stringify([{start:'s',end:'e',target:'n',mode:'calendar'}])};const context={kintone:{$PLUGIN_ID:'id',plugin:{app:{getConfig:()=>cfg}},events:{on:(ev,fn)=>events.push([ev,fn])}},console};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/js/desktop.js'),'utf8'),context);assert.equal(events.length,1);const record={s:{value:'2026-10-16'},e:{value:'2026-10-19'},n:{value:''},unrelated:{value:'safe'}};events[0][1]({record,type:'app.record.create.show'});assert.equal(record.n.value,'3');assert.equal(record.unrelated.value,'safe');});

test('date calculator skips unsupported calculated/status targets',()=>{
 const src={start:{type:'DATE',value:'2026-10-16'},end:{type:'DATE',value:'2026-10-19'},target:{type:'CALC',value:''}};
 const rules=[{start:'start',end:'end',target:'target',mode:'calendar'}];
 const result=core.evaluate(rules,src)[0];
 assert.equal(result.missing,true);
 assert.equal(src.target.value,'');
 src.target.type='NUMBER';
 assert.equal(core.evaluate(rules,src)[0].value,'3');
 src.start.type='SINGLE_LINE_TEXT';
 assert.equal(core.evaluate(rules,src)[0].missing,true);
});

test('clearing a source date clears stale calculated values without mutating input',()=>{
 const rules=[{start:'start',end:'end',target:'days',mode:'business'}];
 const record={start:{type:'DATE',value:''},end:{type:'DATE',value:'2026-10-19'},days:{type:'NUMBER',value:'9'}};
 const [result]=core.evaluate(rules,record);
 assert.equal(result.clear,true);
 assert.equal(result.value,'');
 assert.equal(record.days.value,'9');
});
test('runtime clears target when either date is erased',()=>{
 const events=[];
 const config={rules:JSON.stringify([{start:'start',end:'end',target:'days',mode:'calendar'}])};
 const sandbox={kintone:{$PLUGIN_ID:'test',plugin:{app:{getConfig:()=>config}},events:{on:(names,handler)=>events.push(handler)}},console};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/js/desktop.js'),'utf8'),sandbox);
 const record={start:{type:'DATE',value:'2026-10-16'},end:{type:'DATE',value:''},days:{type:'NUMBER',value:'3'}};
 events[0]({record,type:'app.record.edit.change.end'});
 assert.equal(record.days.value,'');
 record.end.value='2026-10-19';
 events[0]({record,type:'app.record.edit.change.end'});
 assert.equal(record.days.value,'3');
});

test('date calculation recomputes on save, including mobile',()=>{
 for(const eventType of ['app.record.create.submit','app.record.edit.submit','mobile.app.record.create.submit','mobile.app.record.edit.submit']){
  const handlers=[];
  const settings={rules:JSON.stringify([{start:'start',end:'end',target:'days',mode:'calendar'}])};
  const context={kintone:{$PLUGIN_ID:'test',plugin:{app:{getConfig:()=>settings}},events:{on:(types,callback)=>handlers.push({types,callback})}},console};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/js/desktop.js'),'utf8'),context);
  assert.equal(handlers.length,1);
  assert.ok(Array.from(handlers[0].types).includes(eventType));
  const record={start:{type:'DATE',value:'2026-10-16'},end:{type:'DATE',value:'2026-10-21'},days:{type:'NUMBER',value:'999'}};
  const event={type:eventType,record};
  assert.equal(handlers[0].callback(event),event);
  assert.equal(record.days.value,'5');
 }
});
test('date save rejects inaccessible or deleted configured field',()=>{
 const handlers=[];
 const cfg={rules:JSON.stringify([{start:'start',end:'end',target:'days'}])};
 const sandbox={kintone:{$PLUGIN_ID:'test',plugin:{app:{getConfig:()=>cfg}},events:{on:(types,handler)=>handlers.push(handler)}},console};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/js/desktop.js'),'utf8'),sandbox);
 const record={start:{type:'DATE',value:'2026-10-16'},end:{type:'DATE',value:'2026-10-19'}};
 const shown={type:'app.record.create.show',record};
 handlers[0](shown);
 assert.equal(shown.error,undefined);
 const submitted={type:'app.record.create.submit',record};
 handlers[0](submitted);
 assert.match(submitted.error,/保存を中止/);
});
test('invalid date input prevents save instead of keeping old calculated value',()=>{
 const handlers=[];
 const cfg={rules:JSON.stringify([{start:'start',end:'end',target:'days'}])};
 const sandbox={kintone:{$PLUGIN_ID:'test',plugin:{app:{getConfig:()=>cfg}},events:{on:(types,handler)=>handlers.push(handler)}},console};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../src/js/desktop.js'),'utf8'),sandbox);
 const record={start:{type:'DATE',value:'2026-02-30'},end:{type:'DATE',value:'2026-10-19'},days:{type:'NUMBER',value:'999'}};
 handlers[0]({type:'app.record.edit.submit',record});
 assert.match(record.days.error,/存在しない日付/);
 assert.equal(record.days.value,'999');
});
