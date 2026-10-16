import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {runInNewContext} from 'node:vm';
const code=readFileSync(new URL('../center-plugin/src/js/runtime.js',import.meta.url),'utf8');

function makeUi(record){
  let details,executionCount=0;
  const network=[];
  const header={
    elements:[],
    querySelector:()=>null,
    append(x){this.elements.push(x);}
  };
  const document={
    createElement(tag){
      return {
        tag,textContent:'',style:{},dataset:{},children:[],handlers:{},
        append(...xs){this.children.push(...xs);},
        addEventListener(event,fn){this.handlers[event]=fn;}
      };
    }
  };
  const kApi=async(path,method,params)=>{
    network.push({path,method,params});
    if(method==='GET')return{record:{...record,$revision:{value:'4'}}};
    if(method==='PUT')return{revision:network.length===2?'5':'6'};
    throw Error('unexpected request');
  };
  kApi.url=path=>path;
  const core={
    runFlow:async()=>{
      executionCount++;
      return {results:[{number:1,type:'read',count:0}]};
    }
  };
  const center={
    parseRecord:()=>({id:'fake',name:'test',steps:[{type:'read',app:10,query:''}]}),
    nextScheduledRun:()=> '2026-10-17T18:00:00Z'
  };
  const handlers={};
  const kintone={
    api:kApi,
    app:{getId:()=>99,record:{getHeaderMenuSpaceElement:()=>header}},
    events:{on:(names,fn)=>{for(const name of Array.isArray(names)?names:[names])handlers[name]=fn;}}
  };
  runInNewContext(code,{document,kintone,confirm:()=>true,ResoArcBatchFlow:core,ResoArcBatchCenter:center,console,Date});
  const event={record:{$id:{value:'7'},Steps:{value:[]},DailyTime:{value:'03:00'},RunState:{value:'待機'}}};
  handlers['app.record.detail.show'](event);
  const view=header.elements[0];
  const [title,testButton,runButton,message]=view.children;
  return {network,message,testButton,runButton,get executionCount(){return executionCount}};
}

test('manual writes blocked after ambiguous failure until operator resets to waiting',async()=>{
  const ui=makeUi({RunState:{value:'要確認'},DailyTime:{value:'03:00'}});
  await ui.runButton.handlers.click();
  assert.equal(ui.executionCount,0);
  assert.deepEqual(ui.network.map(x=>x.method),['GET']);
  assert.match(ui.message.textContent,/重複/);
});

test('one-time already completed cannot accidentally rerun',async()=>{
  const ui=makeUi({RunState:{value:'正常終了'},ScheduleType:{value:'一回'},DailyTime:{value:'03:00'}});
  await ui.runButton.handlers.click();
  assert.equal(ui.executionCount,0);
  assert.deepEqual(ui.network.map(x=>x.method),['GET']);
  assert.match(ui.message.textContent,/実行済み/);
});

test('preview remains available for review-needed batch and does not write',async()=>{
  const ui=makeUi({RunState:{value:'要確認'},DailyTime:{value:'03:00'}});
  await ui.testButton.handlers.click();
  assert.equal(ui.executionCount,1);
  assert.deepEqual(ui.network.map(x=>x.method),['GET']);
  assert.match(ui.message.textContent,/変更していません/);
});

test('manually running a waiting batch uses claim, steps, and final revision',async()=>{
  const ui=makeUi({RunState:{value:'待機'},DailyTime:{value:'03:00'},RunHistory:{value:''}});
  await ui.runButton.handlers.click();
  assert.equal(ui.executionCount,1);
  assert.deepEqual(ui.network.map(x=>x.method),['GET','PUT','PUT']);
  assert.equal(ui.network[1].params.revision,'4');
  assert.equal(ui.network[2].params.revision,'5');
  assert.equal(ui.network[1].params.record.RunState.value,'実行中');
  assert.equal(ui.network[2].params.record.RunState.value,'正常終了');
});
