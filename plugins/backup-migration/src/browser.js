import {makeArchive,inspectArchive,MAX_BYTES} from './core.js';
import {createMappedRestorePlan,runResumableRestore,previewRestoreProgress,MARKER_CODE} from './restore.js';
import {planNewApp,createDraftApp} from './migration.js';

const K=window.kintone;
const api=(path,method,body)=>K.api(K.api.url(path,true),method,body);
const positiveId=v=>{const n=Number(v);if(!Number.isSafeInteger(n)||n<=0)throw Error('アプリ・レコードIDは正の整数で入力してください');return n;};
function managementApp(){const id=Number(K.app.getId());if(!id)throw Error('kintoneアプリの一覧画面から実行してください');return id;}
function ensureExternalId(id){if(id===managementApp())throw Error('バックアップ管理アプリ自体は対象にできません');}
const getFields=app=>api('/k/v1/app/form/fields.json','GET',{app});
const getLayout=app=>api('/k/v1/app/form/layout.json','GET',{app});
async function listRecords(app){
  const created=await api('/k/v1/records/cursor.json','POST',{app,size:500});
  let cursor=created.id,done=false;
  const records=[];
  try{
    while(!done){
      const page=await api('/k/v1/records/cursor.json','GET',{id:cursor});
      records.push(...page.records);
      if(records.length>20000)throw Error('一度に処理できるレコードは20,000件までです');
      done=!page.next;
    }
  } finally {
    // The last page deletes the cursor automatically. Cleanup on failure.
    if(!done)try{await api('/k/v1/records/cursor.json','DELETE',{id:cursor});}catch(e){console.warn('cursor cleanup failed',e);}
  }
  return records;
}
async function downloadFile(fileKey){
  const resp=await fetch('/k/v1/file.json?fileKey='+encodeURIComponent(fileKey),{method:'GET',headers:{'X-Requested-With':'XMLHttpRequest'}});
  if(!resp.ok)throw Error('ファイルの取得に失敗しました (HTTP '+resp.status+')');
  const bytes=new Uint8Array(await resp.arrayBuffer());
  if(bytes.length>MAX_BYTES)throw Error('添付ファイルが容量上限を超えました');
  return bytes;
}
async function uploadFile(bytes,name,type='application/octet-stream'){
  if(bytes.length>MAX_BYTES)throw Error('アップロード容量上限を超えました');
  const form=new FormData();
  form.append('__REQUEST_TOKEN__',K.getRequestToken());
  form.append('file',new Blob([bytes],{type}),name);
  const resp=await fetch('/k/v1/file.json',{method:'POST',headers:{'X-Requested-With':'XMLHttpRequest'},body:form});
  if(!resp.ok)throw Error('ファイルのアップロードに失敗しました (HTTP '+resp.status+'): '+(await resp.text()).slice(0,300));
  const result=await resp.json();
  if(!result.fileKey)throw Error('ファイルキーが返されませんでした');
  return result.fileKey;
}
async function backup(app,name){
  ensureExternalId(app);
  const [fields,layout,records]=await Promise.all([getFields(app),getLayout(app),listRecords(app)]);
  const {zip,hash,manifest}=await makeArchive({appId:app,fields,layout,records,download:downloadFile});
  const key=await uploadFile(zip,'resoarc-backup-'+app+'-'+new Date().toISOString().replace(/[:.]/g,'-')+'.zip','application/zip');
  const record={
    BackupName:{value:name||('App '+app+' '+manifest.createdAt)},
    SourceAppId:{value:String(app)},
    ArchiveHash:{value:hash},
    BackupVersion:{value:String(manifest.version)},
    RecordCount:{value:String(manifest.recordCount)},
    Archive:{value:[{fileKey:key}]}
  };
  const result=await api('/k/v1/record.json','POST',{app:managementApp(),record});
  return {id:result.id,manifest,hash,bytes:zip.length};
}
async function loadBackup(id){
  const {record}=await api('/k/v1/record.json','GET',{app:managementApp(),id});
  const file=record?.Archive?.value?.[0];
  const hash=record?.ArchiveHash?.value;
  if(!file||!hash)throw Error('Archive添付とArchiveHashを持つバックアップレコードを指定してください');
  if(Number(file.size)>MAX_BYTES)throw Error('ZIPの容量上限を超えています');
  const zip=await downloadFile(file.fileKey);
  const result=await inspectArchive(zip,{expectedHash:hash});
  if(String(result.manifest.sourceAppId)!==String(record?.SourceAppId?.value))throw Error('管理レコードのバックアップ元IDとZIPが一致しません');
  return result;
}
function el(tag,text,cls){
  const node=document.createElement(tag);
  if(text!==undefined)node.textContent=text;
  if(cls)node.className=cls;
  return node;
}
function addButton(where,text,onClick){
  const b=el('button',text);
  b.type='button';b.style.cssText='margin:4px 8px 4px 0;padding:9px 13px;border:1px solid #345f75;border-radius:5px;background:#ecf5f7;color:#173c52;cursor:pointer;font-weight:600';
  b.onclick=onClick;where.appendChild(b);return b;
}
function initialize(){
  const header=K.app.getHeaderMenuSpaceElement();
  if(!header || header.querySelector('[data-resoarc-backup]'))return;
  const root=el('section');root.dataset.resoarcBackup='true';
  root.style.cssText='padding:9px;margin:8px 0;border:1px solid #b8d0d4;border-radius:8px;background:#f9fcfd;color:#18353b;max-width:980px';
  root.appendChild(el('strong','ResoArc Backup & Migration | 0.3 alpha'));
  const actions=el('div');root.appendChild(actions);
  const msg=el('div','専用のバックアップ管理アプリです。書き込みは手動操作時だけ実行します。');
  msg.style.cssText='white-space:pre-wrap;font-size:13px;margin-top:7px;line-height:1.6';root.appendChild(msg);
  const progress=el('div');progress.style.cssText='font-size:13px;color:#394';root.appendChild(progress);
  let current=null, draft=null;
  const draftButton=addButton(actions,'新規アプリの下書きを作成 (データは書かない)',async()=>{
    if(!draft)return;
    const plan=draft;
    const typed=window.prompt('新規アプリ「'+plan.name+'」を作成し、'+plan.fieldCount+' フィールドを設定します。\n既存のアプリには変更を加えません。\n作成するには次を正確に入力してください: CREATE '+plan.name,'');
    if(typed!=='CREATE '+plan.name)return;
    if(!window.confirm('最終確認: 新しいアプリの動作テスト環境にフィールドを追加します。レコードの復元・アプリ設定の本番反映は行いません。'))return;
    for(const b of actions.querySelectorAll('button'))b.disabled=true;
    try{
      const done=await createDraftApp(plan,api,text=>{progress.textContent=text;});
      msg.textContent='新規アプリ #'+done.appId+' の下書きを作成しました。\nアプリの管理者設定画面で内容を確認し、手動で「アプリを更新」してください。\n更新後、復元プレビューから同じアプリIDを指定してください。\nレコードはまだ0件、既存アプリは変更していません。';
      draft=null;
      draftButton.hidden=true;
    }catch(e){msg.textContent='新規アプリの作成処理が中断しました。作成されたアプリが残っている可能性があります。\n'+e.message;console.error(e);}
    finally{for(const b of actions.querySelectorAll('button'))b.disabled=false;}
  });
  draftButton.hidden=true;
  const restoreButton=addButton(actions,'復元を実行 (追記のみ)',async()=>{
    if(!current)return;
    const {archive,plan,backupRecordId}=current;
    const confirmText='RESTORE '+plan.targetAppId+' '+plan.recordCount;
    const typed=window.prompt('バックアップレコード #'+backupRecordId+' からアプリ '+plan.targetAppId+' に '+plan.recordCount+' 件を追加します。\n既存データを削除・上書きしません。復元済みの行は一意キーで識別し、再開時にスキップします。追加の取り消しは自動ではできません。\n実行するには正確に入力してください:\n'+confirmText,'');
    if(typed!==confirmText)return;
    if(!window.confirm('最終確認: レコードを '+plan.recordCount+' 件追加します。複数バッチの途中で停止した場合、途中まで追加済みの可能性があります。実行しますか？'))return;
    restoreButton.disabled=true;
    try{
      // Validate once more and recheck current destination field definitions.
      const refreshed=await getFields(plan.targetAppId);
      const updatedPlan=createMappedRestorePlan(archive,refreshed,plan.targetAppId,managementApp(),plan.mapping);
      if(JSON.stringify(updatedPlan.mapped)!==JSON.stringify(plan.mapped))throw Error('復元先のフィールド定義がプレビューから変化しました。プレビューをやり直してください');
      const done=await runResumableRestore({archive,plan,api,upload:uploadFile,
        onProgress:({total,already,added,remaining})=>{
          progress.textContent='復元済み '+already+' 件 / 新規追加 '+added+' 件 / 残り '+remaining+' 件（全 '+total+' 件）';
        }});
      msg.textContent='復元処理完了: '+done.added+' 件追加、'+done.already+' 件は復元済みのためスキップしました。元IDや変更履歴は維持されません。';
      current=null;
    }catch(e){msg.textContent='復元が中断されました。一部が追加済みの可能性があります。再実行前に復元先を確認してください。\n'+e.message;console.error(e);}
    finally{restoreButton.disabled=false;}
  });
  restoreButton.hidden=true;
  async function safeRun(job){
    for(const b of actions.querySelectorAll('button'))b.disabled=true;
    restoreButton.hidden=true;current=null;draft=null;draftButton.hidden=true;progress.textContent='';
    try{await job();}catch(e){msg.textContent='エラー: '+e.message;console.error(e);}
    finally{for(const b of actions.querySelectorAll('button'))b.disabled=false;}
  }
  addButton(actions,'バックアップを作成',()=>safeRun(async()=>{
    const input=window.prompt('バックアップ元アプリIDを入力してください。管理アプリと同じIDは指定できません。','');
    if(input===null)return;
    const id=positiveId(input);ensureExternalId(id);
    const name=window.prompt('バックアップ名 (空欄なら自動生成)','')||'';
    if(!window.confirm('アプリ '+id+' のレコードと添付ファイルを読み出し、この管理アプリにZIPを保存します。続行しますか？'))return;
    msg.textContent='バックアップを作成しています。ブラウザーを閉じないでください。';
    const result=await backup(id,name);
    msg.textContent='バックアップ作成完了。管理レコード #'+result.id+' / '+result.manifest.recordCount+' 件 / '+result.bytes+' bytes\nSHA-256: '+result.hash;
  }));
  addButton(actions,'復元プレビュー',()=>safeRun(async()=>{
    const input=window.prompt('バックアップ管理アプリのレコードIDを入力してください','');
    if(input===null)return;
    const backupRecordId=positiveId(input);
    const targetInput=window.prompt('復元先の既存アプリID (管理アプリ以外) を入力してください','');
    if(targetInput===null)return;
    const targetId=positiveId(targetInput);ensureExternalId(targetId);
    msg.textContent='アーカイブを検証しています。';
    const [archive,targetFields]=await Promise.all([loadBackup(backupRecordId),getFields(targetId)]);
    const mapInput=window.prompt('フィールドコード対応表をJSONで入力してください。\n同じフィールドコード同士なら空欄でOK。\n例: {"Title":"Name","Rows":"Lines","Rows.Memo":"Lines.Note"}','');
    if(mapInput===null)return;
    let fieldMap;
    try{fieldMap=mapInput.trim()?JSON.parse(mapInput):{};}catch(e){throw Error('対応表のJSONが不正です: '+e.message);}
    const plan=createMappedRestorePlan(archive,targetFields,targetId,managementApp(),fieldMap);
    const skipped=plan.skipped.length ? ('\n移行対象外:\n'+plan.skipped.join('\n')) : '';
    const resume=await previewRestoreProgress({archive,plan,api});
    msg.textContent='整合性検証: OK\n元アプリ: '+plan.sourceAppId+' / 復元先: '+targetId+'\nバックアップ日時: '+plan.archiveCreatedAt+'\n全対象: '+plan.recordCount+' 件 / 復元済み: '+resume.already+' 件 / 新規追加予定: '+resume.remaining+' 件 / マップされた項目: '+Object.keys(plan.mapped).length+' 件'+skipped+'\n※復元先に重複禁止の '+MARKER_CODE+' が必要です。途中で停止しても復元済みレコードを照合して再開できます。元ID・アクセス権・監査履歴は復元しません。';
    current={archive,plan,backupRecordId};
    restoreButton.hidden=false;
  }));
  addButton(actions,'外部ZIPから移行プレビュー',()=>safeRun(async()=>{
    const file=await new Promise(resolve=>{
      const input=el('input');
      input.type='file'; input.accept='.zip,application/zip';
      input.onchange=()=>resolve(input.files?.[0] || null);
      input.oncancel=()=>resolve(null);
      input.click();
    });
    if(!file)return;
    if(file.size>MAX_BYTES)throw Error('ZIPの容量上限（25MiB）を超えています');
    const targetInput=window.prompt('移行先の既存アプリIDを入力してください','');
    if(targetInput===null)return;
    const targetId=positiveId(targetInput);ensureExternalId(targetId);
    msg.textContent='外部ZIPを検証しています。';
    const archive=await inspectArchive(new Uint8Array(await file.arrayBuffer()));
    const fields=await getFields(targetId);
    const mapInput=window.prompt('フィールドコード対応表をJSONで入力してください。\n同じフィールドコード同士なら空欄でOK。\n例: {"Title":"Name"}','');
    if(mapInput===null)return;
    let fieldMap;
    try{fieldMap=mapInput.trim()?JSON.parse(mapInput):{};}catch(e){throw Error('対応表のJSONが不正です: '+e.message);}
    const plan=createMappedRestorePlan(archive,fields,targetId,managementApp(),fieldMap);
    const skipped=plan.skipped.length ? ('\n移行対象外:\n'+plan.skipped.join('\n')) : '';
    const resume=await previewRestoreProgress({archive,plan,api});
    msg.textContent='外部ZIPの内部整合性: OK (送信元の真正性は別途確認してください)\n元アプリ: '+plan.sourceAppId+' / 移行先: '+targetId+'\n全対象: '+plan.recordCount+' 件 / 復元済み: '+resume.already+' 件 / 新規追加予定: '+resume.remaining+' 件 / マップ項目: '+Object.keys(plan.mapped).length+' 件'+skipped+'\n※復元先に重複禁止の '+MARKER_CODE+' が必要です。元のレコードID・操作履歴・アクセス権は移行できません。';
    current={archive,plan,backupRecordId:'外部ZIP'};
    restoreButton.hidden=false;
  }));
  async function showNewAppPreview(archive){
    const proposed='ResoArc Copy '+archive.manifest.sourceAppId;
    const name=window.prompt('新しいアプリ名を入力してください。既存アプリは変更しません。',proposed);
    if(name===null)return;
    const plan=planNewApp(archive,name);
    const detail=plan.skipped.length?'\n非対応フィールド:\n'+plan.skipped.join('\n'):'';
    msg.textContent='【新規アプリ構造のプレビュー】\n元アプリ: '+plan.sourceAppId+
      '\n作成予定: '+plan.name+'\n対応フィールド: '+plan.fieldCount+
      '\nレコード移行予定: この操作では 0 件（復元は別操作です）'+detail+
      '\n\n制約:\n'+plan.warnings.join('\n');
    draft=plan;
    draftButton.hidden=false;
  }
  addButton(actions,'管理レコードから新規アプリ構造プレビュー',()=>safeRun(async()=>{
    const input=window.prompt('バックアップ管理アプリのレコードIDを指定してください','');
    if(input===null)return;
    msg.textContent='保存済みZIPの整合性を検証しています。';
    await showNewAppPreview(await loadBackup(positiveId(input)));
  }));
  addButton(actions,'外部ZIPから新規アプリ構造プレビュー',()=>safeRun(async()=>{
    const file=await new Promise(resolve=>{
      const input=el('input'); input.type='file';input.accept='.zip,application/zip';
      input.onchange=()=>resolve(input.files?.[0]||null);
      input.oncancel=()=>resolve(null);
      input.click();
    });
    if(!file)return;
    if(file.size>MAX_BYTES)throw Error('ZIPの容量上限を超えています');
    msg.textContent='外部ZIPの整合性を検証しています。';
    await showNewAppPreview(await inspectArchive(new Uint8Array(await file.arrayBuffer())));
  }));
  header.appendChild(root);
}
if(K?.events)K.events.on('app.record.index.show',event=>{try{initialize();}catch(e){console.error('ResoArc Backup init failed',e);}return event;});