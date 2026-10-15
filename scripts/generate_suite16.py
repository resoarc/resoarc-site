from pathlib import Path
import re, json, html
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
source = (SITE/'tools'/'kintone-import-check'/'index.html').read_text(encoding='utf-8')
header = re.search(r'<header\b.*?</header>', source, flags=re.S).group()
footer = re.search(r'<footer\b.*?</footer>', source, flags=re.S).group()
TOOLS = [
('kintone-bulk-preview','bulk-update','一括更新・変更前プレビュー','既存レコードと更新予定データの差分を照合します。書き込みは一切行いません。','更新前のCSV/JSON','更新予定のCSV/JSON',{'keyField':'id'},'照合キーは一意にしてください。値が一致する行のみ変更点を列挙します。','DATA CHANGE'),
('kintone-permission-audit','permission-audit','kintone権限定義の可視化','kintone設定JSONの rights / rules を読み取り、主体・許可操作・条件を一覧化します。','権限設定JSON',None,{},'実効権限の判定ではありません。優先順位、所属グループ、アクセス条件の評価は行いません。','PERMISSIONS'),
('kintone-duplicates','duplicates','重複レコード候補の検出','CSV/JSONの複数項目を正規化比較し、重複候補と元データの行番号を表示します。','レコードCSV/JSON',None,{'fields':['name','email']},'比較するフィールド名を入力データに合わせて変更してください。行の削除・統合はしません。','DATA QUALITY'),
('kintone-lookup-audit','lookup-audit','ルックアップ不整合診断','参照元と参照先をキーで照合し、未一致・参照先キー重複・取得値不整合を検出します。','参照元レコードCSV/JSON','参照先マスタCSV/JSON',{'sourceKey':'code','masterKey':'code','compareFields':{'name':'name'}},'値の再取得や修復は実行しません。比較先のフィールド名を指定してください。','DATA RELATIONS'),
('kintone-cross-aggregate','aggregate','アプリ横断集計','複数アプリから用意した共通形式のCSV/JSONを集計します。統合済みデータを入力します。','統合済みCSV/JSON',None,{'dimension':'department','metric':'amount','operation':'sum'},'集計対象のCSV/JSONを事前に統合してください。kintone APIからの直接取得は未対応です。','ANALYTICS'),
('kintone-print-report','report','ブラウザー帳票・PDF保存','CSV/JSONから印刷用の表を生成し、ブラウザーの印刷機能でPDF保存できます。','帳票用CSV/JSON',None,{'columns':['name','amount'],'title':'ResoArc 帳票'},'帳票はブラウザー内で作成します。PDF保存は印刷ダイアログから行ってください。','DOCUMENTS'),
]
for route, tool, title, desc, primary, secondary, cfg, note, category in TOOLS:
    path = SITE/'tools'/route/'index.html'
    path.parent.mkdir(parents=True,exist_ok=True)
    esc = html.escape
    opts = esc(json.dumps(cfg,ensure_ascii=False,indent=2))
    secondary_html = ('<label for="suite-secondary">2. '+esc(secondary)+'</label><input id="suite-secondary" type="file" accept=".json,.csv,.tsv,text/csv,application/json">' if secondary else '')
    settings_no = '3' if secondary else '2'
    form = ('<div class="suite-panel"><h2>データを指定</h2><p class="suite-note">ファイルはサーバーへ送信されません。最大12 MB。</p>'
       + '<label for="suite-primary">1. '+esc(primary)+'</label><input id="suite-primary" type="file" accept=".json,.csv,.tsv,text/csv,application/json">'
       + secondary_html
       + '<label for="suite-settings">'+settings_no+'. 診断設定（JSON）</label><textarea id="suite-settings" rows="8" spellcheck="false">'+opts+'</textarea>'
       + '<p class="suite-note">'+esc(note)+'</p><button type="button" id="suite-run">診断を実行</button></div>'
    )
    result = ('<div class="suite-panel"><h2>診断結果</h2><p id="suite-state" class="suite-status" role="status" aria-live="polite">ファイルを指定して実行してください。</p><pre id="suite-output" class="suite-result" tabindex="0"></pre>'
        + '<button type="button" id="suite-download" class="suite-outline" hidden>結果をJSON保存</button>'
        + '<button type="button" id="suite-print" class="suite-outline" hidden>印刷・PDF保存</button>'
        + '</div>')
    url='https://resoarc.com/tools/'+route+'/'
    head = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
       + '<meta name="description" content="'+esc(desc,quote=True)+'"><meta name="referrer" content="strict-origin-when-cross-origin">'
       + '<link rel="canonical" href="'+url+'"><link rel="icon" type="image/svg+xml" href="/assets/resoarc-icon.svg">'
       + '<link rel="stylesheet" href="/assets/site-20261015-v10.css"><link rel="stylesheet" href="/assets/tools/suite.css">'
       + '<title>'+esc(title)+' | ResoArc</title></head><body><a class="skip-link" href="#main">本文へ移動</a>')
    main = ('<main id="main" data-resoarc-tool="'+tool+'"><section class="inside-hero"><div class="container inside-hero-inner"><div class="kicker"><span class="kicker-no">B</span><span class="kicker-en">'+category+'</span><span class="kicker-jp">Webツール</span></div>'
       + '<h1>'+esc(title)+'</h1><p>'+esc(desc)+'</p></div></section>'
       + '<section class="section inner-section"><div class="container"><p class="catalog-lede"><strong>ブラウザー内 β版</strong>：ファイルの解析・表示のみ。kintoneにログインせず、更新APIも呼び出しません。</p>'
       + '<div class="suite-layout">'+form+result+'</div><section id="suite-preview" class="suite-preview" aria-label="印刷プレビュー" hidden></section>'
       + '<div class="suite-guide article-strip"><div><strong>扱うデータの注意</strong><p>サンプルデータで先に検証してください。各ツールの判定結果は、kintone上の操作や業務承認を代替しません。CSVの文字コードはUTF-8を推奨します。</p>'
       + '<p><a href="/assets/tools/suite-core.js" rel="noopener noreferrer">解析処理のソースコードを見る ↗</a></p></div>'
       + '<a class="inline-link" href="/products/web/">Webツール一覧に戻る <span>↗</span></a></div></div></section></main>')
    scripts='<script src="/assets/tools/suite-core.js" defer></script><script src="/assets/tools/suite-ui.js" defer></script>'
    path.write_text(head+'\n'+header+'\n'+main+'\n'+footer+'\n'+scripts+'</body></html>\n',encoding='utf-8',newline='\n')
catalog = SITE/'products'/'web'/'index.html'
c = catalog.read_text(encoding='utf-8')
if 'href="/tools/kintone-duplicates/"' not in c:
    cards = []
    for i,(route,tool,title,desc,primary,secondary,cfg,note,category) in enumerate(TOOLS,5):
        cards.append('<article class="product-card"><div class="product-meta"><span>'+category+'</span><span>β v0.1</span></div><div class="product-index">'+str(i).zfill(2)+'</div><h2>'+html.escape(title)+'</h2><p>'+html.escape(desc)+'</p><div class="product-tags"><span>ブラウザー内 β版</span><span>読み取り専用</span></div><a class="product-cta" href="/tools/'+route+'/">ツールを開く <span aria-hidden="true">↗</span></a></article>')
    marker='<div class="catalog-more">'
    assert marker in c
    c=c.replace(marker,'</div><div class="product-grid">' + ''.join(cards) + '</div>' + marker,1)
    # Fix extraneous closed grid only if earlier grid ended exactly before catalog more
    c=c.replace('</div></div><div class="product-grid">','</div><div class="product-grid">',1)
    catalog.write_text(c,encoding='utf-8',newline='\n')
roadmap = SITE/'products'/'roadmap'/'index.html'
r = roadmap.read_text(encoding='utf-8')
for title in ('安全な一括更新＋変更前確認','権限設定の可視化・監査','重複レコード検出・統合支援','ルックアップ不整合の検出・修復','アプリ横断集計・ダッシュボード','帳票テンプレート＋ブラウザー内PDF生成'):
    r,n=re.subn(r'(<th scope="row">'+re.escape(title)+r'</th><td>).*?(</td>)',lambda m:m.group(1)+'ブラウザー内診断β版公開／kintoneへの変更機能は未実装'+m.group(2),r,count=1)
    assert n==1,title
roadmap.write_text(r,encoding='utf-8',newline='\n')
sitemap=SITE/'sitemap.xml'
s=sitemap.read_text(encoding='utf-8')
for route,*_ in TOOLS:
    url='https://resoarc.com/tools/'+route+'/'
    if url not in s:s=s.replace('</urlset>','<url><loc>'+url+'</loc></url>\n</urlset>')
sitemap.write_text(s,encoding='utf-8',newline='\n')
wf=ROOT/'.github'/'workflows'/'verify.yml'
w=wf.read_text(encoding='utf-8')
if 'node --test tests/suite.test.cjs' not in w:
    marker='      - name: Test kintone CSV import preflight'
    assert marker in w
    w=w.replace(marker,'      - name: Test ResoArc local-only suite\n        run: |\n          node --check site/assets/tools/suite-core.js\n          node --check site/assets/tools/suite-ui.js\n          node --test tests/suite.test.cjs\n'+marker)
    wf.write_text(w,encoding='utf-8',newline='\n')
changelog = SITE/'releases'/'index.html'
cl = changelog.read_text(encoding='utf-8')
if 'ResoArc Web解析ツール6種類' not in cl:
    release = '<div class="release-entry"><div><time datetime="2026-10-16">2026.10.16</time><span>WEB β v0.1</span></div><div><h2>ResoArc Web解析ツール6種類</h2><p>一括更新の差分プレビュー、権限定義の可視化、重複候補、ルックアップ不整合、集計、帳票/PDF印刷のブラウザー内β版を追加しました。変更APIの実行は行いません。kintone実機連携や自動修復は未実装です。</p><p><a href="/products/web/">Webツール一覧はこちら</a></p></div></div>'
    assert '<div class="release-entry">' in cl
    cl = cl.replace('<div class="release-entry">',release+'<div class="release-entry">',1)
    changelog.write_text(cl,encoding='utf-8',newline=None)
doc=ROOT/'docs'/'SUITE16_PROGRESS.md'
doc.write_text('''# ResoArc 16機能開発状況（2026-10-16）

## 分類と提供範囲
- kintone 8種類: 自動採番、タブ表示、条件付き表示・必須制御、条件付き書式、高機能検索・絞り込み、日付・期間計算、Excel風一覧編集、カード・カンバン表示。
- Web 8種類: 一括更新変更前確認、アプリ設定差分比較、権限定義監査、CSV取込前診断、重複候補検出、ルックアップ不整合診断、アプリ横断集計、ブラウザー帳票/PDF。

## Web 8種類
- 既存: アプリ設定差分比較β、CSV取込前診断β。
- 新規: 一括更新プレビュー、権限定義の可視化、重複候補、ルックアップ診断、統合済データの集計、帳票/ブラウザーPDF。6種はいずれもオフライン解析β版。
- 制約: kintoneへのログイン、変更APIの実行、実効権限の判定、各アプリの自動収集、Excel(.xlsx)読込、ルックアップ修復、一括更新、グラフ描画は未実装。
- 安全: ローカルで処理し、ファイルをサーバーに送らない。帳票はHTMLをエスケープする。

## kintone 8種類
- 自動採番: 通常フィールド版を配布済み。テーブル対応β版は開発済み、実機未検証。
- タブ表示: β版配布済み。実機未検証。
- 条件付き表示・必須制御: α版ソース公開、実機未検証。
- 他5種類: 継続開発。完成と表示しない。

## 受け入れ基準
各機能の単体試験に加え、kintone実機テスト、権限・モバイル・テーブル・競合プラグイン確認、ZIP署名とサンプル導入の検証を実施後に安定版とする。
''',encoding='utf-8',newline='\n')
print('Generated suite pages:',len(TOOLS),'plus catalog/roadmap/sitemap/CI/status')
