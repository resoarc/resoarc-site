# -*- coding: utf-8 -*-
"""ResoArc mini plugin source builder (stdlib only)."""
from pathlib import Path
import json,zlib,struct,binascii
ROOT=Path(__file__).parent
ITEMS=[
('input-template','入力テンプレート','定型入力を複数フィールドへ一括反映',{'templates':[{'name':'標準','values':{'Title':'サンプル'}}]}),
('reuse-reset','レコード再利用制御','再利用時に指定フィールドを初期化',{'fields':'Date,Status'}),
('text-normalizer','入力文字自動整形','保存時に指定フィールドを自動整形',{'fields':'Title','mode':'NFKC_TRIM'}),
('field-help','フィールド説明表示','項目の補足説明や入力例を表示',{'help':[{'field':'Title','text':'ここに入力例を指定'}]}),
('save-navigation','保存後画面遷移','保存後に一覧や新規登録画面へ移動',{'target':'list'}),
('mail-compose','メール作成ボタン','レコードの項目を差し込んだメールを作成',{'toField':'Email','subject':'{{Title}}','body':'{{Title}}についてご連絡します。'}),
('list-aggregate','一覧合計バー','表示ページの件数・合計・平均を表示',{'field':'Amount'}),
('csv-export','CSVワンクリック出力','一覧を指定フィールドでCSV化',{'fields':'Title,Amount','filename':'resoarc-export.csv'}),
('attachment-count','添付ファイル有無表示','一覧の添付有無と件数を表示',{'field':'Attachment'}),
('table-row-tools','サブテーブル行コピー','サブテーブルの行複製・上下移動',{'field':'Details'}),
('qr-code','QRコード生成','レコードURLや指定項目をQRコードで表示',{'field':'','size':'192'}),
('record-toc','レコード目次','長いレコードの項目にジャンプ',{'fields':'Title,Details'}),
('related-links','関連アプリリンク','レコード項目を埋め込んだ関連リンク',{'label':'関連情報を開く','url':'https://example.com/?q={{Title}}','allowExternal':'false'}),
('sticky-list','一覧表示固定','一覧の見出しと先頭列を固定',{'firstColumn':'true'}),
('file-preview','添付ファイルプレビュー','画像・PDFを画面内で確認',{'field':'Attachment'}),
('lookup-suggest','ルックアップ候補表示','他アプリの候補を入力しながら検索',{'sourceApp':'0','sourceField':'Name','targetField':'CustomerName','runLookup':'false'}),
('postal-address','郵便番号住所入力','郵便番号から住所の入力を補助',{'postalField':'Zip','addressField':'Address'}),
('barcode-scan','バーコード読取','カメラからバーコードを読み取る',{'targetField':'Barcode'}),
]
CONFIG_JS=r'''(function(id){'use strict';
const initial=kintone.plugin.app.getConfig(id)||{};let saved={};try{saved=JSON.parse(initial.ra_settings||'{}')}catch(_){}
const defaults=JSON.parse(document.getElementById('ra-defaults').textContent), root=document.getElementById('ra-fields'),fields={};
for(const [key,def] of Object.entries(defaults)){
 const label=document.createElement('label');label.textContent=key;
 const control=document.createElement(typeof def==='object'?'textarea':'input');
 control.value=typeof(saved[key]??def)==='object'?JSON.stringify(saved[key]??def,null,2):String(saved[key]??def);
 if(control.tagName==='TEXTAREA')control.rows=6;
 label.appendChild(control);root.appendChild(label);fields[key]=control;
}
document.getElementById('ra-save').addEventListener('click',()=>{
 try {const out={};for(const [key,def] of Object.entries(defaults))out[key]=typeof def==='object'?JSON.parse(fields[key].value):fields[key].value;
 kintone.plugin.app.setConfig({ra_settings:JSON.stringify(out)},()=>{document.getElementById('ra-status').textContent='設定を保存しました。アプリを更新してください。'});
 }catch(e){document.getElementById('ra-status').textContent='入力エラー: '+e.message;}
});document.getElementById('ra-back').addEventListener('click',()=>history.back());})(kintone.$PLUGIN_ID);
'''
COMMON=r'''(function(){'use strict';
const stored=kintone.plugin.app.getConfig(kintone.$PLUGIN_ID)||{};
let cfg={};try{cfg=JSON.parse(stored.ra_settings||'{}')}catch(_){}
const defaults=__DEFAULTS__,safeCfg=Object.create(null);if(!cfg||typeof cfg!=='object'||Array.isArray(cfg))cfg={};for(const key of Object.keys(defaults)){safeCfg[key]=Object.prototype.hasOwnProperty.call(cfg,key)?cfg[key]:defaults[key];}cfg=safeCfg;
const on=(events,cb)=>kintone.events.on(events,cb);
const parse=s=>String(s||'').split(',').map(x=>x.trim()).filter(Boolean);
const el=(tag,content)=>{const x=document.createElement(tag);if(content!==undefined)x.textContent=String(content);return x;};
const btn=(label,fn)=>{const x=el('button',label);x.type='button';x.className='ra-mini-button';x.style.cssText='background:#176c68;color:white;border:none;border-radius:5px;padding:7px 11px;margin:3px;cursor:pointer';x.addEventListener('click',fn);return x;};
const panel=()=>{let space=null;try{space=kintone.app.record.getHeaderMenuSpaceElement?.()||kintone.app.getHeaderMenuSpaceElement?.()||kintone.app.getHeaderSpaceElement?.();}catch(_){}if(!space)return null;let x=document.getElementById('ra-mini-'+__SLUG__);if(x){x.replaceChildren();return x;}x=el('div');x.id='ra-mini-'+__SLUG__;x.style.cssText='display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin:8px 0;padding:7px;border:1px solid #bbd8d2;border-radius:6px;background:#f6fbfa;color:#1e4240';space.appendChild(x);return x;};
const cur=()=>{try{return kintone.app.record.get()?.record||null;}catch(_){return null;}};
const val=(r,k)=>r&&typeof k==='string'&&Object.prototype.hasOwnProperty.call(r,k)?r[k]?.value:undefined;
const scalar=x=>x==null?'':Array.isArray(x)?x.map(v=>v==null?'':typeof v==='object'?(v.name||v.code||''):String(v)).join(', '):typeof x==='object'?'':String(x);
const template=(t,r,encode=false)=>String(t??'').replace(/\{\{([A-Za-z0-9_]+)\}\}/g,(_,k)=>encode?encodeURIComponent(scalar(val(r,k))):scalar(val(r,k)));
const set=(r,k,value)=>{if(!r||typeof r!=='object'||typeof k!=='string'||!k||k.length>128||['__proto__','prototype','constructor'].includes(k)||!Object.prototype.hasOwnProperty.call(r,k))return false;const item=r[k];if(!item||['CALC','RECORD_NUMBER','CREATED_TIME','UPDATED_TIME','CREATOR','MODIFIER','STATUS','STATUS_ASSIGNEE','FILE','SUBTABLE','REFERENCE_TABLE','CATEGORY'].includes(item.type))return false;
const arrays=['CHECK_BOX','MULTI_SELECT','USER_SELECT','ORGANIZATION_SELECT','GROUP_SELECT'];
if(arrays.includes(item.type)){
 if(!Array.isArray(value)||value.length>100)return false;
 if(['CHECK_BOX','MULTI_SELECT'].includes(item.type)){
  if(!value.every(x=>typeof x==='string'&&x.length<=1000))return false;
 }else if(!value.every(x=>x&&typeof x==='object'&&!Array.isArray(x)&&
  typeof x.code==='string'&&x.code.length>0&&x.code.length<=128&&
  /^[\p{L}\p{N}_@.\-]+$/u.test(x.code)))return false;
}else{
 if(value!==null&&typeof value==='object')return false;
 if(item.type==='RICH_TEXT')return false;
 if(item.type==='NUMBER'&&value!==null&&value!==''){
  const str=String(value);
  if(!/^-?(?:\d+(?:\.\d+)?|\.\d+)$/.test(str)||str.length>64||!Number.isFinite(Number(str)))return false;
 }
 if(item.type==='DATE'&&value!==null&&value!==''){
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
  const dt=new Date(value+'T00:00:00Z');if(!Number.isFinite(dt.valueOf())||dt.toISOString().slice(0,10)!==value)return false;
 }
 if(item.type==='TIME'&&value!==null&&value!==''){
  if(typeof value!=='string'||!/^([01]\d|2[0-3]):[0-5]\d$/.test(value))return false;
 }
 if(item.type==='DATETIME'&&value!==null&&value!==''){
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:Z|[+-]\d{2}:\d{2})$/.test(value)||!Number.isFinite(Date.parse(value)))return false;
 }
}
item.value=value;return true;};
const apply=r=>{try{kintone.app.record.set({record:r});return true;}catch(err){console.warn('[ResoArc Mini]',err);return false;}};
'''
STYLE='''body{font:14px system-ui,sans-serif;background:#f3f8f6;color:#17363a}main{max-width:800px;margin:auto;background:#fff;padding:28px}h1{margin-top:0}p{line-height:1.65}label{display:block;font-weight:600;margin:15px 0}input,textarea{display:block;box-sizing:border-box;width:100%;font:inherit;margin-top:5px;padding:10px;border:1px solid #9dbcb8;border-radius:6px}button{border:0;border-radius:5px;background:#176c68;color:white;padding:9px 14px;margin-right:7px}#ra-status{color:#ba4c26;white-space:pre-wrap}'''

def icon_bytes(seed):
    w=h=64;raw=b''
    for y in range(h):
        pixels=b''
        for x in range(w):
            rgb=((40+seed*29)%100+50,(60+seed*13)%90+90,(50+seed*21)%100+90) if 12<=x<52 and 12<=y<52 else (24,53,59)
            if 20<x<45 and (24<y<31 or 38<y<44):rgb=(240,247,244)
            pixels+=bytes((*rgb,255))
        raw+=b'\x00'+pixels
    def chunk(tp,data):return struct.pack('!I',len(data))+tp+data+struct.pack('!I',binascii.crc32(tp+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')

def build():
    catalog=[]
    for i,(slug,name,description,defaults) in enumerate(ITEMS):
        target=ROOT/'plugins'/slug
        for d in ('js','html','css','image'):(target/d).mkdir(parents=True,exist_ok=True)
        manifest={'manifest_version':1,'version':'0.1.2','type':'APP','name':{'ja':'ResoArc '+name,'en':'ResoArc '+slug},'description':{'ja':description,'en':description},'icon':'image/icon.png','homepage_url':{'ja':'https://resoarc.com/tools/mini-plugins/','en':'https://resoarc.com/tools/mini-plugins/'},'desktop':{'js':['js/desktop.js']},'config':{'html':'html/config.html','js':['js/config.js'],'css':['css/config.css'],'required_params':['ra_settings']}}
        (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (target/'js/config.js').write_text(CONFIG_JS,encoding='utf-8')
        (target/'css/config.css').write_text(STYLE,encoding='utf-8')
        config='<html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main><h1>ResoArc '+name+'</h1><p>'+description+'。フィールドコードを指定してください。</p><div id="ra-fields"></div><button type="button" id="ra-save">設定を保存</button><button type="button" id="ra-back">戻る</button><div id="ra-status" role="alert"></div><script id="ra-defaults" type="application/json">'+json.dumps(defaults,ensure_ascii=False).replace('<','\\u003c')+'</script></main></body></html>'
        (target/'html/config.html').write_text(config,encoding='utf-8')
        (target/'image/icon.png').write_bytes(icon_bytes(i))
        impl=ROOT/'runtimes'/(slug+'.js')
        (target/'js/desktop.js').write_text(COMMON.replace('__DEFAULTS__',json.dumps(defaults,ensure_ascii=False)).replace('__SLUG__',json.dumps(slug))+(impl.read_text(encoding='utf-8') if impl.exists() else '// NOT IMPLEMENTED\n')+'\n})();\n',encoding='utf-8')
        catalog.append({'slug':slug,'name':name,'description':description,'implemented':impl.exists()})
    (ROOT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Scaffold: %s modules, %s implemented'%(len(catalog),sum(x['implemented'] for x in catalog)))
if __name__=='__main__':build()
