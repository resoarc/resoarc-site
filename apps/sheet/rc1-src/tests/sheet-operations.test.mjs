import test from 'node:test';
import assert from 'node:assert/strict';
import {displayValue,findCells,literalReplace,isPlainSortable,sortedSheet,rowsNotMatching,formatTsv,usedRows,isSheetProtected,assertSheetEditable} from '../src/sheet-operations.mjs';

const cell=v=>({v:{v,m:String(v)}});
const sheet=(rows)=>({id:'test',name:'Sheet1',row:100,column:26,data:rows.map(row=>row.map(cell)),config:{}});
test('findCells matches Japanese and numeric displays but excludes blank cells',()=>{
 const s=sheet([['名前','番号'],['東京','007'],['大阪',3]]);
 assert.deepEqual(findCells(s,'東京').map(h=>[h.r,h.c]),[[1,0]]);
 assert.equal(findCells(s,'7').length,1);
 assert.equal(findCells(s,'空').length,0);
 assert.deepEqual(findCells(s,'').length,0);
});
test('replace only plain string values and never formulas or numeric values',()=>{
 assert.equal(literalReplace(cell('東京東京'),'東京','大阪'),'大阪大阪');
 assert.equal(literalReplace(cell(700),'7','8'),null);
 assert.equal(literalReplace({...cell('東京'),f:'SUM(A1:A2)'},'東京','大阪'),null);
 assert.equal(literalReplace(cell('Case'),'case','next'),'next');
});
test('stable sort moves entire styled rows, retains the first header row',()=>{
 const s=sheet([['name','qty'],['C',3],['A',1],['B',2]]);
 s.data[1][0].bg='#ff0000';
 const next=sortedSheet(s,1,'asc');
 assert.deepEqual(next.data.map(row=>row[0].v.v),['name','A','B','C']);
 assert.equal(next.data[3][0].bg,'#ff0000');
 assert.deepEqual(s.data.map(row=>row[0].v.v),['name','C','A','B']);
 assert.deepEqual(sortedSheet(s,1,'desc').data.map(row=>row[0].v.v),['name','C','B','A']);
});
test('sort refuses formulas, merges, existing filters or hidden rows',()=>{
 const s=sheet([['h'],['a'],['b']]);
 s.data[1][0].f='A1';
 assert.equal(isPlainSortable(s),false);
 assert.throws(()=>sortedSheet(s,0),/数式/);
 delete s.data[1][0].f;
 s.config.merge={'1_0':{r:1,c:0,rs:1,cs:2}};
 assert.throws(()=>sortedSheet(s,0),/結合/);
 delete s.config.merge;
 s.config.rowhidden={'2':1};
 assert.throws(()=>sortedSheet(s,0),/安全/);
});
test('filter only hides nonmatches after the header',()=>{
 const s=sheet([['name'],['東京'],['大阪'],['京都']]);
 assert.deepEqual(rowsNotMatching(s,0,'京'),['2']);
 assert.throws(()=>rowsNotMatching(s,0,''),/入力/);
 assert.equal(usedRows(s),4);
});
test('TSV copy quotes tabs, newlines and quotation marks',()=>{
 assert.equal(formatTsv([['a\tb','a"b'],['x\ny','0']]),'"a\tb"\t"a""b"\r\n"x\ny"\t0');
});

test('plain imported CSV can sort despite empty FortuneSheet validation defaults',()=>{
 const s=sheet([['name'],['Z'],['A']]);
 s.dataVerification={};s.hyperlink={};s.filter=[];s.filter_select={};s.conditionformat=[];
 assert.equal(isPlainSortable(s),true);
 assert.deepEqual(sortedSheet(s,0).data.map(r=>r?.[0]?.v?.v),['name','A','Z']);
 s.dataVerification={'0_1':{type:'dropdown'}};
 assert.equal(isPlainSortable(s),false);
 delete s.dataVerification;
 s.hyperlink={'1_0':{linkAddress:'https://example.invalid'}};
 assert.equal(isPlainSortable(s),false);
 delete s.hyperlink;
 s.config.rowlen={'1':30};
 assert.equal(isPlainSortable(s),false);
});

test('protected sheets cannot be edited or sorted, including actual FortuneSheet metadata',()=>{
 const s=sheet([['h'],['B'],['A']]);
 assert.equal(isSheetProtected(s),false);
 s.config.protect=true;
 assert.equal(isSheetProtected(s),true);
 assert.throws(()=>assertSheetEditable(s),/保護されたシート/);
 assert.equal(isPlainSortable(s),false);
 assert.throws(()=>sortedSheet(s,0),/安全に移動/);
 delete s.config.protect;
 s.config.protect={isProtect:true};
 assert.equal(isSheetProtected(s),true);
 delete s.config.protect;
 assert.equal(isPlainSortable(s),true);
 assert.doesNotThrow(()=>assertSheetEditable(s));
});
