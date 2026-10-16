from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[1]
template=ROOT/'plugins'/'conditional'/'v0.1.0-alpha'
sources={
 'conditional-format':('ResoArc 条件付き書式','ResoArc Conditional Formatting','レコードフィールドの条件付き強調表示。CSS注入なし。'),
 'date-calculator':('ResoArc 日付・期間計算','ResoArc Date Calculations','カレンダー日数と営業日数をフォーム上で算出。外部通信なし。'),
 'list-search':('ResoArc 高機能検索・絞り込み','ResoArc List Search','レコード一覧の表示中データを条件検索する開発版。'),
 'grid-editor':('ResoArc Excel風一覧編集','ResoArc Grid Editor','レコード一覧の編集プレビューとリビジョン検査付き更新の開発版。'),
 'kanban':('ResoArc カード・カンバン表示','ResoArc Kanban','一覧のレコードを分類してカード表示する開発版。')
}
for slug,(ja,en,description) in sources.items():
 target=ROOT/'plugins'/slug/'v0.1.0-alpha'
 if target.exists():
  print('Skip existing scaffold',target)
  continue
 (target/'src'/'image').mkdir(parents=True,exist_ok=True)
 for sub in ('js','css','html'): (target/'src'/sub).mkdir(parents=True,exist_ok=True)
 (target/'scripts').mkdir(parents=True,exist_ok=True)
 (target/'tests').mkdir(parents=True,exist_ok=True)
 shutil.copy2(template/'src'/'image'/'icon.png',target/'src'/'image'/'icon.png')
 shutil.copy2(template/'LICENSE',target/'LICENSE')
 manifest=json.loads((template/'src'/'manifest.json').read_text(encoding='utf-8'))
 manifest['name']={'ja':ja,'en':en}
 manifest['description']={'ja':description,'en':description}
 (target/'src'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (target/'scripts'/'build.cjs').write_text("const fs=require('node:fs'),path=require('node:path');const root=path.resolve(__dirname,'../src/js');const code=fs.readFileSync(path.join(root,'core.js'),'utf8')+'\\n'+fs.readFileSync(path.join(root,'runtime.js'),'utf8');for(const file of ['desktop.js','mobile.js'])fs.writeFileSync(path.join(root,file),code,'utf8');\n",encoding='utf-8')
 (target/'package.json').write_text(json.dumps({'name':'resoarc-'+slug,'version':'0.1.0','private':True,'license':'MIT','scripts':{'build':'node scripts/build.cjs','test':'node --test tests/*.test.cjs','check':'npm run build && npm test'}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (target/'src'/'html'/'config.html').write_text('<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main class="ra-rule-config"><h1>'+ja+'</h1><p>試験版です。設定はJSON形式で入力します。保存後、アプリを更新してください。</p><label for="rules">ルール定義（JSON配列）</label><textarea id="rules" rows="16" spellcheck="false"></textarea><div><button id="save" type="button">設定を保存</button><button id="cancel" type="button">戻る</button></div><p role="alert" id="error"></p></main></body></html>',encoding='utf-8')
 (target/'src'/'css'/'config.css').write_text('.ra-rule-config{max-width:800px;margin:30px auto;padding:20px;font:15px/1.7 system-ui,sans-serif;color:#173b44}.ra-rule-config label{display:block;font-weight:bold;margin:12px 0}.ra-rule-config textarea{width:100%;padding:14px;border:1px solid #849ea8;font:14px/1.5 Consolas,monospace}.ra-rule-config button{margin:12px 8px 0 0;padding:10px 18px;background:#183d49;color:#fff;border:0;cursor:pointer}#error{color:#991b1b;white-space:pre-wrap}',encoding='utf-8')
 (target/'src'/'js'/'config.js').write_text('/* ResoArc generic alpha settings / MIT */\n(function(pid){"use strict";const cfg=kintone.plugin.app.getConfig(pid)||{};const area=document.getElementById("rules");const err=document.getElementById("error");area.value=cfg.rules||"[]";document.getElementById("save").addEventListener("click",()=>{err.textContent="";try{const parsed=JSON.parse(area.value);if(!Array.isArray(parsed)||parsed.length<1||parsed.length>30)throw Error("1～30件のルールが必要です");kintone.plugin.app.setConfig({rules:JSON.stringify(parsed)});}catch(e){err.textContent=e.message;}});document.getElementById("cancel").addEventListener("click",()=>history.back());})(kintone.$PLUGIN_ID);\n',encoding='utf-8')
 (target/'README.md').write_text('# '+ja+' v0.1.0-alpha\n\nソースコード・単体試験用の開発α版です。公開配布用の署名ZIPではありません。実機試験完了前に本番アプリへ導入しないでください。\n\nMIT License / ResoArc Open Technology Project.\n',encoding='utf-8')
 print('Scaffolded',target)
