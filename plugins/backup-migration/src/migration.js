// Pure, conservative kintone application scaffold planner. No writes here.
// v2 archive includes schema/source-fields.json. V1 archives remain restorable,
// but cannot reproduce forms because v1 only retained field types.
const TYPES=new Set([
  'SINGLE_LINE_TEXT','MULTI_LINE_TEXT','RICH_TEXT','NUMBER',
  'RADIO_BUTTON','DROP_DOWN','CHECK_BOX','MULTI_SELECT',
  'DATE','TIME','DATETIME','LINK','USER_SELECT','ORGANIZATION_SELECT',
  'GROUP_SELECT','FILE'
]);
const SELECT=new Set(['RADIO_BUTTON','DROP_DOWN','CHECK_BOX','MULTI_SELECT']);
const TABLE_TYPES=new Set([...TYPES].filter(t=>t!=='RICH_TEXT'));
const SAFE_CODE=/^[^\s.\[\]\\/]{1,128}$/u;
const bad=message=>{throw new Error(message);};
const plain=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const str=x=>typeof x==='string'?x:'';
const copy=(o,keys,into)=>{for(const key of keys)if(Object.hasOwn(o,key))into[key]=structuredClone(o[key]);};

function definition(code,raw,inTable,skipped){
  if(!plain(raw)||!SAFE_CODE.test(code)||['__proto__','prototype','constructor'].includes(code)){
    skipped.push(code+': 未対応のフィールドコード');
    return null;
  }
  if(raw.type==='SUBTABLE'){
    if(inTable){skipped.push(code+': テーブルの入れ子は未対応');return null;}
    const fields={};
    for(const [child,def] of Object.entries(raw.fields||{})){
      const built=definition(child,def,true,skipped);
      if(built)Object.defineProperty(fields,child,{value:built,enumerable:true,writable:true,configurable:true});
    }
    if(!Object.keys(fields).length){skipped.push(code+': テーブル内の移行可能フィールドがありません');return null;}
    return {type:'SUBTABLE',code,label:str(raw.label)||code,fields};
  }
  if(!TYPES.has(raw.type)||raw.lookup||raw.referenceTable||(inTable&&!TABLE_TYPES.has(raw.type))){
    skipped.push(code+': 対応できないフィールド種別または参照設定 ('+(raw.type||'unknown')+')');
    return null;
  }
  const def={type:raw.type,code,label:str(raw.label)||code,required:false,unique:false};
  // Deliberately omit defaults, organization/user constraints, validations and
  // cross-app references. This is a safe *data migration* scaffold, not a clone.
  if(SELECT.has(raw.type)){
    if(!plain(raw.options)||Object.keys(raw.options).length===0){
      skipped.push(code+': 選択肢がなく再作成できません');
      return null;
    }
    const options={};
    for(const [label,opt] of Object.entries(raw.options)){
      if(!plain(opt)||!label||!Number.isFinite(Number(opt.index))) {
        skipped.push(code+': 選択肢設定が不正です');return null;
      }
      Object.defineProperty(options,label,{value:{label,index:String(opt.index)},enumerable:true,writable:true,configurable:true});
    }
    def.options=options;
    if(raw.type==='RADIO_BUTTON'||raw.type==='CHECK_BOX'||raw.type==='MULTI_SELECT')
      if(['VERTICAL','HORIZONTAL'].includes(raw.align))def.align=raw.align;
  }
  if(raw.type==='LINK')def.protocol=['WEB','CALL','MAIL'].includes(raw.protocol)?raw.protocol:'WEB';
  if(raw.type==='NUMBER')copy(raw,['digit','displayScale','unit','unitPosition'],def);
  if(raw.type==='FILE'&&['50','150','250','500'].includes(String(raw.thumbnailSize)))def.thumbnailSize=String(raw.thumbnailSize);
  return def;
}

/** Create a minimum compatible form for a fresh kintone app.
 * Do not use this on existing applications. */
export function planNewApp(archive, name){
  if(!archive||!archive.manifest||!plain(archive.sourceFields?.properties))
    bad('このバックアップにはアプリ構造再現用のフィールド設定がありません。v2形式で再取得してください');
  if(archive.manifest.version!==2)bad('自動フォーム再現はv2形式だけ対応します');
  if(typeof name!=='string'||!name.trim()||name.length>64)bad('アプリ名は1～64文字にしてください');
  const props={};
  const skipped=[];
  for(const [code,def] of Object.entries(archive.sourceFields.properties)){
    const compiled=definition(code,def,false,skipped);
    if(compiled)Object.defineProperty(props,code,{value:compiled,enumerable:true,writable:true,configurable:true});
  }
  if(!Object.keys(props).length)bad('移行できるフィールドがありません');
  // Mandatory unique record identity for resumable append-only restores.
  // Even if the source already has a field with this code, do not copy its
  // original values. Each migrated row receives a NEW deterministic marker.
  Object.defineProperty(props,'ResoArcRestoreKey',{value:{
    type:'SINGLE_LINE_TEXT',code:'ResoArcRestoreKey',label:'ResoArc復元識別子',
    required:false,unique:true
  },writable:true,enumerable:true,configurable:true});
  // Use no implicit auto-mapping for skipped required fields.
  const sourceCodes=Object.keys(archive.schema);
  const missing=sourceCodes.filter(code=>!Object.hasOwn(props,code));
  for(const code of missing)if(!skipped.some(s=>s.startsWith(code+':')))skipped.push(code+': 移行対象から除外');
  return {name:name.trim(),properties:props,skipped,fieldCount:Object.keys(props).length,sourceAppId:archive.manifest.sourceAppId,recordCount:archive.records.length,
    warnings:['既存のアプリには適用しません','元の表示配置・権限・一覧・プロセス・ルックアップ参照は再現しません','必須・一意制約は移行優先のため無効にします','データ復元は別途プレビューと明示承認が必要です']};
}

/** Injectable mockable adapter. Affects a newly-created preview app only.
 * Stops on any error, preserving the created app for manual review.
 * Does NOT add records, set layout, alter existing apps, or delete anything.
 */
export async function createDraftApp(plan, api, onStep=()=>{}){
  if(typeof api!=='function')bad('kintone API関数がありません');
  if(!plan?.name||!plain(plan.properties)||!Object.keys(plan.properties).length)bad('作成計画が不正です');
  onStep('動作テスト環境に新規アプリを作成しています');
  const created=await api('/k/v1/preview/app.json','POST',{name:plan.name});
  const id=Number(created?.app);
  if(!Number.isSafeInteger(id)||id<=0)bad('新規アプリIDを取得できませんでした');
  try {
    onStep('新規アプリ #'+id+' にフィールドを設定しています');
    await api('/k/v1/preview/app/form/fields.json','POST',{app:id,properties:plan.properties});
    // No automatic deployment: the user reviews settings and updates the app
    // manually, avoiding activation of an incomplete or mismatched form.
    onStep('新規アプリ #'+id+' の下書きができました。アプリの設定画面で内容を確認してください');
  } catch(e){
    throw new Error('アプリ #'+id+' は作成されましたが、フィールド追加が失敗しました。設定画面で確認してください。原因: '+e.message);
  }
  return {appId:id,deployed:false,recordsCopied:0,requiresManualDeploy:true};
}