/* ResoArc v1 candidate safety tests against real generated runtime. No live tenant. */
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('node:assert/strict'),test=require('node:test');
const root=path.resolve(__dirname,'..');
const runtime=fs.readFileSync(path.join(root,'plugins','input-template','js','desktop.js'),'utf8');
const marker=runtime.match(/const set=\(r,k,value\)=>\{[\s\S]*?\};\r?\nconst apply=/);
if(!marker)throw new Error('Cannot find generated setter in runtime');
const setter=marker[0].replace(/\r?\nconst apply=$/,'\nreturn set;');
const set=vm.runInNewContext('(()=>{'+setter+'})()');
const field=(type,value)=>({type,value});
test('normal string value and checkbox update accepted',()=>{
 const r={name:field('SINGLE_LINE_TEXT',''),choices:field('CHECK_BOX',[])};
 assert.equal(set(r,'name','新しい'),true);
 assert.equal(r.name.value,'新しい');
 assert.equal(set(r,'choices',['A','B']),true);
 assert.equal(r.choices.value.length,2);
});
test('prototype/constructor pollution is rejected',()=>{
 const r=Object.create({inherited:field('SINGLE_LINE_TEXT','x')});
 r.name=field('SINGLE_LINE_TEXT','ok');
 assert.equal(set(r,'__proto__',{polluted:true}),false);
 assert.equal(set(r,'constructor','bad'),false);
 assert.equal(set(r,'inherited','bad'),false);
 assert.equal({}.polluted,undefined);
});
test('malformed numbers blocked, valid finite decimal accepted',()=>{
 const r={n:field('NUMBER','100')};
 for(const x of ['1e999','NaN','Infinity','1,000','--10'])assert.equal(set(r,'n',x),false,x);
 assert.equal(r.n.value,'100');
 assert.equal(set(r,'n','-12.75'),true);
});
test('invalid calendar and clock entries rejected',()=>{
 const r={d:field('DATE','2026-01-01'),t:field('TIME','12:00'),dt:field('DATETIME','2026-01-01T12:00:00Z')};
 assert.equal(set(r,'d','2026-02-30'),false);
 assert.equal(set(r,'d','2026-02-28'),true);
 assert.equal(set(r,'t','25:90'),false);
 assert.equal(set(r,'t','23:59'),true);
 assert.equal(set(r,'dt','2026-10-17T25:00:00Z'),false);
});
test('rich-text HTML writes are blocked by default',()=>{
 const r={html:field('RICH_TEXT','safe')};
 assert.equal(set(r,'html','<img src=x onerror=alert(1)>'),false);
 assert.equal(r.html.value,'safe');
});
test('malformed structured values never mutate users/subtables',()=>{
 const r={users:field('USER_SELECT',[]),table:field('SUBTABLE',[])};
 assert.equal(set(r,'users',[{}]),false);
 assert.equal(set(r,'users',[{code:'user_01'}]),true);
 assert.equal(set(r,'table',[]),false);
 assert.equal(r.table.value.length,0);
});
test('generated runtime allowlists plugin setting keys',()=>{
 assert.match(runtime,/safeCfg=Object\.create\(null\)/);
 assert.doesNotMatch(runtime,/cfg=Object\.assign\(\{\},/);
});
test('related-link rejects off-origin URLs by default',()=>{
 const content=fs.readFileSync(path.join(root,'plugins','related-links','js','desktop.js'),'utf8');
 assert.match(content,/allowExternal/);
 assert.match(content,/target\.protocol!=='https:'/);
});
