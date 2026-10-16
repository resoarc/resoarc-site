const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('../site/assets/tools/suite-core.js');
test('CSV multiline and escaped quotes', () => assert.deepEqual(api.parseDelimited('id,note\r\n1,"a\n""b"""\r\n'), [{id:'1',note:'a\n"b"'}]));
test('TSV auto-detect', () => assert.deepEqual(api.parseDelimited('x\ty\na\tb'),[{x:'a',y:'b'}]));
test('CSV duplicate headers rejected', () => assert.throws(() => api.parseDelimited('x,x\n1,2')));
test('CSV unequal columns rejected', () => assert.throws(() => api.parseDelimited('x,y\n1')));
test('CSV unterminated quote rejected', () => assert.throws(() => api.parseDelimited('x\n"oops')));
test('JSON kintone record values unwrapped', () => assert.deepEqual(api.dataRows({records:[{x:{type:'SINGLE_LINE_TEXT',value:'ok'}}]}), [{x:'ok'}]));
test('bulk update previews only real changes', () => {const r=api.bulkPreview([{id:'a',v:'0'},{id:'b',v:'1'}],[{id:'a',v:'2'},{id:'b',v:'1'}],'id'); assert.equal(r.changedRecords,1); assert.equal(r.writeExecuted,false);});
test('bulk update missing key identified', () => assert.deepEqual(api.bulkPreview([{id:1}],[{id:2,v:3}],'id').unmatched,[2]));
test('bulk source collision is fatal', () => assert.throws(() => api.bulkPreview([{id:1},{id:1}],[],'id')));
test('bulk patch collision is fatal', () => assert.throws(() => api.bulkPreview([{id:1}],[{id:1},{id:1}],'id')));
test('bulk does not mutate baseline', () => {const a=[{id:1,v:2}];api.bulkPreview(a,[{id:1,v:3}],'id');assert.equal(a[0].v,2);});
test('duplicates compare normalized strings', () => {const r=api.duplicateGroups([{a:'Ａ',b:'X'},{a:'a ',b:'x'},{a:'b',b:'x'}],['a','b']);assert.equal(r.duplicateGroups,1);assert.deepEqual(r.groups[0].rowNumbers,[1,2]);});
test('duplicates skip wholly empty rows', () => assert.deepEqual(api.duplicateGroups([{a:''},{a:null}],['a']).ignoredRows,[1,2]));
test('lookup missing match', () => {const r=api.lookupAudit([{code:'2'}],[{code:'1'}],'code','code',{});assert.equal(r.issues[0].type,'not-found');});
test('lookup ambiguous master', () => {const r=api.lookupAudit([{code:'x'}],[{code:'X'},{code:'x'}],'code','code',{});assert.equal(r.issues[0].type,'ambiguous-master');});
test('lookup mismatched fields', () => {const r=api.lookupAudit([{code:'x',name:'old'}],[{code:'x',name:'new'}],'code','code',{name:'name'});assert.equal(r.issues[0].type,'value-mismatch');});
test('aggregate sum/count/average', () => {const d=[{cat:'a',n:'2'},{cat:'a',n:'4'},{cat:'b',n:'3'}];assert.equal(api.aggregate(d,'cat','n','sum').groups[0].value,6);assert.equal(api.aggregate(d,'cat',null,'count').groups[0].value,2);assert.equal(api.aggregate(d,'cat','n','average').groups[0].value,3);});
test('aggregate invalid numeric rows reported', () => {const r=api.aggregate([{cat:'A',n:'bad'}],'cat','n','sum');assert.deepEqual(r.skippedNonNumericRows,[1]);});
test('permission matrix does not claim effective rights', () => {const r=api.permissionAudit({rights:[{entity:{type:'GROUP',code:'G'},viewRecord:true}]});assert.equal(r.matrix[0].subject,'G');assert.equal(r.permissionsModified,false);assert.match(r.warnings[0],/実効権限/);});
test('report escapes HTML and is print friendly', () => {const r=api.reportHTML([{a:'<img src=x onerror=alert(1)>'}],['a'],'<script>');assert.match(r,/&lt;script&gt;/);assert.doesNotMatch(r,/<script>/);assert.match(r,/<table/);});
test('load text recognizes CSV and JSON', () => {assert.equal(api.loadText('a\n1','x.csv')[0].a,'1');assert.equal(api.loadText('[{"a":1}]','x.json')[0].a,1);});
test('rows reject nonsensical input', () => assert.throws(() => api.dataRows({foo:1})));

test('CSV forbids stray quotes inside unquoted columns',()=>assert.throws(()=>api.parseDelimited('name\nnot"valid'),/引用符/));
test('CSV extension overrides JSON sniffing on bracket-led cell',()=>{
 const rows=api.loadText('code,value\n[abc],42','batch.csv');assert.equal(rows[0].code,'[abc]');
});
test('record loader caps row count to prevent browser exhaustion',()=>assert.throws(()=>api.dataRows(Array.from({length:50001},()=>({foo:'x'}))),/50,000/));
test('duplicate compare fields must be distinct and bounded',()=>{
 assert.throws(()=>api.duplicateGroups([{id:'1'}],['id','id']),/重複/);
 assert.throws(()=>api.duplicateGroups([{id:'1'}],Array.from({length:21},(_,i)=>'field'+i)),/1～20/);
});
test('lookup audit rejects missing keys instead of false positives',()=>{
 assert.throws(()=>api.lookupAudit([{key:'a'}],[{key:'a'}],'','key'),/照合キー/);
 assert.throws(()=>api.lookupAudit([{key:'a'}],[{key:'a'}],'key','key',[]),/対応表/);
});
test('aggregate rejects finite individual numbers with infinite sum',()=>assert.throws(()=>api.aggregate([{c:'x',v:'1e308'},{c:'x',v:'1e308'}],'c','v','sum'),/範囲/));
test('permission audit rejects malformed rule elements',()=>assert.throws(()=>api.permissionAudit([null]),/権限ルール/));
test('printed reports reject oversized records and excessive columns',()=>{
 assert.throws(()=>api.reportHTML(Array.from({length:5001},()=>({v:'x'}))),/5,000/);
 assert.throws(()=>api.reportHTML([{x:'1'}],Array.from({length:51},(_,i)=>String(i))),/1～50/);
});

test('CSV parser rejects excessive rows before materializing 50k+ objects',()=>{
 const input='id\n'+Array.from({length:50001},(_,i)=>String(i)).join('\n');
 assert.throws(()=>api.parseDelimited(input),/50,000/);
});
test('CSV parser rejects 251 columns even on empty data',()=>{
 assert.throws(()=>api.parseDelimited(Array(251).fill('field').map((v,i)=>v+i).join(',')),/250列/);
});
test('CSV parser accepts exactly 250 columns',()=>{
 const input=Array.from({length:250},(_,i)=>'h'+i).join(',')+'\n'+Array.from({length:250},(_,i)=>String(i)).join(',');
 assert.equal(Object.keys(api.parseDelimited(input)[0]).length,250);
});
test('bulk preview treats number 1 and CSV string 1 as the same key',()=>{
 const r=api.bulkPreview([{key:1,a:'before'}],[{key:'1',a:'after'}],'key');
 assert.equal(r.changedRecords,1);
 assert.equal(r.unmatched.length,0);
});
test('bulk preview rejects keys that are structured objects',()=>{
 assert.throws(()=>api.bulkPreview([{key:{nested:1}}],[],'key'),/照合キー/);
});
test('permission audit handles explicit false text and absent rules safely',()=>{
 const r=api.permissionAudit({rights:[{entity:{type:'GROUP',code:'g'},viewRecord:'false',addRecord:'true',editRecord:false,deleteRecord:0}]});
 assert.equal(r.matrix[0].view,false);
 assert.equal(r.matrix[0].add,true);
 assert.equal(r.matrix[0].edit,false);
 assert.equal(r.matrix[0].delete,false);
 assert.throws(()=>api.permissionAudit({unrelated:[]}),/rights/);
});
test('report rejects duplicate column IDs or string for columns',()=>{
 assert.throws(()=>api.reportHTML([{a:'A'}],'a'),/配列/);
 assert.throws(()=>api.reportHTML([{a:'A'}],['a','a']),/重複/);
});
