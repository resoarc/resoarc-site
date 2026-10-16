/* ResoArc kintone CSV Import Diagnostics v0.1-beta / SPDX-License-Identifier: MIT
   Pure validation helpers: never access DOM, network or external storage.
*/
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object' && module.exports)module.exports=api;
 if(root)root.ResoArcImportCheck=api;
})(typeof globalThis==='object'?globalThis:this,function(){
 'use strict';
 const MAX_ROWS=20000, MAX_COLUMNS=250, MAX_ISSUES=500;
 function parseDelimited(text,delimiter=','){
  if(typeof text!=='string'||!['\t',','].includes(delimiter))throw Error('CSV/TSV形式を確認してください。');
  const data=text.charCodeAt(0)===0xfeff?text.slice(1):text;
  const rows=[];let row=[],field='',quoted=false,closed=false,rowIndex=1,limit=false;
  for(let i=0;i<data.length;i++){
   const ch=data[i],next=data[i+1];
   if(quoted){
    if(ch==='"'&&next==='"'){field+='"';i++;}
    else if(ch==='"'){quoted=false;closed=true;}
    else field+=ch;
   }else if(closed){
    if(ch===delimiter){row.push(field);field='';closed=false;}
    else if(ch==='\r'&&next==='\n'||ch==='\n'||ch==='\r'){
     if(ch==='\r'&&next==='\n')i++;
     row.push(field);rows.push(row);
     row=[];field='';closed=false;rowIndex++;
    } else if(ch===' '||ch==='\t'&&delimiter!==ch){throw Error('閉じた引用符の後に不要な文字があります（行 '+rowIndex+'）。');}
    else throw Error('閉じた引用符の後に不要な文字があります（行 '+rowIndex+'）。');
   }else if(ch===delimiter){row.push(field);field='';}
   else if(ch==='"'){
    if(field!=='')throw Error('引用符はセルの先頭だけで使用できます（行 '+rowIndex+'）。');
    quoted=true;
   }
   else if(ch==='\r'||ch==='\n'){
    if(ch==='\r'&&next==='\n')i++;
    row.push(field);rows.push(row);
    row=[];field='';rowIndex++;
   }else field+=ch;
   if(rows.length>MAX_ROWS){limit=true;break;}
  }
  if(quoted)throw Error('引用符が閉じていません（行 '+rowIndex+'）。');
  if(!limit && (field!==''||row.length!==0||closed)) {row.push(field);rows.push(row);}
  // A final newline terminates the preceding row, not an additional empty row.
  if(!rows.length)throw Error('CSV/TSVが空です。');
  if(rows[0].length>MAX_COLUMNS)throw Error('列数が上限を超えています（最大250列）。');
  return {rows,truncated:limit,delimiter};
 }
 function formProperties(form){
  if(!form || typeof form!=='object'||!form.properties||typeof form.properties!=='object'
     ||Array.isArray(form.properties))throw Error('kintoneのフォーム定義JSONではありません。propertiesが必要です。');
  const fields=[];
  for(const [code,value] of Object.entries(form.properties)){
   if(!value || typeof value!=='object')continue;
   const current={...value,code:value.code||code};
   if(value.type==='SUBTABLE'){
    // Table columns require separate, row-aware CSV import mapping. Never silently flatten them.
    fields.push({code:current.code,label:current.label||current.code,type:'SUBTABLE',required:false});
   }else fields.push(current);
  }
  if(!fields.length)throw Error('フィールド情報がありません。');
  return fields;
 }
 function actualDate(s){
  const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if(!m)return false;
  const y=+m[1],mm=+m[2],d=+m[3];
  if(y<1900||y>9999||mm<1||mm>12||d<1||d>31)return false;
  const t=new Date(Date.UTC(y,mm-1,d));
  return t.getUTCFullYear()===y && t.getUTCMonth()===mm-1 && t.getUTCDate()===d;
 }
 function checkValue(field,value){
  const v=String(value??'').trim();
  if(!v)return null;
  const type=field.type;
  if(type==='NUMBER'){
   if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(v))return '数値形式を確認してください';
  }else if(type==='DATE'){
   if(!actualDate(v))return '日付はYYYY-MM-DD形式の実在日付にしてください';
  }else if(type==='TIME'){
   const m=/^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(v);
   if(!m||+m[1]>23||+m[2]>59||(m[3]!==undefined&&+m[3]>59))return '時刻形式を確認してください';
  }else if(type==='DATETIME'){
   const m=/^(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?(?:Z|[+-]\d{2}:?\d{2})?$/.exec(v);
   if(!m||!actualDate(m[1])||+m[2]>23||+m[3]>59||(m[4]!==undefined&&+m[4]>59))return '日時形式を確認してください';
  }else if(['DROP_DOWN','RADIO_BUTTON'].includes(type)){
   const choices=Object.keys(field.options||{});
   if(choices.length && !choices.includes(v))return '設定された選択肢に存在しません';
  }else if(['SINGLE_LINE_TEXT','MULTI_LINE_TEXT'].includes(type)&&field.maxLength){
   const max=Number(field.maxLength);
   if(Number.isFinite(max)&&max>0&&[...v].length>max)return '最大文字数を超えています';
  }
  return null;
 }
 const CHECKED_TYPES=new Set(['SINGLE_LINE_TEXT','MULTI_LINE_TEXT','NUMBER','DATE','TIME','DATETIME','DROP_DOWN','RADIO_BUTTON']);
 function analyze(parsed,form,opts={}){
  const fields=formProperties(form),headers=parsed.rows[0].map(x=>String(x||'').trim());
  if(!headers.length || !headers.some(Boolean))throw Error('CSVヘッダーがありません。');
  const issues=[],matched=[],byCode=new Map(),byLabel=new Map(),notices=new Set(),seen=new Set();
  let errorCount=0,warningCount=0,analyzed=0;
  const add=(severity,row,column,message)=>{
   if(severity==='error')errorCount++;else warningCount++;
   if(issues.length<MAX_ISSUES)issues.push({severity,row,column,message});
  };
  for(const field of fields){
   byCode.set(field.code,field);
   const label=String(field.label||'');
   if(label){const prev=byLabel.get(label)||[];prev.push(field);byLabel.set(label,prev);}
  }
  headers.forEach((header,index)=>{
   if(!header){add('warning',1,index+1,'ヘッダーが空欄です');matched.push(null);return;}
   if(seen.has(header))add('error',1,index+1,'ヘッダーが重複しています');
   seen.add(header);
   const exact=byCode.get(header);
   const byName=byLabel.get(header)||[];
   if(!exact && byName.length>1){add('warning',1,index+1,'同じ表示名のフィールドが複数あります。フィールドコードで指定してください');matched.push(null);return;}
   const field=exact||(byName.length===1?byName[0]:null);
   matched.push(field);
   if(!field)add('warning',1,index+1,'対応するフィールドがありません');
   else if(field.type==='SUBTABLE')add('warning',1,index+1,'テーブルの行単位の形式には対応していません');
   else if(!CHECKED_TYPES.has(field.type))notices.add(field.code);
  });
  const codes=new Set(matched.filter(Boolean).map(f=>f.code));
  for(const field of fields){
   if(field.required===true && !codes.has(field.code) && field.type!=='SUBTABLE')
    add('warning',1,0,'必須フィールド「'+(field.label||field.code)+'」に対応する列がありません。初期値の有無も確認してください');
  }
  const rows=parsed.rows.slice(1),limit=Math.min(rows.length,MAX_ROWS);
  for(let r=0;r<limit;r++){
   const cols=rows[r];
   if(cols.length===1 && !cols[0])continue;
   analyzed++;
   const rowNo=r+2;
   if(cols.length!==headers.length)add('error',rowNo,0,'列数がヘッダーと一致しません（'+cols.length+'/'+headers.length+'）');
   for(let c=0;c<Math.min(cols.length,headers.length);c++){
    const field=matched[c];
    if(!field || !CHECKED_TYPES.has(field.type))continue;
    const value=String(cols[c]??'');
    if(field.required===true && !value.trim())add('error',rowNo,c+1,'必須項目が空欄です');
    const failure=checkValue(field,value);
    if(failure)add('error',rowNo,c+1,failure+'：'+(field.label||field.code));
   }
  }
  if(parsed.truncated)add('warning',0,0,'CSVが処理上限を超えたため、先頭部分のみ検査しました');
  for(const code of notices)add('warning',0,0,'フィールド '+code+' のデータ形式は自動検査の対象外です');
  return {issues,counts:{errors:errorCount,warnings:warningCount},columns:headers.length,analyzedRows:analyzed,
   totalDataRows:rows.length,matchedColumns:matched.filter(Boolean).length,partial:parsed.truncated||rows.length>MAX_ROWS,
   reportVersion:'0.1.0-beta'};
 }
 return {parseDelimited,formProperties,actualDate,checkValue,analyze,MAX_ROWS,MAX_COLUMNS,MAX_ISSUES};
});
