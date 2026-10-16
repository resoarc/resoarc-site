import test from 'node:test';
import assert from 'node:assert/strict';
import {unzipSync,zipSync,strToU8} from 'fflate';
import {makeArchive,inspectArchive} from '../src/core.js';
import {planNewApp,createDraftApp} from '../src/migration.js';

const fields={properties:{
 Name:{type:'SINGLE_LINE_TEXT',code:'Name',label:'顧客名',required:true,unique:true,defaultValue:'sample'},
 Priority:{type:'DROP_DOWN',code:'Priority',label:'優先度',required:true,options:{High:{label:'High',index:'0'},Low:{label:'Low',index:'1'}}},
 Website:{type:'LINK',code:'Website',label:'ホームページ',protocol:'WEB'},
 Attachments:{type:'FILE',code:'Attachments',label:'資料'},
 Lookup:{type:'SINGLE_LINE_TEXT',code:'Lookup',label:'顧客参照',lookup:{relatedApp:{app:200}}},
 Related:{type:'REFERENCE_TABLE',code:'Related',label:'関連',referenceTable:{relatedApp:{app:210}}},
 Derived:{type:'CALC',code:'Derived',label:'計算',expression:'1+1'},
 Table:{type:'SUBTABLE',code:'Table',label:'明細',fields:{
   Detail:{type:'MULTI_LINE_TEXT',code:'Detail',label:'詳細'},
   Units:{type:'NUMBER',code:'Units',label:'数量'}
 }}
}};
const rows=[{
 Name:{value:'Alpha'},Priority:{value:'High'},Website:{value:'https://example.com'},
 Attachments:{value:[]},Lookup:{value:'X'},
 Table:{value:[{value:{Detail:{value:'test'},Units:{value:'12'}}}]}
}];
const fixture=async ()=>{
 const a=await makeArchive({appId:123,fields,layout:{layout:[]},records:rows,download:async()=>new Uint8Array()});
 return inspectArchive(a.zip,{expectedHash:a.hash});
};
test('v2 format retains verified source definitions and app plan reconstructs selectable fields and tables',async()=>{
 const a=await fixture();
 assert.equal(a.manifest.version,2);
 assert.equal(a.sourceFields.properties.Priority.options.High.label,'High');
 const plan=planNewApp(a,'移行先アプリ');
 assert.equal(plan.name,'移行先アプリ');
 assert.equal(plan.fieldCount,6);
 assert.equal(plan.properties.ResoArcRestoreKey.unique,true);
 assert.equal(plan.properties.Name.label,'顧客名');
 assert.equal(plan.properties.Name.required,false);
 assert.equal(plan.properties.Name.unique,false);
 assert.equal(plan.properties.Name.defaultValue,undefined);
 assert.deepEqual(plan.properties.Priority.options,fields.properties.Priority.options);
 assert.equal(plan.properties.Table.fields.Units.type,'NUMBER');
 assert.ok(plan.skipped.some(w=>w.startsWith('Lookup:')));
 assert.ok(plan.skipped.some(w=>w.startsWith('Related:')));
 assert.ok(plan.skipped.some(w=>w.startsWith('Derived:')));
});
test('draft creation uses ONLY preview endpoints and never deploys or changes existing app',async()=>{
 const plan=planNewApp(await fixture(),'Backup Copy 2026');
 const requests=[];
 const result=await createDraftApp(plan,async(path,method,body)=>{
   requests.push({path,method,body});
   if(path==='/k/v1/preview/app.json')return {app:'101',revision:'1'};
   if(path==='/k/v1/preview/app/form/fields.json')return {revision:'2'};
   throw new Error('unexpected API call');
 });
 assert.deepEqual(requests.map(r=>[r.path,r.method]),[
   ['/k/v1/preview/app.json','POST'],
   ['/k/v1/preview/app/form/fields.json','POST']
 ]);
 assert.equal(requests[1].body.app,101);
 assert.deepEqual(result,{appId:101,deployed:false,recordsCopied:0,requiresManualDeploy:true});
});
test('failed field update identifies newly created app ID for manual cleanup',async()=>{
 const p=planNewApp(await fixture(),'test');
 await assert.rejects(()=>createDraftApp(p,async(path)=>{
   if(path==='/k/v1/preview/app.json')return {app:'567'};
   throw new Error('permissions');
 }),/アプリ #567.*permissions/);
});
test('v1 archive remains restorable but cannot auto-create fields',async()=>{
 const a=await makeArchive({appId:123,fields,records:rows,download:async()=>new Uint8Array()});
 const files=unzipSync(a.zip);
 const manifest=JSON.parse(new TextDecoder().decode(files['manifest.json']));
 manifest.version=1;
 delete manifest.digests['schema/source-fields.json'];
 delete files['schema/source-fields.json'];
 files['manifest.json']=strToU8(JSON.stringify(manifest));
 const legacy=await inspectArchive(zipSync(files));
 assert.equal(legacy.manifest.version,1);
 assert.equal(legacy.sourceFields,null);
 assert.throws(()=>planNewApp(legacy,'legacy'),/v2形式/);
});
test('tampered v2 metadata is rejected before any scaffold planning',async()=>{
 const a=await makeArchive({appId:123,fields,records:rows,download:async()=>new Uint8Array()});
 const entries=unzipSync(a.zip);
 entries['schema/source-fields.json']=strToU8('{"properties":{"Evil":{"type":"FILE"}}}');
 await assert.rejects(()=>inspectArchive(zipSync(entries)),/ハッシュ/);
});
test('reject malicious reserved field names even when signed in a locally constructed fixture',()=>{
 const a={manifest:{version:2,sourceAppId:123},schema:{},records:[],sourceFields:{properties:{
   __proto__:{type:'SINGLE_LINE_TEXT',label:'Prototype'},
   constructor:{type:'SINGLE_LINE_TEXT',label:'Bad'},
   okay:{type:'SINGLE_LINE_TEXT',label:'ok'}
 }}};
 const plan=planNewApp(a,'clean');
 assert.deepEqual(Object.keys(plan.properties),['okay','ResoArcRestoreKey']);
});

test('v2 source fields must agree with portable record schema even after rehashing',async()=>{
 const a=await makeArchive({appId:123,fields,records:rows,download:async()=>new Uint8Array()});
 const z=unzipSync(a.zip);
 const source=JSON.parse(new TextDecoder().decode(z['schema/source-fields.json']));
 source.properties.Name.type='NUMBER';
 z['schema/source-fields.json']=strToU8(JSON.stringify(source));
 const m=JSON.parse(new TextDecoder().decode(z['manifest.json']));
 const data=await import('../src/core.js');
 m.digests['schema/source-fields.json']=await data.sha256(z['schema/source-fields.json']);
 z['manifest.json']=strToU8(JSON.stringify(m));
 await assert.rejects(()=>inspectArchive(zipSync(z)),/矛盾/);
});