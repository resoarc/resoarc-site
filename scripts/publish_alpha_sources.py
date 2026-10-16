from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import json,html,re
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
reference=(SITE/'tools'/'kintone-conditional'/'index.html').read_text(encoding='utf-8')
header=re.search(r'<header\b.*?</header>',reference,re.S).group()
footer=re.search(r'<footer\b.*?</footer>',reference,re.S).group()
ITEMS=[
 ('conditional-format','条件付き書式','条件に応じてレコード項目の背景色・文字を強調。固定カラーのみ。','[{"source":"risk","target":"amount","operator":"gte","value":"80","theme":"red"}]','通常フィールドが対象です。テーブル内フィールドや非対応フィールドには適用できません。'),
 ('date-calculator','日付・期間計算','開始日・終了日からカレンダー日数と営業日数を算出。休日指定に対応。','[{"start":"start_date","end":"end_date","target":"days","mode":"business","holidays":["2026-10-19"]}]','フォームでDATE型の開始日と終了日から計算し、数値・文字列型の出力先のみを書き換えます。元の日付が消されたら計算結果を空欄に戻します。開始日を含まず終了日を含みます。'),
 ('list-search','高機能検索・絞り込み','現在ページ内検索と、一覧の絞り込み条件を尊重した最大2,000件の範囲検索に対応。','[{"code":"Name","label":"名称","operator":"contains"}]','通常は表示中ページのみ検索。明示的な操作で一覧条件に合う最大2,000件を読み取り検索します。上限を超えたデータは未検索であり、全件検索ではありません。変更APIは使いません。'),
 ('grid-editor','Excel風一覧編集','単一フィールドを最大100件、リビジョン検査付きで一括更新。失敗時は全件取消。','[{"field":"Notes","limit":25}]','現在の一覧ページのみ。通常文字列・複数行文字列・数値フィールドを最大100件まで、更新前にGETで現在値・リビジョンを再確認し、変化がなければ1回の原子的なPUTリクエストで更新します。1件でも失敗すれば全件取消。ネットワーク障害では実際の結果を再読込で確認してください。複数列編集は未実装です。'),
 ('kanban','カード・カンバン表示','現在の一覧ページをグループ化して読み取り専用カードで表示。','[{"groupField":"Status","labelField":"Title","limit":60}]','現在の一覧ページのみ。ドラッグ＆ドロップ更新、全レコード取得は未実装です。'),
]
for slug,title,desc,example,limit in ITEMS:
    pkg=ROOT/'plugins'/slug/'v0.1.0-alpha'
    assert (pkg/'src'/'manifest.json').is_file(),slug
    files=sorted((f for f in pkg.rglob('*') if f.is_file() and f.suffix not in ('.pyc',)),key=lambda f:f.relative_to(pkg).as_posix())
    archive=SITE/'downloads'/('resoarc-'+slug+'-v0.1.0-alpha-source.zip')
    archive.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as zipf:
        for f in files:
            relative=(slug+'-v0.1.0-alpha/'+f.relative_to(pkg).as_posix())
            entry=ZipInfo(relative,date_time=(2026,10,16,0,0,0))
            entry.compress_type=ZIP_DEFLATED
            zipf.writestr(entry,f.read_bytes())
    url='https://resoarc.com/tools/kintone-'+slug+'/'
    head=('<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
      +'<meta name="description" content="'+html.escape(desc,quote=True)+'"><meta name="referrer" content="strict-origin-when-cross-origin">'
      +'<link rel="canonical" href="'+url+'"><link rel="stylesheet" href="/assets/site-20261015-v10.css">'
      +'<link rel="icon" type="image/svg+xml" href="/assets/resoarc-icon.svg"><title>'+html.escape(title)+'（αソース） | ResoArc</title></head><body><a class="skip-link" href="#main">本文へ移動</a>')
    main=('<main id="main"><section class="inside-hero"><div class="container inside-hero-inner"><div class="kicker"><span class="kicker-no">A</span><span class="kicker-en">DEVELOPER PREVIEW</span><span class="kicker-jp">kintoneプラグイン</span></div><h1>'+html.escape(title)+'</h1><p>'+html.escape(desc)+'</p></div></section>'
      +'<section class="section inner-section"><div class="container reading-width"><h2>開発α版・検証用ソース公開</h2><p><strong>この版はkintone実環境への導入試験が完了していません。署名付き評価用ZIPは別ページで公開していますが、運用アプリに導入しないでください。</strong>コード、設定画面、ロジック、単体テストを確認するためのソースパッケージです。</p>'
      +'<p>'+html.escape(limit)+'</p><div class="article-strip"><div><strong>ソース一式・設定例</strong><p>ソースパッケージに、manifest・設定画面・PC/モバイルJS・ビルド手順・テストを収録しています。</p></div>'
      +'<a class="inline-link" href="/downloads/resoarc-'+slug+'-v0.1.0-alpha-source.zip" download>α版ソースZIPを取得 <span>↗</span></a></div>'
      +'<p><strong>設定画面をフォーム化。</strong>JSONを直接編集せず、フィールドコード候補の補完・ルール追加・保存前の形式検証を利用できます。旧JSON設定も引き継ぎます。</p><h3>設定ルール例</h3><pre class="suite-result" style="overflow:auto;background:#17343d;color:white;padding:16px">'+html.escape(example)+'</pre><p>署名付き評価用ZIPは<a href="/products/kintone/qa/">こちら</a>にまとめています。導入前に専用のテストアプリで権限、API動作、他プラグインとの競合を確認してください。</p>'
      +'<p><a href="/products/kintone/">kintoneツール一覧に戻る ↗</a></p></div></section></main>')
    target=SITE/'tools'/('kintone-'+slug)/'index.html'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(head+'\n'+header+'\n'+main+'\n'+footer+'</body></html>\n',encoding='utf-8',newline='\n')
product=SITE/'products'/'kintone'/'index.html'
p=product.read_text(encoding='utf-8')
if 'href="/tools/kintone-date-calculator/"' not in p:
    cards=[]
    for i,(slug,title,desc,example,limit) in enumerate(ITEMS,4):
        cards.append('<article class="product-card"><div class="product-meta"><span>DEVELOPER PREVIEW</span><span>α v0.1</span></div><div class="product-index">'+str(i).zfill(2)+'</div><h2>'+html.escape(title)+'</h2><p>'+html.escape(desc)+'</p><div class="product-tags"><span>ソース公開のみ</span><span>実機未検証</span></div><a class="product-cta" href="/tools/kintone-'+slug+'/">開発版を見る <span aria-hidden="true">↗</span></a></article>')
    marker='<div class="catalog-more">'
    assert marker in p
    p=p.replace(marker,'<div class="product-grid">' + ''.join(cards) + '</div>' + marker,1)
    product.write_text(p,encoding='utf-8',newline='\n')
roadmap=SITE/'products'/'roadmap'/'index.html'
r=roadmap.read_text(encoding='utf-8')
for slug,title,desc,example,limit in ITEMS:
    r,n=re.subn(r'(<th scope="row">'+re.escape(title)+r'</th><td>).*?(</td>)',lambda m:m.group(1)+'開発α版ソース公開／実機未検証'+m.group(2),r,count=1)
    assert n==1,title
roadmap.write_text(r,encoding='utf-8',newline='\n')
sitemap=SITE/'sitemap.xml'
s=sitemap.read_text(encoding='utf-8')
for slug,*_ in ITEMS:
    url='https://resoarc.com/tools/kintone-'+slug+'/'
    if url not in s:s=s.replace('</urlset>','<url><loc>'+url+'</loc></url>\n</urlset>')
sitemap.write_text(s,encoding='utf-8',newline='\n')
history=SITE/'releases'/'index.html'
h=history.read_text(encoding='utf-8')
if 'kintone追加5機能の開発α版' not in h:
    entry='<div class="release-entry"><div><time datetime="2026-10-16">2026.10.16</time><span>KINTONE α</span></div><div><h2>kintone追加5機能の開発α版</h2><p>条件付き書式、日付・期間計算、一覧検索、Excel風編集、カンバン表示のソースと単体テストを公開。実機試験前のため署名ZIPは配布していません。</p><p><a href="/products/kintone/">開発状況を見る</a></p></div></div>'
    h=h.replace('<div class="release-entry">',entry+'<div class="release-entry">',1)
    history.write_text(h,encoding='utf-8',newline='\n')
docs=ROOT/'docs'/'SUITE16_PROGRESS.md'
d=docs.read_text(encoding='utf-8')
d=d.replace('- 他5種類: 継続開発。完成と表示しない。','- 他5種類: 条件付き書式、日付・期間計算、高機能検索、Excel風一覧編集、カンバン表示。開発α版ソース・単体テストを追加。kintone実環境未検証のため安定版扱いしない。')
docs.write_text(d,encoding='utf-8',newline='\n')
wf=ROOT/'.github'/'workflows'/'verify.yml'
w=wf.read_text(encoding='utf-8')
if 'Test five alpha kintone features' not in w:
    pos='      - name: Verify reproducible plugin builds'
    assert pos in w
    checks='      - name: Test five alpha kintone features\n        run: |\n'
    for slug,*_ in ITEMS:checks+='          cd plugins/'+slug+'/v0.1.0-alpha && npm run check && cd ../../..\n'
    w=w.replace(pos,checks+pos,1)
    wf.write_text(w,encoding='utf-8',newline='\n')
print('Generated',len(ITEMS),'kintone alpha source archives and product pages')
