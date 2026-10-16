// Safe, append-only migration with explicit field mapping and per-record
// destination markers. Requires a unique ResoArcRestoreKey destination field.
import {createRestorePlan, materializeRestoreRow, sha256} from './core.js';

export const MARKER_CODE='ResoArcRestoreKey';
const bad=message=>{throw new Error(message);};
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const unsafe=new Set(['__proto__','prototype','constructor']);
const code=v=>typeof v==='string'&&v.length>0&&v.length<=128&&!unsafe.has(v)&&!/[/\\\[\].\s]/u.test(v);
const ensureCode=v=>{if(!code(v))bad('不正なフィールドコード: '+String(v));return v;};
const put=(obj,key,value)=>Object.defineProperty(obj,key,{value,writable:true,enumerable:true,configurable:true});
const own=(obj,key)=>Object.hasOwn(obj,key);

/**
 * Map source field codes to destination codes by exact type.
 * Example {"Customer":"Client","Rows":"Details",
 *          "Rows.Note":"Details.Description"}.
 * Never silently coerce a field type or allow two sources to share a target.
 */
export function createMappedRestorePlan(archive,targetFields,targetAppId,managementAppId,mapping={}){
  if(!object(mapping))bad('フィールド対応表はJSONオブジェクトにしてください');
  if(!archive?.schema||!Array.isArray(archive?.records))bad('検証済みバックアップが必要です');
  const src=archive.schema, usedTargets=new Set();
  const target=targetFields?.properties||targetFields;
  if(!object(target))bad('移行先のフィールド設定がありません');
  const sourcePaths=new Set();
  for(const [name,def] of Object.entries(src)){
    sourcePaths.add(name);
    if(def.type==='SUBTABLE')for(const child of Object.keys(def.fields||{}))sourcePaths.add(name+'.'+child);
  }
  for(const [from,to] of Object.entries(mapping)){
    if(!sourcePaths.has(from))bad('対応表に存在しない元フィールドがあります: '+from);
    if(typeof to!=='string')bad('移行先フィールドコードは文字列で指定してください: '+from);
    for(const p of to.split('.'))ensureCode(p);
    if(from.split('.').length!==to.split('.').length)bad('テーブル階層が一致しません: '+from);
    if(to.split('.').length>2)bad('テーブルの入れ子は未対応です');
    if(to===MARKER_CODE || to.endsWith('.'+MARKER_CODE))bad('復元管理用フィールドは対応先に指定できません');
  }
  const renamedSchema=Object.create(null);
  const schemaCopy=(defs,mappedDefs,tableSource='',tableTarget='')=>{
    for(const [name,def] of Object.entries(defs)){
      if(!tableSource&&name===MARKER_CODE)continue;
      const from=tableSource?tableSource+'.'+name:name;
      const destName=own(mapping,from)?mapping[from]:tableTarget?tableTarget+'.'+name:name;
      const destParts=destName.split('.');
      const expectedDepth=tableSource?2:1;
      if(destParts.length!==expectedDepth)bad('フィールド対応の階層が不正です: '+from);
      destParts.forEach(ensureCode);
      if(tableSource&&destParts[0]!==tableTarget)bad('テーブル内フィールドの対応先が親テーブルと異なります: '+from);
      const destField=destParts.at(-1);
      if(!tableSource&&destField===MARKER_CODE)bad('復元管理用フィールドを上書きできません');
      const complete=tableSource?destParts.join('.'):destField;
      if(usedTargets.has(complete))bad('複数の元フィールドが同じ移行先を参照しています: '+complete);
      usedTargets.add(complete);
      if(def.type==='SUBTABLE'){
        const nestedSchema=Object.create(null);
        schemaCopy(def.fields,nestedSchema,name,destField);
        put(mappedDefs,destField,{type:'SUBTABLE',fields:nestedSchema});
      }else put(mappedDefs,destField,{type:def.type});
    }
  };
  // Create mappings only once. Record values are independently transformed.
  schemaCopy(src,renamedSchema);
  const remapRow=(defs,row,tableSource='',tableTarget='')=>{
    const out=Object.create(null);
    for(const [name,def] of Object.entries(defs)){
      if(!tableSource&&name===MARKER_CODE)continue;
      if(!own(row||{},name))continue;
      const from=tableSource?tableSource+'.'+name:name;
      const targetPath=own(mapping,from)?mapping[from]:tableTarget?tableTarget+'.'+name:name;
      const dest=targetPath.split('.').at(-1);
      if(def.type==='SUBTABLE'){
        put(out,dest,{value:(row[name].value||[]).map(r=>({value:remapRow(def.fields,r.value,name,dest)}))});
      }else put(out,dest,{value:structuredClone(row[name].value)});
    }
    return out;
  };
  const rows=archive.records.map(r=>remapRow(src,r));
  const mappedArchive={...archive,schema:renamedSchema,records:rows};
  const plan=createRestorePlan(mappedArchive,targetFields,targetAppId,managementAppId);
  plan.mapping=structuredClone(mapping);
  // Reject explicit maps that target missing destination or incompatible types.
  for(const [from,to] of Object.entries(mapping)){
    const targetParts=to.split('.');
    const schemaEntry=targetParts.length===1?target[targetParts[0]]:target[targetParts[0]]?.fields?.[targetParts[1]];
    if(!schemaEntry)bad('対応表の移行先フィールドが存在しません: '+to);
    if(plan.skipped.some(x=>x===to+': 復元先に存在しません'))bad('対応先を移行できません: '+to);
  }
  // Destination validation must finish before any upload or record write.
  // Choice labels can differ between domains even when field types match.
  const validChoices=new Set(['DROP_DOWN','RADIO_BUTTON','CHECK_BOX','MULTI_SELECT']);
  const checkRow=(row,defs,fieldDefs,location)=>{
    for(const [field,info] of Object.entries(defs)){
      const dest=fieldDefs?.[field];
      if(!dest)continue;
      const value=row[field]?.value;
      if(info.type==='SUBTABLE'){
        for(const [index,sub] of (Array.isArray(value)?value:[]).entries())
          checkRow(sub.value||{},info.fields,dest.fields,location+field+'['+index+'].');
      }else if(validChoices.has(info.type)&&value!==undefined&&value!==null){
        const choices=new Set(Object.keys(dest.options||{}));
        const chosen=Array.isArray(value)?value:[value];
        for(const selected of chosen){
          if(selected!==''&&selected!==null&&!choices.has(String(selected)))
            bad('移行先の選択肢に存在しない値: '+location+field+' = '+String(selected));
        }
      }
    }
  };
  for(const [index,row] of plan.rows.entries())checkRow(row,plan.mapped,target,'record['+index+'].');
  // Do not start a batch that is guaranteed to fail due to a missing
  // required destination field. Source table rows are validated by kintone.
  for(const [name,definition] of Object.entries(target)){
    if(name===MARKER_CODE)continue;
    if(definition.required===true && !own(plan.mapped,name) &&
       (definition.defaultValue===undefined||definition.defaultValue===null||definition.defaultValue===''))
      bad('復元先に未対応の必須フィールドがあります: '+name);
  }
  const marker=target[MARKER_CODE];
  if(!marker||marker.type!=='SINGLE_LINE_TEXT'||marker.unique!==true||marker.lookup||marker.expression)
    bad('移行先に重複禁止の文字列（1行）フィールド '+MARKER_CODE+' が必要です。既存アプリの場合は管理者が追加してください');
  if(plan.rows.some(row=>own(row,MARKER_CODE)))bad('復元管理用フィールドはデータに含められません');
  plan.markerCode=MARKER_CODE;
  return plan;
}
function digestUtf8(s){return sha256(new TextEncoder().encode(s));}
export async function restoreKeyBase(archive,plan){
  if(!/^[0-9a-f]{64}$/.test(archive?.archiveHash||''))bad('検証済みアーカイブのハッシュが必要です');
  const canonicalMapping=Object.fromEntries(Object.entries(plan.mapping||{}).sort(([a],[b])=>a.localeCompare(b,'en')));
  const mapDigest=await digestUtf8(JSON.stringify(canonicalMapping));
  const base='RA3_'+archive.archiveHash.slice(0,32)+'_'+mapDigest.slice(0,12)+'_';
  return {base, archivePrefix:'RA3_'+archive.archiveHash.slice(0,32)+'_', mappingFingerprint:mapDigest.slice(0,12)};
}
export function keyForIndex(base,index){
  if(!Number.isSafeInteger(index)||index<0)bad('復元行番号が不正です');
  const key=base+index.toString(36);
  if(key.length>64)bad('復元識別子が長すぎます');
  return key;
}

/** Cursor scan includes all visible destination rows. A unique marker field
 * additionally protects against a second client inserting the same record. */
export async function scanRestoreKeys(app,api,{maxRows=200000}={}){
  const response=await api('/k/v1/records/cursor.json','POST',{app,fields:[MARKER_CODE],size:500});
  if(!response?.id)bad('復元済み確認用のCursorを作成できませんでした');
  let finished=false,count=0;
  const keys=new Set();
  try{
    while(!finished){
      const page=await api('/k/v1/records/cursor.json','GET',{id:response.id});
      if(!Array.isArray(page?.records)||typeof page.next!=='boolean'||page.records.length>500)
        bad('移行先の取得結果が不正です');
      if(page.next&&page.records.length===0)
        bad('復元済み確認用Cursorが進行しません。処理を中止します');
      count+=page.records.length;
      if(count>maxRows)bad('移行先のレコード数が検索上限を超えています');
      for(const record of page.records){
        const k=record?.[MARKER_CODE]?.value;
        if(typeof k==='string'&&k)keys.add(k);
      }
      finished=!page.next;
    }
  }finally{
    if(!finished)try{await api('/k/v1/records/cursor.json','DELETE',{id:response.id});}catch{/* expired cursors are cleaned by kintone */}
  }
  return keys;
}

/** Read-only preview that grounds the resume counts in actual target data. */
export async function previewRestoreProgress({archive,plan,api}){
  if(plan?.markerCode!==MARKER_CODE||!Array.isArray(plan?.rows))bad('復元用プランが不正です');
  const {base,archivePrefix}=await restoreKeyBase(archive,plan);
  const keys=await scanRestoreKeys(plan.targetAppId,api);
  if([...keys].some(k=>k.startsWith(archivePrefix)&&!k.startsWith(base)))
    bad('同じバックアップを別のフィールド対応付けで移行した履歴があります。データを確認してください');
  const missingIndexes=[];
  for(let i=0;i<plan.rows.length;i++)if(!keys.has(keyForIndex(base,i)))missingIndexes.push(i);
  return {base,missingIndexes,total:plan.rows.length,already:plan.rows.length-missingIndexes.length,remaining:missingIndexes.length};
}

/** Resume by scanning destination markers every time.
 * Once an upload batch was sent but its result is unknown, STOP; never
 * auto-retry blindly. The user explicitly starts a new preview/resume. */
export async function runResumableRestore({archive,plan,api,upload,onProgress=()=>{},batchSize=20}){
  if(typeof api!=='function'||typeof upload!=='function')bad('kintone APIの実装が必要です');
  if(!Number.isSafeInteger(batchSize)||batchSize<1||batchSize>100)bad('バッチ件数が不正です');
  if(plan?.markerCode!==MARKER_CODE||!Array.isArray(plan?.rows))bad('復元用プランが不正です');
  const snapshot=await previewRestoreProgress({archive,plan,api});
  const {base}=snapshot;
  const missing=snapshot.missingIndexes;
  onProgress({total:plan.rows.length,already:snapshot.already,added:0,remaining:missing.length});
  let completed=0;
  for(let start=0;start<missing.length;start+=batchSize){
    const indexes=missing.slice(start,start+batchSize);
    const records=[];
    for(const index of indexes){
      const row=await materializeRestoreRow(plan.rows[index],plan.mapped,upload,archive.files);
      row[MARKER_CODE]={value:keyForIndex(base,index)};
      records.push(row);
    }
    // Atomic per-request on kintone. If the response is lost, we MUST NOT
    // assume failure. A future invocation scans keys before writing again.
    const result=await api('/k/v1/records.json','POST',{app:plan.targetAppId,records});
    if(!Array.isArray(result?.ids)||result.ids.length!==records.length)
      bad('登録結果を確認できません。復元先を再確認してから再開してください');
    completed+=records.length;
    onProgress({total:plan.rows.length,already:plan.rows.length-missing.length,added:completed,remaining:missing.length-completed});
  }
  return {total:plan.rows.length,added:completed,already:plan.rows.length-missing.length,completed:true};
}
