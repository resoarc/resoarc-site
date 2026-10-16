const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const candidate=path.resolve(__dirname,'../site/assets/tools/import-diagnose-core.js');
const source=fs.existsSync(candidate)?candidate:path.resolve(__dirname,'../dist/assets/tools/import-diagnose-core.js');
const core=require(source);
const schema={properties:{
 name:{code:'name',label:'氏名',type:'SINGLE_LINE_TEXT',required:true,maxLength:'5'},
 amount:{code:'amount',label:'金額',type:'NUMBER',required:true},
 day:{code:'day',label:'日付',type:'DATE'},
 status:{code:'status',label:'状態',type:'DROP_DOWN',options:{OK:{label:'OK'},NG:{label:'NG'}}},
 memo:{code:'memo',label:'メモ',type:'MULTI_LINE_TEXT'},
 Table:{code:'Table',label:'行一覧',type:'SUBTABLE'}
}};
test('CSV quoted commas and CRLF/newlines',()=>{
 const p=core.parseDelimited('name,amount\r\n"A,B",12\r\n"line\ninside",15\r\n');
 assert.equal(p.rows.length,3);
 assert.deepEqual(p.rows[1],['A,B','12']);
 assert.deepEqual(p.rows[2],['line\ninside','15']);
});
test('CSV escaped quotes, BOM, TSV',()=>{
 const p=core.parseDelimited('\uFEFFname\tamount\n"a""b"\t10\n','\t');
 assert.deepEqual(p.rows,[['name','amount'],['a"b','10']]);
});
test('malformed CSV is rejected with clear error',()=>{
 assert.throws(()=>core.parseDelimited('a\n"unterminated'),/閉じて/);
 assert.throws(()=>core.parseDelimited('a\n"ok"xxx'),/不要な文字/);
 assert.throws(()=>core.parseDelimited('a\nx"bad"'),/引用符/);
});
test('fields from kintone properties and type validation',()=>{
 assert.equal(core.formProperties(schema).length,6);
 assert.equal(core.checkValue(schema.properties.day,'2026-02-30')!==null,true);
 assert.equal(core.checkValue(schema.properties.day,'2026-02-28'),null);
 assert.equal(core.checkValue(schema.properties.amount,'12a')!==null,true);
 assert.equal(core.checkValue(schema.properties.amount,'-12.5'),null);
 assert.equal(core.checkValue(schema.properties.status,'INVALID')!==null,true);
 assert.equal(core.checkValue(schema.properties.status,'OK'),null);
 assert.equal(core.checkValue(schema.properties.name,'123456')!==null,true);
});
test('reports required missing value, bad date, number, choice',()=>{
 const csv=core.parseDelimited('name,amount,day,status\n,ABC,2026-02-30,NONE\n');
 const result=core.analyze(csv,schema);
 assert.equal(result.analyzedRows,1);
 assert.equal(result.counts.errors,4);
 assert.ok(result.issues.some(x=>/必須項目/.test(x.message)));
});
test('matches label as well as code',()=>{
 const csv=core.parseDelimited('氏名,金額\nサンプル,10\n');
 const result=core.analyze(csv,schema);
 assert.equal(result.matchedColumns,2);
 assert.equal(result.counts.errors,0);
});
test('duplicate header and unknown field warnings',()=>{
 const csv=core.parseDelimited('name,name,unknown\nA,B,10');
 const result=core.analyze(csv,schema);
 assert.ok(result.issues.some(x=>/重複/.test(x.message)));
 assert.ok(result.issues.some(x=>/対応するフィールド/.test(x.message)));
});
test('nonuniform column counts cause error',()=>{
 const report=core.analyze(core.parseDelimited('name,amount\nA,1,extra\nB'),schema);
 assert.equal(report.counts.errors,2);
});
test('unsupported table type must be explicitly surfaced',()=>{
 const report=core.analyze(core.parseDelimited('Table,name,amount\nX,A,1'),schema);
 assert.ok(report.issues.some(x=>/テーブル/.test(x.message)));
});
test('does not treat unsafe values as HTML or execute them',()=>{
 const csv=core.parseDelimited('name,amount\n"<img src=x onerror=alert(1)>",1');
 const report=core.analyze(csv,schema);
 assert.ok(report.issues.every(x=>typeof x.message==='string'));
});
test('rejects invalid schema',()=>{
 assert.throws(()=>core.analyze(core.parseDelimited('name\nA'),{}),/properties/);
});
