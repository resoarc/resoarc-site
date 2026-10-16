import test from 'node:test';
import assert from 'node:assert/strict';
import * as m from '../src/core.mjs';
function field(type,value){return {type,value};}
const examples=[
 ['input-template applies only allowed, blank fields',()=>{
   const r={A:field('SINGLE_LINE_TEXT',''),B:field('NUMBER','1'),C:field('CALC','')};
   m.applyPreset(r,{A:'new',B:'99',C:'wrong'});assert.equal(r.A.value,'new');assert.equal(r.B.value,'1');assert.equal(r.C.value,'');
 }],
 ['reuse-reset preserves normal create and clears only reuse',()=>{
   const r={A:field('SINGLE_LINE_TEXT','secret')};m.resetOnReuse(r,['A'],false);assert.equal(r.A.value,'secret');
   m.resetOnReuse(r,['A'],true);assert.equal(r.A.value,'');
 }],
 ['text-normalizer covers phone and Unicode',()=>{
   assert.equal(m.normalizeText('ＡＢＣ　','nfkc-trim'),'ABC');
   assert.equal(m.normalizeText('０３-１２３４－５６７８','phone'),'0312345678');
 }],
 ['field-help caps malicious-looking text without markup interpretation',()=>{
   assert.equal(m.helpContent('<script>'),'<script>');assert.equal(m.helpContent('x'.repeat(4000)).length,2000);
 }],
 ['save-navigation only allows own HTTPS app paths',()=>{
   assert.equal(m.postSaveDestination('stay','https://demo.example',123),null);
   assert.equal(m.postSaveDestination('index','https://demo.example',123),'https://demo.example/k/123/');
   assert.throws(()=>m.postSaveDestination('create','http://demo.example',123));
 }],
 ['mail-compose encodes and blocks header injection',()=>{
   assert.match(m.mailtoTemplate('test@example.com','hi?','a&b'),/subject=hi%3F&body=a%26b/);
   assert.throws(()=>m.mailtoTemplate('a@example.com\nbcc:x','', ''));
 }],
 ['list-aggregate is explicitly per current page',()=>{
   assert.deepEqual(m.aggregatePage([{n:field('NUMBER','10')},{n:field('NUMBER','20')}],'n'),
     {pageRecordCount:2,numericCount:2,sum:30,average:15,scope:'current_page'});
   assert.equal(m.aggregatePage([],'n').average,null);
 }],
 ['CSV protects formulas and quotes with BOM',()=>{
   const csv=m.exportCurrentPage([{n:field('SINGLE_LINE_TEXT','=1+2'),m:field('SINGLE_LINE_TEXT','a,"b"')}],['n','m']);
   assert.ok(csv.startsWith('\uFEFF'));assert.ok(csv.includes('"\'=1+2"'));
   assert.ok(csv.includes('"a,""b"""'));
 }],
 ['attachment-count counts only file field arrays',()=>{
   assert.equal(m.attachmentCount({f:field('FILE',[{fileKey:'abc'},{fileKey:'xyz'}])},'f'),2);
   assert.equal(m.attachmentCount({},'f'),0);
 }],
 ['table-row-tools copy must omit row ID',()=>{
   const row={id:'123',value:{A:field('SINGLE_LINE_TEXT','one')}};
   const copy=m.copySubtableRow(row);assert.equal(copy.id,undefined);
   copy.value.A.value='two';assert.equal(row.value.A.value,'one');
 }],
 ['qr-code validates payload not generating image at core stage',()=>{
   assert.equal(m.qrPayload('https://example.com'),'https://example.com');
   assert.throws(()=>m.qrPayload(''));
 }],
 ['record-toc only lists present fields',()=>{
   assert.deepEqual(m.tocEntries([{code:'A',label:'Name'},{code:'B'}],{A:field('SINGLE_LINE_TEXT','x')}),
      [{code:'A',label:'Name'}]);
 }],
 ['related-links restrict to own origin app paths',()=>{
   assert.match(m.safeRelatedLink('https://host.example','/k/10/','1&2'),/q=1%262/);
   assert.throws(()=>m.safeRelatedLink('https://host.example','https://evil.example','x'));
 }],
 ['sticky-list CSS scoped',()=>{
   assert.match(m.stickyStyle(),/recordlist-gaia/);
   assert.doesNotMatch(m.stickyStyle(false),/first-child/);
 }],
 ['file-preview rejects huge or unsupported files',()=>{
   const f={fileKey:'abcd_123',size:100,contentType:'application/pdf',name:'manual.pdf'};
   assert.equal(m.previewFileMeta(f).fileKey,'abcd_123');
   assert.throws(()=>m.previewFileMeta({...f,size:30*1024*1024}));
 }],
 ['lookup-suggest escapes quote/backslash',()=>{
   assert.match(m.lookupQuery('name','A"B'),/A\\"B/);
   assert.throws(()=>m.lookupQuery('name','x',101));
 }],
 ['postal-address requires opt-in and seven digits',()=>{
   assert.equal(m.normalizePostal('１２３-４５６７'),'1234567');
   assert.throws(()=>m.postalLookupAllowed('1234567',false));
 }],
 ['barcode-scan rejects controls and empty values',()=>{
   assert.equal(m.barcodeValue('  TEST-001  '),'TEST-001');
   assert.throws(()=>m.barcodeValue('\u0001abc'));
 }]];

for(const [name,fn] of examples)test(name,fn);
test('untrusted field name cannot mutate prototype',()=>{
 assert.throws(()=>m.applyPreset({A:field('SINGLE_LINE_TEXT','')},Object.fromEntries([['__proto__','bad']])));
 assert.throws(()=>m.fieldCode('constructor'));
});
test('numeric precision stops unbounded aggregate',()=>{
 assert.throws(()=>m.aggregatePage([{n:field('NUMBER',Number.MAX_SAFE_INTEGER)},{n:field('NUMBER','5')}],'n'));
});
test('CSV guards whitespace-prefixed spreadsheet formulas',()=>{
 assert.match(m.csvCell('  @sum(1,2)'),/^"'/);
});
test('reuse-reset preserves system read-only columns',()=>{
 const rec={CREATOR:field('CREATOR',{code:'user'})};
 m.resetOnReuse(rec,['CREATOR'],true);assert.deepEqual(rec.CREATOR.value,{code:'user'});
});
