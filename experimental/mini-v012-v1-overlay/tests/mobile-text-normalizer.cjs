const assert=require('node:assert/strict'),test=require('node:test'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'plugins/text-normalizer/manifest.json'),'utf8'));
const mobile=fs.readFileSync(path.join(root,'plugins/text-normalizer/js/mobile.js'),'utf8');
function context(settings={fields:'Title',mode:'NFKC_TRIM'},source=mobile){
  const handlers=Object.create(null);
  const kintone={
    $PLUGIN_ID:'test',
    plugin:{app:{getConfig:()=>({ra_settings:JSON.stringify(settings)})}},
    events:{on:(events,fn)=>{for(const e of Array.isArray(events)?events:[events])handlers[e]=fn}}
  };
  vm.runInNewContext(source,{kintone,console,URL,Date,setTimeout,clearTimeout});
  return handlers;
}
test('mobile manifest and source bundle are supplied',()=>{
 assert.deepEqual(manifest.mobile?.js,['js/mobile.js']);
 assert.ok(mobile.includes('mobile.app.record.create.submit'));
});
test('mobile create submit normalizes configured text and preserves other fields',()=>{
 const handlers=context();
 const event={record:{Title:{type:'SINGLE_LINE_TEXT',value:'ＡＢＣ　'},Amount:{type:'NUMBER',value:'42'}}};
 const result=handlers['mobile.app.record.create.submit'](event);
 assert.equal(result.record.Title.value,'ABC');
 assert.equal(result.record.Amount.value,'42');
});
test('mobile edit submit does not mutate unsupported field types',()=>{
 const handlers=context({fields:'Title,Amount',mode:'NFKC_TRIM'});
 const event={record:{Title:{type:'MULTI_LINE_TEXT',value:'１２３　'},Amount:{type:'NUMBER',value:'４２'}}};
 const result=handlers['mobile.app.record.edit.submit'](event);
 assert.equal(result.record.Title.value,'123');
 assert.equal(result.record.Amount.value,'４２');
});
test('desktop handlers remain present',()=>{
 const desktop=fs.readFileSync(path.join(root,'plugins/text-normalizer/js/desktop.js'),'utf8');
 const handlers=context({fields:'Title',mode:'NFKC_TRIM'},desktop);
 assert.equal(typeof handlers['app.record.create.submit'],'function');
 assert.equal(typeof handlers['app.record.edit.submit'],'function');
});
