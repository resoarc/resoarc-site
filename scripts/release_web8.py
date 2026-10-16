#!/usr/bin/env python3
"""Prepare public GA metadata for eight read-only browser utilities.

Once published, do not replace v1.0.0 bytes: future modifications use a new version.
This script is deterministic for unchanged checked-in source files.
"""
from pathlib import Path
from hashlib import sha256
import json, zipfile, io
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
ROUTES={
 'kintone-bulk-preview':('一括更新・変更前プレビュー','データへの書き込みは行いません。JSON／CSVのファイル照合のみです。'),
 'kintone-app-diff':('アプリ設定JSON差分比較','設定JSONの構造的差分の表示のみです。実際のkintoneアプリの変更・同期は行いません。'),
 'kintone-permission-audit':('権限定義の可視化','定義を一覧化するだけです。ユーザー・グループに適用される実効権限は判定しません。'),
 'kintone-import-check':('CSV取込前診断','取り込みの成功を保証しません。テーブル行、ルックアップなど未対応の形式があります。'),
 'kintone-duplicates':('重複レコード候補の検出','文字列正規化による候補抽出であり、重複レコードの削除はしません。'),
 'kintone-lookup-audit':('ルックアップ不整合診断','手元の2ファイルを比較する静的診断です。参照関係の自動更新はしません。'),
 'kintone-cross-aggregate':('統合済みCSV／JSON集計','統合済みデータを入力します。異なるkintoneアプリの直接API取得は行いません。'),
 'kintone-print-report':('ブラウザ帳票／PDF保存','PDFはブラウザの印刷機能で保存します。帳票サーバーやPDF生成APIは使いません。'),
}
SOURCES=[
 'site/assets/tools/app-diff.js',
 'site/assets/tools/import-diagnose-core.js',
 'site/assets/tools/import-diagnose-ui.js',
 'site/assets/tools/suite-core.js',
 'site/assets/tools/suite-ui.js',
 'site/assets/tools/suite.css',
 'LICENSE',
 'docs/WEB8_V1_RELEASE.md',
]
SOURCES += ['site/tools/'+route+'/index.html' for route in ROUTES]
RELEASE='resoarc-web8-v1.0.0-source.zip'
def run():
 catalog=SITE/'products/web/index.html'
 html=catalog.read_text(encoding='utf8')
 ga_routes=list(ROUTES)
 for route in ga_routes:
  target='href="/tools/'+route+'/"'
  pos=html.find(target)
  if pos<0:raise ValueError('Missing catalog link '+route)
  # Each catalog card includes one tool path.
  start=html.rfind('<article class="product-card">',0,pos)
  end=html.find('</article>',pos)+len('</article>')
  card=html[start:end]
  card=card.replace('β v0.1.0','v1.0.0').replace('β v0.1','v1.0.0')
  card=card.replace('試験公開','正式公開').replace('β版','正式公開').replace('ブラウザー内 β版','正式公開')
  card=card.replace('試験版を開く','ツールを開く')
  html=html[:start]+card+html[end:]
 first='<div class="kicker"><span class="kicker-no">01</span><span class="kicker-en">AVAILABLE</span>'
 ga_note='<div class="article-strip"><div><strong>ブラウザ専用の診断8機能を v1.0.0 正式公開</strong><p>読み取り専用・ローカル処理の範囲で正式リリースしました。kintoneプラグイン8機能は別途実機受入が必要な評価版です。入力データに対する診断はその結果の完全性やkintoneへの適用成功を保証するものではありません。</p></div><a class="inline-link" href="/downloads/'+RELEASE+'">正式版ソースZIP ↘</a></div>'
 if '正式版ソースZIP' not in html:
  html=html.replace(first,ga_note+first,1)
 catalog.write_text(html,encoding='utf8',newline='\n')
 for route,(name,limits) in ROUTES.items():
  path=SITE/'tools'/route/'index.html'
  content=path.read_text(encoding='utf8')
  if 'data-resoarc-web-ga' not in content:
   note='<section data-resoarc-web-ga="1.0.0" class="section inner-section"><div class="container reading-width"><p><strong>ResoArc Web診断ツール v1.0.0（正式版）</strong>。<span>'+limits+'</span> 入力ファイルはブラウザ内で解析し、サーバーへアップロードしません。<a href="/products/web/">Webツール一覧に戻る</a></p></div></section>'
   content=content.replace('</main>',note+'</main>',1)
  path.write_text(content,encoding='utf8',newline='\n')
 output=SITE/'downloads'/RELEASE
 files=SOURCES[:]
 for f in files:
  if not (ROOT/f).is_file():raise ValueError('Missing file: '+f)
 buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in sorted(files):
   info=zipfile.ZipInfo(name,date_time=(2026,10,16,0,0,0))
   info.compress_type=zipfile.ZIP_DEFLATED
   info.external_attr=0o100644 << 16
   z.writestr(info,(ROOT/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
 packed=buffer.getvalue()
 if output.exists() and output.read_bytes()!=packed:
  raise ValueError('Version v1.0.0 is immutable: source changed. Bump the version instead of overwriting a release.')
 if not output.exists():output.write_bytes(packed)
 digest=sha256(packed).hexdigest()
 (SITE/'downloads'/(RELEASE+'.sha256')).write_text(f'{digest}  {RELEASE}\n',encoding='ascii',newline='\n')
 manifest={'release':'ResoArc Web Diagnostics','version':'1.0.0','date':'2026-10-16',
    'category':'browser-only offline diagnostics','scope':'8 web utilities only',
    'kintonePluginStatus':'NOT_GA - independent kintone tenant acceptance pending',
    'zip':RELEASE,'sha256':digest,
    'tools':[{'path':'/tools/'+slug+'/','name':name,'limitation':limitation} for slug,(name,limitation) in ROUTES.items()],
    'sources':[{'path':p,'sha256':sha256((ROOT/p).read_bytes()).hexdigest()} for p in sorted(files)]}
 (SITE/'downloads/resoarc-web8-v1.0.0-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
 print('WEB8_V1_PACKAGE',output.stat().st_size,'bytes',digest,'files',len(files))
if __name__=='__main__':run()
