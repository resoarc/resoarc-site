import JSZip from 'jszip';

const FEATURES = [
  ['charts','グラフ','high',p => /^xl\/charts\/chart\d+\.xml$/i.test(p)],
  ['images','画像ファイル','high',p => /^xl\/media\//i.test(p)],
  ['drawings','図形・描画','high',p => /^xl\/drawings\/drawing\d+\.xml$/i.test(p)],
  ['pivots','ピボットテーブル','high',p => /^xl\/pivotTables\/pivotTable\d+\.xml$/i.test(p)],
  ['tables','Excelテーブル','high',p => /^xl\/tables\/table\d+\.xml$/i.test(p)],
  ['chartsheets','グラフシート','high',p => /^xl\/chartsheets\/sheet\d+\.xml$/i.test(p)],
  ['printer','プリンター設定','medium',p => /^xl\/printerSettings\//i.test(p)],
  ['queryConnections','クエリ・接続','high',p => /^xl\/connections\.xml$/i.test(p)||/^xl\/queryTables\//i.test(p)],
  ['external','外部リンク','high',p => /^xl\/externalLinks\/externalLink\d+\.xml$/i.test(p)],
  ['embedded','埋め込みオブジェクト','high',p => /^xl\/embeddings\//i.test(p)],
  ['slicers','スライサー','high',p => /^xl\/slicers\//i.test(p)],
  ['macros','VBA','high',p => /vbaProject\.bin$/i.test(p)],
  ['comments','コメント','medium',p => /^xl\/(?:comments|threadedComments)\//i.test(p)||/^xl\/comments\d+\.xml$/i.test(p)],
];
const XML_FEATURES = [
  ['conditional','条件付き書式','high','conditionalFormatting','worksheet'],
  ['formulas','セルの数式','medium','f','worksheet'],
  ['autoFilters','オートフィルター','medium','autoFilter','worksheet'],
  ['sheetTables','テーブル参照','high','tablePart','worksheet'],
  ['pageBreaks','手動改ページ','medium','brk','worksheet'],
  ['headers','ヘッダー・フッター','medium','headerFooter','worksheet'],
  ['validation','データの入力規則','high','dataValidation','worksheet'],
  ['protected','シート保護','high','sheetProtection','worksheet'],
  ['hyperlinks','ハイパーリンク','medium','hyperlink','worksheet'],
  ['merged','セルの結合','medium','mergeCell','worksheet'],
  ['freeze','ウィンドウ枠の固定','medium','pane','worksheet'],
  ['print','印刷ページ設定','medium','pageSetup','worksheet'],
  ['definedNames','定義済みの名前','high','definedName','workbook'],
];
const MAX_FILES=5000, MAX_XML=5*1024*1024, MAX_TOTAL=150*1024*1024;
const xmlCount=(str,local)=>((str.match(new RegExp('<(?:[A-Za-z_][\\w.-]*:)?'+local+'(?=[\\s/>])','g')))||[]).length;
async function secureZip(blob){
 const zip=await JSZip.loadAsync(typeof blob.arrayBuffer==='function'?await blob.arrayBuffer():blob);
 const files=Object.values(zip.files).filter(f=>!f.dir);
 if(files.length>MAX_FILES)throw Error('Excel内部のファイル数が多すぎます。');
 const size=files.reduce((a,f)=>a+(f._data?.uncompressedSize||0),0);
 if(size>MAX_TOTAL)throw Error('Excel内部の展開後サイズが制限を超えます。');
 return {zip,files};
}
function compareSets(original,after){
 const current=new Map(after.features.map(x=>[x.id,x]));
 return original.features
  .filter(x=>x.count>(current.get(x.id)?.count||0))
  .map(x=>({...x,remaining:current.get(x.id)?.count||0,missing:x.count-(current.get(x.id)?.count||0)}));
}
export async function inspectXlsx(blob){
 if(!blob||!blob.name?.toLowerCase().endsWith('.xlsx')) {
  // Blob from export has no name; caller supplies filename explicitly.
  if(!blob||blob.name) return {features:[],totalParts:0};
 }
 const {zip,files}=await secureZip(blob);
 const paths=files.map(f=>f.name);
 if(!paths.includes('xl/workbook.xml'))throw Error('Excelとして読み取れないファイルです。');
 const counters=new Map();
 for(const [id,, ,match] of FEATURES) counters.set(id,paths.filter(match).length);
 const xmlSources=[
  ...paths.filter(p=>/^xl\/worksheets\/sheet\d+\.xml$/i.test(p)).map(p=>[p,'worksheet']),
  ['xl/workbook.xml','workbook']
 ];
 for(const [path,partType] of xmlSources) {
  const f=zip.file(path);
  if(!f)continue;
  if((f._data?.uncompressedSize||0)>MAX_XML)throw Error('内部XMLが大きすぎるため安全に検査できません。');
  const body=await f.async('string');
  for(const [id,,,element,target] of XML_FEATURES)if(target===partType)
   counters.set(id,(counters.get(id)||0)+xmlCount(body,element));
 }
 const defs=[
  ...FEATURES.map(([id,label,severity])=>({id,label,severity})),
  ...XML_FEATURES.map(([id,label,severity])=>({id,label,severity})),
 ];
 return {features:defs.map(v=>({...v,count:counters.get(v.id)||0})).filter(x=>x.count>0),totalParts:paths.length};
}
export async function auditExcelSave(originalFile,outputBlob){
 const original=await inspectXlsx(originalFile);
 const output=await inspectXlsx(outputBlob);
 const losses=compareSets(original,output);
 return {original,output,losses,hasRisks:original.features.some(x=>x.severity==='high')};
}
export function formatAuditMessage(audit){
 const lines=audit.losses.map(x=>'・'+x.label+' : '+x.count+' → '+x.remaining);
 if(!lines.length&&audit.hasRisks)lines.push('・特殊なExcel機能が含まれており、内部内容の完全保持は検証できません。');
 return lines.join('\n');
}