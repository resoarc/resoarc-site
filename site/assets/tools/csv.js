/*!
 * ResoArc CSV Structure Inspector v1.0.0
 * Copyright (c) 2026 ResoArc Open Technology Project
 * MIT License (see /licenses/RESOARC-MIT.txt)
 * Local-only parser: no fetch / XHR, no uploads or server processing.
 */
(()=>{
"use strict";
const $=id=>document.getElementById(id),maxBytes=10*1024*1024;
const file=$("csv-file"),delim=$("csv-delimiter"),encoding=$("csv-encoding"),run=$("csv-run"),reset=$("csv-reset"),output=$("csv-output"),status=$("csv-status"),summary=$("csv-summary"),findings=$("csv-findings"),table=$("csv-sample");
let selected=null;
function statusText(s,kind=""){status.textContent=s;status.dataset.status=kind;}
function fresh(){output.hidden=true;summary.replaceChildren();findings.replaceChildren();table.replaceChildren();}
function escapeHeader(h){return h.trim().toLocaleLowerCase();}
function detectDelimiter(text){
  let counts=[0,0,0],quote=false;
  const first=text.slice(0,Math.min(text.length,15000));
  for(let i=0;i<first.length;i++){
    const c=first[i];
    if(c==='"'){if(quote && first[i+1]==='"'){i++;continue;}quote=!quote;continue;}
    if(!quote){if(c==='\r'||c==='\n')break; const n=[',','\t',';'].indexOf(c);if(n>=0)counts[n]++;}
  }
  let max=Math.max(...counts);
  return max>0?[',','\t',';'][counts.indexOf(max)]:',';
}
function parseCSV(src,separator){
  const rows=[],problems=[];
  let row=[],field="",quote=false,closed=false,started=false,line=1,rowLine=1,content=false,afterSeparator=false;
  function problem(detail){if(problems.length<30)problems.push({line,detail});}
  function finishCell(){row.push(field);field="";closed=false;started=false;afterSeparator=false;}
  function finishRow(){
    finishCell();
    if(row.length===1&&row[0]===""&&!content){row=[];rowLine=line;return;}
    rows.push({line:rowLine,cells:row});row=[];content=false;rowLine=line;
  }
  src=src.replace(/^\uFEFF/,"");
  for(let i=0;i<src.length;i++){
    const c=src[i];
    if(quote){
      if(c==='"'){if(src[i+1]==='"'){field+='"';i++;}else{quote=false;closed=true;}}
      else if(c==='\r'||c==='\n'){field+='\n';if(c==='\r'&&src[i+1]==='\n')i++;line++;}
      else field+=c;
      continue;
    }
    if(c==='"'){
      if(field===""&&!started&&!closed){quote=true;started=true;content=true;}
      else {problem("引用符（\"）の位置が不正です。");field+=c;content=true;}
    }else if(c===separator){
      // Delimiter ends the current field.
      finishCell();content=true;afterSeparator=true;
    }else if(c==='\r'||c==='\n'){
      if(c==='\r'&&src[i+1]==='\n')i++;
      finishRow();line++;rowLine=line;
    }else{
      if(closed && c!==" " && c!=="\t")problem("閉じ引用符の後に区切り以外の文字があります。");
      field+=c;started=true;content=true;
    }
  }
  if(quote)problem("引用符が閉じられていません。");
  if(field!==""||row.length>0||content||closed)finishRow();
  return {rows,problems};
}
function append(parent,tag,text,cls){
 const n=document.createElement(tag);if(cls)n.className=cls;n.textContent=text;parent.appendChild(n);return n;
}
function choose(f){
  selected=f||null;fresh();
  $("csv-drop-name").textContent=selected?selected.name:"CSV / TSVファイルを選択する";
  run.disabled=!selected||selected.size>maxBytes;
  if(!selected)statusText("ファイルは外部へ送信されません。");
  else if(selected.size>maxBytes)statusText("10 MiBを超えるファイルには対応していません。","error");
  else statusText(selected.size.toLocaleString("ja-JP")+" バイトのファイルを選択しました。");
}
function makeTable(rows){
 const fragment=document.createDocumentFragment();
 for(let i=0;i<Math.min(rows.length,5);i++){
   const tr=document.createElement("tr");
   for(const v of rows[i].cells.slice(0,12))append(tr,i===0?"th":"td",v);
   fragment.appendChild(tr);
 }
 table.appendChild(fragment);
}
async function inspect(){
 if(!selected)return;
 run.disabled=true;fresh();statusText("解析中…");
 try{
  if(selected.size>maxBytes)throw Error("ファイルサイズが上限を超えています。");
  const buf=await selected.arrayBuffer();
  const decoder=new TextDecoder(encoding.value,{fatal:true});
  const content=decoder.decode(buf);
  const sep=delim.value==="auto"?detectDelimiter(content):delim.value;
  const result=parseCSV(content,sep);
  if(!result.rows.length)throw Error("表として読み込める行がありません。");
  const width=result.rows[0].cells.length;
  const messages=[];
  function finding(level,message){messages.push({level,message});}
  const sepName=sep==="\t"?"タブ":sep===","?"カンマ":"セミコロン";
  if(width===1)finding("warning","列数が1列です。区切り文字の設定を確認してください。");
  for(let i=0;i<result.problems.length;i++){const x=result.problems[i];finding("error",x.line+"行目："+x.detail);}
  const headers=result.rows[0].cells;
  const seen=new Map();
  headers.forEach((h,index)=>{
    const key=escapeHeader(h);
    if(!key)finding("warning","ヘッダー"+(index+1)+"列目が空欄です。");
    if(key&&seen.has(key))finding("warning","重複ヘッダー："+h+"（"+(seen.get(key)+1)+"列目と"+(index+1)+"列目）");
    seen.set(key,index);
  });
  let inconsistent=0,formula=0;
  for(let i=1;i<result.rows.length;i++){
    const r=result.rows[i];
    if(r.cells.length!==width){
       inconsistent++;
       if(inconsistent<=20)finding("error",r.line+"行目：列数"+r.cells.length+"（見出し行は"+width+"列）");
    }
    for(let c=0;c<r.cells.length;c++)if(/^[\t ]*[=+\-@]/.test(r.cells[c])){
      formula++;
      if(formula<=5)finding("warning",r.line+"行"+(c+1)+"列目：表計算ソフトで数式として解釈される可能性があります。");
    }
  }
  if(inconsistent>20)finding("error","列数不一致はほかにも"+(inconsistent-20)+"行あります。");
  if(formula>5)finding("warning","数式として扱われる可能性があるセルは合計"+formula+"件です。");
  const eCount=messages.filter(x=>x.level==="error").length;
  const wCount=messages.filter(x=>x.level==="warning").length;
  const cells=[["文字コード",encoding.value==="utf-8"?"UTF-8":"Shift_JIS"],["区切り文字",sepName],["データ行数",String(Math.max(0,result.rows.length-1))],["見出し列数",String(width)],["列数不一致行",String(inconsistent)],["指摘",eCount+"件のエラー / "+wCount+"件の注意"]];
  for(const [name,val] of cells){const item=append(summary,"div","", "metric");append(item,"span",name);append(item,"strong",val);}
  if(!messages.length)append(findings,"li","このファイルで確認した構造上の問題は見つかりませんでした。", "issue ok");
  else for(const msg of messages.slice(0,40))append(findings,"li",msg.message,"issue "+msg.level);
  makeTable(result.rows);
  output.hidden=false;
  statusText("解析完了。ブラウザー内だけで処理しました。","success");
 }catch(e){statusText("解析できませんでした："+(e?.message||String(e)),"error");}
 finally{run.disabled=!selected||selected.size>maxBytes;}
}
file.addEventListener("change",()=>choose(file.files?.[0]));
$("csv-drop").addEventListener("dragover",e=>{e.preventDefault();e.currentTarget.classList.add("drag");});
$("csv-drop").addEventListener("dragleave",e=>e.currentTarget.classList.remove("drag"));
$("csv-drop").addEventListener("drop",e=>{e.preventDefault();e.currentTarget.classList.remove("drag");if(e.dataTransfer?.files?.length)choose(e.dataTransfer.files[0]);});
$("csv-drop").addEventListener("keydown",e=>{if(e.target===e.currentTarget&&(e.key==="Enter"||e.key===" ")){e.preventDefault();file.click();}});
run.addEventListener("click",inspect);
reset.addEventListener("click",()=>{file.value="";choose(null);});
choose(null);
})();