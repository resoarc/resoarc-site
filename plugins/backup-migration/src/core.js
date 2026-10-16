// ResoArc Backup v2. Portable data model; supports reading legacy v1 ZIPs.
import {zipSync, unzipSync, strToU8, strFromU8} from 'fflate';

export const FORMAT = 'resoarc.kintone.backup';
export const VERSION = 2;
export const MAX_BYTES = 25 * 1024 * 1024;
export const MAX_RECORDS = 20000;
const WRITABLE = new Set(['SINGLE_LINE_TEXT','MULTI_LINE_TEXT','RICH_TEXT','NUMBER','RADIO_BUTTON','DROP_DOWN','CHECK_BOX','MULTI_SELECT','DATE','TIME','DATETIME','LINK','USER_SELECT','ORGANIZATION_SELECT','GROUP_SELECT','FILE']);
const s = v => JSON.stringify(v);
const u8 = v => v instanceof Uint8Array ? v : new Uint8Array(v);
const stop = reason => { throw new Error(reason); };
export const sha256 = async b => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', u8(b)))).map(v=>v.toString(16).padStart(2,'0')).join('');
export const allowedField = d => !!d && WRITABLE.has(d.type) && !d.lookup && !d.referenceTable && !(d.type==='SINGLE_LINE_TEXT' && typeof d.expression==='string' && d.expression.trim());
const obj = v => v && typeof v === 'object' && !Array.isArray(v);
function fieldContents(props) {
  const fields = {};
  for (const [code, def] of Object.entries(props || {})) {
    if (def?.type === 'SUBTABLE') {
      const members = fieldContents(def.fields);
      if (Object.keys(members).length) fields[code] = {type:'SUBTABLE', fields:members};
    } else if (allowedField(def)) fields[code] = {type:def.type};
  }
  return fields;
}
export const writableSchema = raw => fieldContents(raw?.properties || raw);
function filterValue(value, def) {
  if (def.type === 'SUBTABLE') {
    if (!Array.isArray(value)) return [];
    return value.map(row => {
      const result = {};
      for (const [code, fd] of Object.entries(def.fields)) {
        if (row?.value?.[code]) result[code] = {value:filterValue(row.value[code].value,fd)};
      }
      return {value:result};
    });
  }
  if (def.type === 'FILE') {
    return (Array.isArray(value) ? value : []).map(f=>({fileKey:String(f.fileKey||''),name:String(f.name||''),size:Number(f.size||0),contentType:String(f.contentType||'application/octet-stream')}));
  }
  if (['USER_SELECT','GROUP_SELECT','ORGANIZATION_SELECT'].includes(def.type)) {
    return (Array.isArray(value) ? value : []).map(x => ({code:String(x.code)}));
  }
  if (Array.isArray(value)) return value.map(v=>obj(v) ? structuredClone(v) : v);
  return value === undefined ? null : value;
}
export function normalizeRecord(record, schema) {
  if (!obj(record) || !obj(schema)) stop('不正なレコード形式です');
  const result = {};
  for (const [code, def] of Object.entries(schema)) {
    if (record[code]) result[code] = {value:filterValue(record[code].value,def)};
  }
  return result;
}
function visitFiles(rec, schema, visit) {
  for (const [code, def] of Object.entries(schema)) {
    const val=rec[code]?.value;
    if (def.type === 'FILE' && Array.isArray(val)) {
      for (const f of val) visit(f);
    } else if (def.type === 'SUBTABLE' && Array.isArray(val)) {
      for (const row of val) visitFiles(row.value, def.fields, visit);
    }
  }
}
const checkPath = name => { if (!/^(manifest\.json|schema\/(fields|layout|source-fields)\.json|data\/records\.jsonl|attachments\/[0-9a-f]{64})$/.test(name)) stop('ZIP内の不正なパス: '+name); };
function sizeCheck(bytes, limit=MAX_BYTES) { if (bytes>limit) stop('容量上限（25MiB）を超えました。安全のため処理を中止します'); }
export async function makeArchive({appId,fields,layout,records,download,now=new Date().toISOString(), maxBytes=MAX_BYTES}) {
  if (!Number.isSafeInteger(Number(appId)) || Number(appId)<=0) stop('アプリIDが不正です');
  if (!Array.isArray(records) || records.length>MAX_RECORDS) stop('レコード上限を超えました');
  if (typeof download!=='function') stop('ファイル取得処理が必要です');
  const schema=writableSchema(fields);
  const out=records.map(r=>normalizeRecord(r,schema));
  const contents={};
  const attachments={};
  let size=0;
  for (const rec of out) {
    const pending=[];
    visitFiles(rec,schema, f=>pending.push(f));
    for (const f of pending) {
      if (!f.fileKey) stop('添付ファイルの識別子がありません');
      sizeCheck(size+f.size,maxBytes);
      if (!attachments[f.fileKey]) {
        const bytes=u8(await download(f.fileKey));
        size+=bytes.byteLength; sizeCheck(size,maxBytes);
        const hash=await sha256(bytes);
        contents['attachments/'+hash]=bytes;
        attachments[f.fileKey]={ref:hash, name:f.name, size:bytes.byteLength, contentType:f.contentType};
      }
      const info=attachments[f.fileKey];
      // File reference remains self-describing in records, portable without source fileKey.
      f.ref=info.ref; f.name=info.name; f.size=info.size; f.contentType=info.contentType;
      delete f.fileKey;
    }
  }
  const texts={
    'schema/fields.json':s(schema),
    'schema/layout.json':s(layout || {}),
    // Full source field definitions are only used to create a NEW app draft.
    // Never apply raw definitions to an existing app.
    'schema/source-fields.json':s({properties:fields?.properties||fields||{}}),
    'data/records.jsonl':out.map(r=>s(r)).join('\n')+(out.length?'\n':'')
  };
  const digests={};
  for (const [path,body] of Object.entries(texts)) {
    const bytes=strToU8(body); size+=bytes.length; sizeCheck(size,maxBytes);
    contents[path]=bytes; digests[path]=await sha256(bytes);
  }
  const uniqueFiles=Object.entries(contents).filter(([name])=>name.startsWith('attachments/')).map(([path,b])=>({path,size:b.length,sha256:path.slice('attachments/'.length)}));
  const manifest={
    format:FORMAT,version:VERSION,createdAt:now,sourceAppId:Number(appId),
    recordCount:out.length, files:uniqueFiles, digests,
    limitations:['append-only restore','no system fields or audit history','no process status reconstruction','new-app draft only','no permissions or views','lookup values omitted'],
  };
  const manifestBytes=strToU8(s(manifest)); size+=manifestBytes.length; sizeCheck(size,maxBytes);
  contents['manifest.json']=manifestBytes;
  const zip=zipSync(contents,{level:6}); sizeCheck(zip.length,maxBytes);
  return {zip,manifest,hash:await sha256(zip)};
}
export async function inspectArchive(zipInput,{expectedHash, maxBytes=MAX_BYTES}={}) {
  const bytes=u8(zipInput); sizeCheck(bytes.byteLength,maxBytes);
  if (expectedHash && (await sha256(bytes))!==expectedHash.toLowerCase()) stop('ZIP全体のSHA-256が一致しません');
  let inflatedTotal=0, entries;
  try {
    entries=unzipSync(bytes,{filter:(file)=>{
      checkPath(file.name);
      const n=Number(file.originalSize);
      if (!Number.isSafeInteger(n)||n<0) stop('ZIPのサイズが不正です');
      inflatedTotal+=n; sizeCheck(inflatedTotal,maxBytes);
      return true;
    }});
  } catch(e) { throw new Error('ZIP展開・検証に失敗しました: '+e.message); }
  const load = path => { if(!entries[path])stop('必須ファイルがありません: '+path); return strFromU8(entries[path]); };
  let manifest,schema,layout,sourceFields=null,records;
  try {
    manifest=JSON.parse(load('manifest.json'));
    schema=JSON.parse(load('schema/fields.json'));
    layout=JSON.parse(load('schema/layout.json'));
    const text=load('data/records.jsonl');
    records=text.trim()?text.trimEnd().split('\n').map(line=>JSON.parse(line)):[];
  } catch(e) { throw new Error('内容を読み取れません: '+e.message); }
  if (manifest?.format!==FORMAT||![1,2].includes(manifest?.version)) stop('未対応のバックアップ形式です');
  const expectedTextPaths=['schema/fields.json','schema/layout.json','data/records.jsonl'];
  if(manifest.version===2){
    try { sourceFields=JSON.parse(load('schema/source-fields.json')); }
    catch(e){stop('v2形式のフォーム定義が不正です: '+e.message);}
    if (!obj(sourceFields)||!obj(sourceFields.properties))stop('フォーム定義が不正です');
    expectedTextPaths.push('schema/source-fields.json');
  }
  // Do not permit an attacker to present a legacy archive with unchecked new metadata.
  if(manifest.version===1&&entries['schema/source-fields.json'])stop('v1形式に未検証のフィールド設定があります');
  if (!obj(schema)||!Array.isArray(records)||records.length>MAX_RECORDS||records.length!==manifest.recordCount)stop('件数またはフィールド構造が不正です');
  for (const p of expectedTextPaths) {
    if (await sha256(entries[p])!==manifest.digests?.[p]) stop('内容のハッシュが一致しません: '+p);
  }
  // v2 schema and complete field definitions must describe the same writable
  // field codes/types. Prevent a validly re-hashed but contradictory ZIP.
  if (sourceFields && JSON.stringify(writableSchema(sourceFields))!==JSON.stringify(schema))
    stop('レコード構造と元アプリのフィールド定義が矛盾しています');
  if (!Array.isArray(manifest.files))stop('ファイル一覧が不正です');
  const manifestPaths=new Set();
  for (const f of manifest.files) {
    if (!f || typeof f.path!=='string' || !/^attachments\/[0-9a-f]{64}$/.test(f.path) || manifestPaths.has(f.path))stop('添付ファイル一覧が不正です');
    manifestPaths.add(f.path);
    if (!entries[f.path]||entries[f.path].length!==f.size||await sha256(entries[f.path])!==f.sha256||f.path!=='attachments/'+f.sha256)stop('添付ファイルの整合性エラー');
  }
  for (const p of Object.keys(entries)) {
    checkPath(p);
    if(p.startsWith('attachments/')&&!manifestPaths.has(p))stop('未申告の添付ファイルがあります');
  }
  for(const r of records){
    if (!obj(r))stop('レコードが不正です');
    visitFiles(r,schema,f=>{if(!manifestPaths.has('attachments/'+f.ref))stop('レコードが参照する添付ファイルが欠落しています');});
  }
  return {manifest,schema,layout,sourceFields,records,files:entries,archiveHash:await sha256(bytes)};
}
export function createRestorePlan(archive, targetFields, targetAppId, managementAppId) {
  if (!archive?.manifest||!obj(archive.schema)||!Array.isArray(archive.records)) stop('検証済みアーカイブが必要です');
  const id=Number(targetAppId);
  if (!Number.isSafeInteger(id)||id<=0||id===Number(managementAppId)) stop('復元先アプリIDが不正または管理アプリです');
  const target=writableSchema(targetFields);
  const mapped={},skipped=[];
  for (const [code, def] of Object.entries(archive.schema)) {
    const t=target[code];
    if (!t) {skipped.push(code+': 復元先に存在しません'); continue;}
    if(t.type!==def.type)stop('互換性のないフィールド型: '+code+' ('+def.type+' -> '+t.type+')');
    if(def.type==='SUBTABLE') {
      const members={};
      for(const [sub,sd] of Object.entries(def.fields)){
        if(!t.fields[sub]){skipped.push(code+'.'+sub+': 復元先に存在しません');continue;}
        if(t.fields[sub].type!==sd.type)stop('テーブル内のフィールド型が一致しません: '+code+'.'+sub);
        members[sub]=sd;
      }
      mapped[code]={type:'SUBTABLE',fields:members};
    }else mapped[code]=def;
  }
  // The archive stores FILE references as SHA256 refs, not kintone fileKeys.
  // Preserve those portable refs while excluding unmatched destination fields.
  const copyMapped = (r, defs) => {
    const targetRecord={};
    for(const [code,def] of Object.entries(defs)) {
      if(!r[code])continue;
      if(def.type==='SUBTABLE'){
        targetRecord[code]={value:(r[code].value||[]).map(row=>({value:copyMapped(row.value||{},def.fields)}))};
      }else targetRecord[code]={value:structuredClone(r[code].value)};
    }
    return targetRecord;
  };
  const rows=archive.records.map(r=>copyMapped(r,mapped));
  if(rows.length && Object.keys(mapped).length===0)stop('転送できるフィールドがありません');
  const fileRefs=new Set(archive.manifest.files.map(f=>f.sha256));
  for(const r of rows)visitFiles(r,mapped,f=>{if(!fileRefs.has(f.ref))stop('添付ファイル参照が不正です');});
  return {targetAppId:id,rows,mapped,skipped,recordCount:rows.length,sourceAppId:archive.manifest.sourceAppId,archiveCreatedAt:archive.manifest.createdAt};
}
export async function materializeRestoreRow(row, schema, upload, entries) {
  const out=structuredClone(row);
  const todo=[];
  visitFiles(out,schema,f=>todo.push(f));
  for(const f of todo) {
    const bytes=entries['attachments/'+f.ref];
    if(!bytes)stop('添付ファイルの実体がありません');
    const key=await upload(bytes,f.name||'file.bin',f.contentType||'application/octet-stream');
    delete f.ref;delete f.name;delete f.size;delete f.contentType;f.fileKey=key;
  }
  return out;
}