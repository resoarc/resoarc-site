/* ResoArc CSV Import Diagnostics v0.1-beta browser layer. No network calls. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const engine=globalThis.ResoArcImportCheck;
const csv=$('import-csv'),form=$('import-form'),mode=$('import-delimiter');
const run=$('import-run'),status=$('import-status'),result=$('import-result');
const counts=$('import-counts'),summary=$('import-summary'),body=$('import-issues');
const MAX_FILE=8*1024*1024;
function ready(){
 const valid=[csv,form].every(x=>x.files.length && x.files[0].size<=MAX_FILE);
 run.disabled=!valid;
}
for(const el of [csv,form])el.addEventListener('change',()=>{ready();result.hidden=true;});
function append(row,tag,value){
 const cell=document.createElement(tag);
 cell.textContent=String(value??'');
 row.append(cell);
}
run.addEventListener('click',async()=>{
 result.hidden=true;run.disabled=true;status.textContent='ファイルをブラウザー内で検査中です…';
 try{
  const [csvFile,formFile]=[csv.files[0],form.files[0]];
  if(!csvFile||!formFile||csvFile.size>MAX_FILE||formFile.size>MAX_FILE)
   throw Error('CSV・JSONの両ファイルを選択してください。各8MiBまでです。');
  const [csvText,formText]=await Promise.all([csvFile.text(),formFile.text()]);
  const separator=mode.value==='tab'?'\t':mode.value==='comma'?',':csvFile.name.toLowerCase().endsWith('.tsv')?'\t':',';
  const parsed=engine.parseDelimited(csvText,separator);
  let config;
  try{config=JSON.parse(formText);}catch(_){throw Error('フォーム定義JSONの読み込みに失敗しました。');}
  const report=engine.analyze(parsed,config);
  counts.replaceChildren();
  for(const [label,v] of [['要修正',report.counts.errors],['要確認',report.counts.warnings],['検査行数',report.analyzedRows],['照合列数',report.matchedColumns]]){
   const d=document.createElement('div');d.className='result-stat';
   const strong=document.createElement('strong');strong.textContent=v.toLocaleString('ja-JP');
   const small=document.createElement('span');small.textContent=label;
   d.append(strong,small);counts.append(d);
  }
  summary.textContent=report.counts.errors===0 && report.counts.warnings===0
    ? '検出した問題はありません。ただし、取り込み成功を保証するものではありません。'
    : '取り込み前に、表示されたエラーと警告を確認してください。';
  body.replaceChildren();
  for(const issue of report.issues){
   const row=document.createElement('tr');
   append(row,'td',issue.severity==='error'?'要修正':'要確認');
   append(row,'td',issue.row||'全体');
   append(row,'td',issue.column||'全体');
   append(row,'td',issue.message);
   body.append(row);
  }
  if(!report.issues.length){
   const row=document.createElement('tr');const cell=document.createElement('td');
   cell.colSpan=4;cell.textContent='検査対象の問題は見つかりませんでした。';
   row.append(cell);body.append(row);
  }
  result.hidden=false;
  status.textContent='検査完了。ファイルは外部にアップロードしていません。'+(report.partial?' 先頭部分のみ検査しています。':'');
 }catch(e){
  status.textContent='検査できませんでした：'+(e.message||String(e));
 }finally{ready();}
});
ready();
})();
