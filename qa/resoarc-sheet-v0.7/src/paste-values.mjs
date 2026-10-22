// TSV copied from spreadsheets: preserve quoted tabs/newlines and cell types safely.
export function parseTsv(text,{maxCells=1000,maxChars=100000}={}){
 if(typeof text!=='string'||!text.trim())throw Error('貼り付けるデータを入力してください。');
 if(text.length>maxChars)throw Error('貼り付け可能な文字数を超えています。');
 const rows=[];let row=[],value='',quoted=false,afterQuote=false;
 for(let i=0;i<text.length;i++){
  const ch=text[i];
  if(quoted){
   if(ch==='"'&&text[i+1]==='"'){value+='"';i++;continue;}
   if(ch==='"'){quoted=false;afterQuote=true;continue;}
   value+=ch;continue;
  }
  if(afterQuote){if(ch==='\t'||ch==='\r'||ch==='\n'){afterQuote=false;}else if(ch===' '){continue;}else throw Error('引用符の閉じ方が不正です。');}
  if(ch==='"'&&value===''){quoted=true;continue;}
  if(ch==='\t'){row.push(value);value='';continue;}
  if(ch==='\r'||ch==='\n'){
   row.push(value);rows.push(row);row=[];value='';
   if(ch==='\r'&&text[i+1]==='\n')i++;
   if(rows.length>maxCells)throw Error('貼り付け可能なセル数を超えています。');
   continue;
  }
  value+=ch;
 }
 if(quoted)throw Error('閉じていない引用符があります。');
 if(value!==''||row.length) {row.push(value);rows.push(row);}
 if(!rows.length)throw Error('貼り付けるデータを入力してください。');
 const width=Math.max(...rows.map(r=>r.length));
 if(width*rows.length>maxCells)throw Error('貼り付け可能なセル数を超えています。');
 return rows.map(r=>[...r,...Array(width-r.length).fill('')]);
}
export function asPasteValue(value){
 const v=String(value??'');
 if(v.startsWith('='))throw Error('数式で始まるセルは「値のみ貼り付け」対象外です。通常の貼り付けを利用してください。');
 if(v==='' )return '';
 if(/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?$/i.test(v) && !/^0\d/.test(v) && !/^[+-]0\d/.test(v)){
  const n=Number(v);if(Number.isFinite(n)&&Number.isSafeInteger(n)||Number.isFinite(n)&&!Number.isInteger(n))return n;
 }
 return v;
}
export function validatePaste(text,opts){
 const data=parseTsv(text,opts).map(r=>r.map(asPasteValue));
 return {data,rows:data.length,columns:data[0].length,cellCount:data.length*data[0].length};
}
