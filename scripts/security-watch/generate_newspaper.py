#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc contributors
# SPDX-License-Identifier: MIT
"""Render an attractive, fully static, Japanese four-page SWWW newspaper.

Only quality-approved, allowlisted public records are accepted.
It is an editorial digest, NOT a replacement for vendor advisories.
"""
from __future__ import annotations
import argparse,collections,datetime as dt,html,json,pathlib,re,sys,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE="/security/weather/newspaper/"
SECTIONS=(
 ("index.html","1面","本日のトップ"),
 ("ranking/index.html","2面","注目ランキング"),
 ("technologies/index.html","3面","技術別の動向"),
 ("action/index.html","4面","今日の対策"),
)
# Manually reviewed Japanese headlines and careful summaries. New advisories not
# reviewed by editors fall back to generic headings, never model-made fixes.
EDITORIAL={
"GHSA-2464-fhr4-w9xw":{
 "head":"Next.js画像処理に重大な問題。SVG経由の遠隔コード実行に注意",
 "blurb":"Next.jsの画像最適化機能で、特定のLinux環境と依存ライブラリの組み合わせにより遠隔コード実行につながる可能性が報告されました。すべてのNext.jsサイトが影響を受けるわけではありません。",
 "check":"Next.js 15系は15.5.28以降、16系は16.4.1以降を確認。関連するsharpのバージョンも確認。",
 "type":"Webフレームワーク","audience":"Next.jsを運用する人","tag":"Next.js / SVG"},
"GHSA-673q-mjm6-r5xr":{
 "head":"Next.js「use cache」に別の重大欠陥。特定の戻り値が条件",
 "blurb":"App RouterのCache Componentsで、複数の型付き配列を返す「use cache」関数がある場合、遠隔コード実行につながり得る問題です。提供元は16.4.1への更新を案内しています。",
 "check":"Next.js 16.0.0〜16.4.0の利用有無を確認し、16.4.1以降への更新を検討。",
 "type":"Webフレームワーク","audience":"Next.js 16系の開発者","tag":"Next.js / Cache"},
"GHSA-v9pv-5gc8-w2m6":{
 "head":"画像ファイルがサーバーの問題に。Pillowの複数フレーム処理",
 "blurb":"画像処理ライブラリPillowで、複数フレームの画像を読み込む際にメモリ破壊が起こる問題です。特定の実行環境でコード実行を示す検証も報告されています。",
 "check":"Pillow 11.0.0〜12.3.0の利用と、外部画像を自動処理する機能の有無を確認。修正版13.0.0を確認。",
 "type":"画像処理","audience":"画像アップロードを扱う人","tag":"Pillow / Python"},
"GHSA-pxh4-856f-4h89":{
 "head":"ログイン用トークンの信頼が揺らぐ。PyJWTの鍵設定に盲点",
 "blurb":"JWK方式で空のHMAC鍵を受け入れると、条件次第で偽造トークンの検証が通る可能性があります。一般的なJWTすべてが破られるという意味ではありません。",
 "check":"PyJWT 2.13.0以前かを確認。JWK/JWKSの鍵設定と2.14.0以降への更新を確認。",
 "type":"認証・API","audience":"API認証の担当者","tag":"PyJWT / 認証"},
"GHSA-p3m5-59mp-jv5r":{
 "head":"Next.jsのServer Actionsに負荷攻撃の問題",
 "blurb":"App RouterでServer Actionsを使う構成は、細工されたリクエストによりCPU負荷が高くなり、サービス停止につながる可能性があります。",
 "check":"Server Actionsの利用有無を確認。15系15.5.28、16系16.4.1以降などを参照。",
 "type":"Webフレームワーク","audience":"Next.js運用者","tag":"Next.js / DoS"},
"GHSA-33wh-fxxf-88vv":{
 "head":"APIへの「Accept」ヘッダーだけでCPU消費。DRFに注意",
 "blurb":"Django REST frameworkのコンテンツ交渉処理で、非常に大きなAcceptヘッダーがCPUを長時間消費させる可能性があります。",
 "check":"Django REST frameworkの利用バージョンを確認。公式リリースノートの3.18.2の修正を参照。",
 "type":"API・Web","audience":"Django API開発者","tag":"Python / DRF"},
"GHSA-354v-3q48-cv69":{
 "head":"Jupyter Serverで実行権限の境界に問題",
 "blurb":"Gateway WebSocketハンドラーで、カーネル実行の認可をすり抜ける問題が報告されています。該当構成の利用者は運用と更新情報を確認してください。",
 "check":"Jupyter ServerのGateway機能の使用有無、アクセス経路と修正版の有無を元情報で確認。",
 "type":"開発基盤","audience":"Notebook環境の管理者","tag":"Jupyter"},
"GHSA-78g4-xqwv-q3g8":{
 "head":"OSを更新しても残る画像ライブラリの問題",
 "blurb":"Pillowの配布パッケージに含まれる画像処理コンポーネントが問題になる事例。OSだけを更新しても、アプリ側の同梱ライブラリは別管理の場合があります。",
 "check":"Pillowのインストール形態と同梱ライブラリを確認。公式アドバイザリーの修正版を参照。",
 "type":"画像処理","audience":"画像変換・OCR担当者","tag":"Pillow / OpenJPEG"},
"GHSA-83vg-56qc-22m7":{
 "head":"GitPythonのサブモジュール取得時にパス検証の盲点",
 "blurb":"サブモジュールをcloneした後に特殊なパスを検証する挙動が、コード実行につながる可能性として報告されています。",
 "check":"GitPythonを使う自動化、特に外部リポジトリのサブモジュールを処理する箇所を確認。",
 "type":"開発基盤","audience":"CI/CD担当者","tag":"GitPython"},
"GHSA-3547-9m27-7rxg":{
 "head":"Django REST frameworkのJSON解釈でも入力処理に注意",
 "blurb":"JSONParserがリクエスト側で指定された文字エンコーディングを処理する仕組みに問題があり、入力処理の悪用が指摘されています。",
 "check":"DRF 3.18.2のセキュリティ修正と利用構成を確認。",
 "type":"API・Web","audience":"Django API開発者","tag":"Python / DRF"},
"GHSA-cg2g-xh64-v4q7":{
 "head":"DOMPurifyの重大度表記に不一致。数字の読み違いに注意",
 "blurb":"SWWWに取り込まれた重大度はCRITICALですが、提供元の個別アドバイザリーではLOWの表記も確認されています。条件付きの問題であり、編集部は順位付けから除外して再確認を促します。",
 "check":"対象機能SAFE_FOR_TEMPLATESとDOM出力モードの併用有無、配布元の最新情報を確認。",
 "type":"データ品質","audience":"Web開発者","tag":"DOMPurify / 注記"},
"GHSA-mchm-gjx6-7h55":{
 "head":"Sentryの重大度表記にも差異。提供元に戻って確認",
 "blurb":"統合集計はCRITICALですが、提供元プロジェクトの案内ではModerate表記が確認されています。編集部では無条件に重大とみなさず、原文への確認を優先します。",
 "check":"Sentryの該当SDK、トンネル設定、公式アドバイザリーの最新重大度を確認。",
 "type":"データ品質","audience":"監視基盤担当者","tag":"Sentry / 注記"},
}
PRIORITY_IDS=[
 "GHSA-2464-fhr4-w9xw","GHSA-673q-mjm6-r5xr","GHSA-v9pv-5gc8-w2m6",
 "GHSA-pxh4-856f-4h89","GHSA-p3m5-59mp-jv5r","GHSA-33wh-fxxf-88vv",
 "GHSA-354v-3q48-cv69","GHSA-78g4-xqwv-q3g8",
]
ISSUES={"GHSA-cg2g-xh64-v4q7":"提供元がLOWと記載","GHSA-mchm-gjx6-7h55":"提供元の案内がModerate"}
COLLECTION_TEXT="「今日」はSWWWのDBに記録された掲載日で、脆弱性が今日初公開されたことを意味しません。"

def e(x):return html.escape(str(x if x is not None else ""),quote=True)
def format_date(s):
    d=dt.date.fromisoformat(s)
    return f"{d.year}年{d.month}月{d.day}日（{'月火水木金土日'[d.weekday()]}）"
def safe_url(u):
    u=str(u or "").strip()
    return u if u.startswith(("https://github.com/","https://nvd.nist.gov/","https://www.django-rest-framework.org/")) else "#"
def anchor(row,label="原文を確認 ↗"):
    return f'<a class="press-link" target="_blank" rel="noopener noreferrer" href="{e(safe_url(row["url"]))}">{e(label)}</a>'
def fact(row):
    return EDITORIAL.get(row["id"],{
      "head":"【"+e(row.get("source","公開情報"))+"】セキュリティ情報を確認",
      "blurb":"原文で影響製品、条件、対応可能なバージョンを確認してください。SWWWの自動集計だけで影響を判断しないことが重要です。",
      "check":"まず製品・バージョン・利用機能の一致を確認してください。",
      "type":"公開アドバイザリー","audience":"製品利用者",
      "tag":(row.get("technologies") or [{"label":"要分類"}])[0]["label"]
    })
def label(row):
    sev=row["severity"]
    return '<span class="pill '+('critical' if sev=="CRITICAL" else 'high')+'">'+e(sev)+'</span>'
def tag(x):return '<span class="pill tech">'+e(x)+'</span>'
def nav(selected,base=BASE):
    labels=["1面 主要記事","2面 注目順位","3面 技術・製品","4面 実用ガイド"]
    result=[]
    for i,(rel,_,_) in enumerate(SECTIONS):
      dest=base+("" if rel=="index.html" else rel.replace("index.html",""))
      result.append(f'<a href="{e(dest)}"'+(' aria-current="page"' if i==selected else '')+'>'+labels[i]+'</a>')
    return '<nav class="edition-nav" aria-label="紙面を選ぶ">'+''.join(result)+'</nav>'
def page_shell(page_i,inner,data):
    meta=data["metadata"]
    date=format_date(meta["date"])
    title=SECTIONS[page_i][2]+" | SWWW 脆弱性朝刊 | "+date
    header=f'''<section class="paper" aria-label="{e(SECTIONS[page_i][1])}">
<div class="flag"><span>ResoArc • Security Weather Watch Web</span><span>安全な情報を、わかる言葉で。</span></div>
<header class="masthead"><span class="sigil" aria-hidden="true">✶</span>
<div><h1>脆弱性朝刊</h1><small>The Security Morning Paper</small></div></header>
<div class="double-rule"></div>
<div class="folio"><span>{e(date)}　｜　第001号　｜　{SECTIONS[page_i][1]}</span><span>品質検証済み・取得 {e(dt.datetime.fromisoformat(meta["generated_at"]).strftime("%H:%M"))} JST / {e(meta["source_count"])}情報源</span></div>
{nav(page_i)}'''
    next_i=(page_i+1)%4
    next_url=BASE+("" if next_i==0 else SECTIONS[next_i][0].replace("index.html",""))
    footer=f'''<footer class="edition-footer">
<div><p>発行：ResoArc SWWW 編集部　｜　{e(meta["date"])} 朝刊</p>
<p>公開情報をわかりやすく整理した編集版。影響の確定・被害数・修正の保証を意味しません。</p></div>
<div class="page-turn"><a href="{BASE}all/">4面をまとめて読む・印刷</a><a class="next" href="{e(next_url)}">次の紙面 →</a></div></footer>
<div class="footnote">【集計について】{COLLECTION_TEXT} 各社の公式文書が優先されます。収集品質がPARTIALの後続データは正式な朝刊へ組み込んでいません。企業への攻撃件数を数えたものではありません。</div>
</section>'''
    return header+inner+footer

def top_story(rows,meta):
    byid={x["id"]:x for x in rows}
    key=byid["GHSA-2464-fhr4-w9xw"];other=byid["GHSA-673q-mjm6-r5xr"]
    n=len(rows);crit=sum(x["severity"]=="CRITICAL" for x in rows);high=sum(x["severity"]=="HIGH" for x in rows)
    cards=[]
    for keyid,tagword in [("GHSA-v9pv-5gc8-w2m6","画像の話"),("GHSA-pxh4-856f-4h89","認証の話"),("GHSA-cg2g-xh64-v4q7","情報の読み方")]:
        r=byid[keyid];f=fact(r)
        cards.append(f'''<article class="teaser"><span class="story-kicker">{e(tagword)}</span>
<h3>{e(f["head"])}</h3><p>{e(f["blurb"])}</p>{tag(f["tag"])}{anchor(r,"記事の根拠 ↗")}</article>''')
    return f'''
<div class="eyebrow">TOP STORY / 5分で読む今日の3大ニュース</div>
<div class="lead-grid">
<article class="lead-story">
<div class="story-kicker">WEB / CRITICAL / 修正版あり</div>
<h2 class="lead-title">画像1枚から、<br><span class="punch">サーバーの奥へ。</span><br>Next.jsに2つの警報</h2>
<p class="deck">Webサイトの“見た目”を支える画像処理。いつものキャッシュ処理。身近な機能に、遠隔コード実行につながる問題が見つかっています。</p>
<p>Next.jsの<a href="{e(safe_url(key["url"]))}" target="_blank" rel="noopener noreferrer">画像最適化機能</a>と、別の<a href="{e(safe_url(other["url"]))}" target="_blank" rel="noopener noreferrer">「use cache」機能</a>にそれぞれ重大な脆弱性が報告されています。影響には実行環境や利用機能などの条件があります。<strong>すべてのNext.jsサイトが直ちに侵害される、という意味ではありません。</strong></p>
<p>開発・運用担当者は、使っている版と該当機能を確認してください。公式情報ではNext.js <strong>15.5.28 / 16.4.1</strong>などの修正版が案内されています。</p>
<div class="byline">出典：GitHub Security Advisories / {anchor(key,"画像処理の公式情報 ↗")}　{anchor(other,"キャッシュの公式情報 ↗")}</div>
</article>
<aside class="metabox">
<h2>本日の紙面を数字で読む</h2>
<div class="metric"><span>掲載日が本日の情報</span><strong>{n}</strong></div>
<div class="metric"><span>集計上 CRITICAL</span><strong>{crit}</strong></div>
<div class="metric"><span>集計上 HIGH</span><strong>{high}</strong></div>
<div class="metric"><span>取得した情報源</span><strong>{meta["source_count"]}</strong></div>
<p class="note">※重大度はSWWW収録値。一部は提供元の表記と差異があり、編集部が注記しています。感染・侵害の件数ではありません。</p>
</aside></div>
<div class="visual" role="img" aria-label="ResoArcの宇宙モチーフを使った抽象的な宇宙のイラスト。実際の被害や攻撃を表す図ではありません">
<div><strong>大量の警報から、<br>本当に読むべき数本へ。</strong><small>LESS NOISE · MORE CONTEXT</small></div><span class="orb" aria-hidden="true"></span></div>
<hr class="break">
<h2 class="sectitle">本日の3本 <small>EDITOR'S PICK</small></h2>
<div class="story-columns">{''.join(cards)}</div>
<div class="ed-note"><strong>編集部から：数だけで焦らない。</strong>
<p>5件の「CRITICAL」が表示されても、5社が攻撃を受けたという意味ではありません。情報を公開した日、修正した日、SWWWが収録した日を分けて考えることが、最初の防御です。</p></div>
<div class="bottomrail"><div class="quote">まず「自分の環境で使っているか」。<br>対策の出発点は、そこから。</div><div class="small"><b>この新聞の読み方</b><br>2面では注目順位、3面では技術・製品ごとの動向、4面では確認・更新の順番を紹介します。ランキングは編集部の読む順番であり、攻撃発生確率の順位ではありません。</div></div>
'''

def ranking(rows):
    byid={x["id"]:x for x in rows}
    entries=[]
    for i,id_ in enumerate(PRIORITY_IDS,1):
        r=byid[id_];f=fact(r)
        entries.append(f'''<article class="rank" id="rank-{i}">
<div class="num">{i:02d}</div>
<div><h3>{e(f["head"])}</h3><p>{e(f["blurb"])}</p>
{label(r)}{tag(f["tag"])}<br>{anchor(r)}</div>
<aside class="rank-side"><b>確認すること</b>{e(f["check"])}
<p>対象：{e(f["audience"])}</p></aside></article>''')
    return f'''
<div class="section-head"><h2>今日、読むべき8件。</h2><span>2面　注目ランキング</span></div>
<p class="deck">31本を全部追う必要はありません。まずは、よく使われる技術・影響の大きさ・対策の明確さを軸に、編集部が8件に絞りました。</p>
<div class="census"><div><strong>8本</strong><small>編集部の注目記事</small></div><div><strong>31件</strong><small>本日掲載扱いの情報</small></div><div><strong>{len(rows)}件</strong><small>ResoArcへの影響未判定</small></div></div>
<div class="ed-note"><strong>この順位は「危険度世界ランキング」ではありません。</strong><p>各製品の利用状況が分からないため、採用している技術で優先順位は変わります。既知の悪用件数、被害者数、会社への影響を推測して順位付けしていません。</p></div>
<div class="rank-list">{''.join(entries)}</div>
<div class="article"><h3>集計の重大度と、発行元の重大度が違うことも</h3>
<p>DOMPurify（{e('GHSA-cg2g-xh64-v4q7')}）とSentry（{e('GHSA-mchm-gjx6-7h55')}）は、収集時の重大度と提供元の評価に差が見られます。どちらも本日の収録データでは「CRITICAL」ですが、<strong>このランキングからは一旦除外</strong>し、出典の最新版の確認を推奨します。</p>
<p><a href="https://github.com/cure53/DOMPurify/security/advisories/GHSA-cg2g-xh64-v4q7" target="_blank" rel="noopener noreferrer">DOMPurify発行元 ↗</a>　/　<a href="https://github.com/getsentry/sentry-javascript/security" target="_blank" rel="noopener noreferrer">Sentry発行元 ↗</a></p></div>
'''

def tech_page(rows,tags,meta):
    daygroups=[
      ("画像処理","Pillow",sum("Pillow:" in r["title"] for r in rows),
       "画像を開く・変換する機能で複数の注意情報。アップロード、サムネイル、画像解析も確認対象。"),
      ("Webフレームワーク","Next.js",sum("Next.js:" in r["title"] for r in rows),
       "画像最適化・キャッシュ・Server Actionsに注意情報。利用機能の条件を原文で確認。"),
      ("API開発","Django REST framework",sum("Django REST framework:" in r["title"] for r in rows),
       "Acceptヘッダー、JSONパーサー、認証トークンの削除処理など。"),
      ("JavaScriptツール","toml-node",sum("toml-node:" in r["title"] for r in rows),
       "設定ファイルの解析でCPUの浪費やプロトタイプ汚染などが報告。"),
    ]
    column=''.join(f'''<article class="tech-feature"><span class="eyebrow">{e(cat)} / 本日収録 {count}件</span>
<h3>{e(name)}</h3><p>{e(desc)}</p></article>''' for cat,name,count,desc in daygroups)
    bars=[]
    show_ids={"oracle","java","python","php","linux","wordpress","chrome","nodejs"}
    selected=[t for t in tags if t["id"] in show_ids]
    selected.sort(key=lambda t:-t["count"])
    mx=max(t["count"] for t in selected)
    for t in selected:
        w=round(100*t["count"]/mx)
        w=max(5,min(100,5*round(w/5)))
        href="https://resoarc.com/api/v1/swww/advisories?technology="+urllib.parse.quote(t["id"])
        bars.append(f'''<div class="barrow"><a href="{href}" title="{e(t["label"])}の記事を検索">{e(t["label"])}</a>
<div class="bar" aria-hidden="true"><i class="w{w}"></i></div><b>{t["count"]:,}</b></div>''')
    return f'''
<div class="section-head"><h2>「何の技術？」から読む。</h2><span>3面　技術・製品面</span></div>
<p class="deck">脆弱性の番号より、毎日触れている技術の名前から探す方がずっと簡単。今日の「目立った分野」と、蓄積データの傾向を分けてみました。</p>
<div class="tech-grid"><section><h2 class="sectitle">本日のよく出る名前 <small>TODAY</small></h2>{column}</section>
<section><h2 class="sectitle">蓄積データのタグ件数 <small>ARCHIVE</small></h2>
<p class="note">PostgreSQLに保存された、最新の品質合格日報に含まれるアドバイザリーから技術名を抽出した件数。同じ記事に複数タグが付くため合計は全件数と一致しません。</p>
<div class="barlist">{''.join(bars)}</div>
<p class="data-key">棒が長い＝危険という意味ではありません。OracleやJavaの情報が多くても、SWWWは利用環境の有無を把握していません。検索結果の件数も被害件数ではありません。</p>
</section></div>
<hr class="break">
<h2 class="sectitle">自分向けの記事にたどり着く</h2>
<div class="story-columns">
<article class="teaser"><span class="story-kicker">Java / Oracle</span><h3>今日の見出しに無くても、安全とは限らない</h3><p>OracleやJavaは蓄積アーカイブから検索可能です。使っている製品・版を確認してから、該当するアドバイザリーだけを追います。</p><a href="https://resoarc.com/api/v1/swww/advisories?technology=oracle">Oracleの一覧 ↗</a>　<a href="https://resoarc.com/api/v1/swww/advisories?technology=java">Javaの一覧 ↗</a></article>
<article class="teaser"><span class="story-kicker">Python / PHP</span><h3>サーバーの裏側にも目を向ける</h3><p>画像処理や認証ライブラリは、画面に見えなくても使われていることがあります。依存関係を棚卸しして検索すると見落としが減ります。</p><a href="https://resoarc.com/api/v1/swww/advisories?technology=python">Pythonの一覧 ↗</a>　<a href="https://resoarc.com/api/v1/swww/advisories?technology=php">PHPの一覧 ↗</a></article>
<article class="teaser"><span class="story-kicker">Web / CMS</span><h3>使用していない技術のニュースは後回しに</h3><p>WordPressを使わない運用環境でWordPressの警報がたくさん出ても、その製品が直ちに問題になるわけではありません。「使っているか」を一番のフィルターに。</p><a href="https://resoarc.com/api/v1/swww/technologies">タグ一覧 ↗</a></article></div>
'''

def action_page(rows,meta):
    return f'''
<div class="section-head"><h2>読んだあと、どうする？</h2><span>4面　実用ガイド</span></div>
<p class="deck">脆弱性情報は、ただ怖がるためのものではありません。今日の31件を受け取っても、いきなり31回更新作業をする必要はありません。</p>
<div class="actiongrid">
<section><h2 class="sectitle">今日の確認は、この順番で</h2>
<ol class="checklist">
<li><b>自分たちが使う製品を数える</b><p>Next.js、Pillow、Django REST framework、PyJWTなど。まず依存ライブラリ一覧やSBOMで確認します。</p></li>
<li><b>「影響する版」と「使う機能」を照合する</b><p>Next.jsなら画像最適化や「use cache」、Pillowなら複数フレーム画像の処理。条件が違えば対応優先度も変わります。</p></li>
<li><b>提供元の修正版・回避策を読む</b><p>最新版にすれば必ず安全、とは限りません。該当版、互換性、既知の回避策を確認します。</p></li>
<li><b>検証環境で動作を確かめてから反映する</b><p>更新による停止や依存関係の変化に備えて、テストと切り戻し手順を準備します。</p></li>
<li><b>対応した記録を残す</b><p>対象外と判断した理由も含め、日付・版・根拠・テスト結果を残すと次の速報で慌てません。</p></li>
</ol></section>
<aside><article class="article"><span class="eyebrow">今日の具体例</span>
<h3>Next.jsを使うなら</h3><p>画像最適化と「use cache」に関する2件の重大情報を確認。公式アドバイザリーには15.5.28、16.4.1などの修正版が示されています。ただし該当条件はそれぞれ異なります。</p>
<a href="https://github.com/advisories/GHSA-2464-fhr4-w9xw" target="_blank" rel="noopener noreferrer">画像処理の情報 ↗</a>　<a href="https://github.com/advisories/GHSA-673q-mjm6-r5xr" target="_blank" rel="noopener noreferrer">キャッシュの情報 ↗</a>
</article><article class="article"><span class="eyebrow">今日の具体例</span>
<h3>Pillowを使うなら</h3><p>外部から届く画像の自動読み込み経路がないか確認。複数フレーム画像の問題では修正版13.0.0が案内されています。OS更新だけで解決しない同梱ライブラリの問題もあります。</p>
<a href="https://github.com/advisories/GHSA-v9pv-5gc8-w2m6" target="_blank" rel="noopener noreferrer">公式アドバイザリー ↗</a>
</article><article class="article"><span class="eyebrow">今日の具体例</span>
<h3>API認証にPyJWTを使うなら</h3><p>JWK/JWKSで空の鍵を許していないか、利用バージョンとともに確認。修正版2.14.0が公表されています。</p>
<a href="https://github.com/advisories/GHSA-pxh4-856f-4h89" target="_blank" rel="noopener noreferrer">公式アドバイザリー ↗</a>
</article></aside></div>
<hr class="break">
<h2 class="sectitle">ニュースを正しく読むための小辞典</h2>
<div class="story-columns">
<article class="teaser"><h3>CRITICAL / HIGH</h3><p>脆弱性そのものの技術的な深刻さの指標です。あなたの会社がすでに被害を受けた証拠ではありません。</p></article>
<article class="teaser"><h3>EPSS / KEV</h3><p>EPSSは悪用の予測確率、KEVはCISAが実際の悪用を確認した脆弱性のリスト。未掲載や未収集を「悪用なし」と判断しないことが大切です。</p></article>
<article class="teaser"><h3>ResoArcへの影響</h3><p>現時点でSWWWに掲載された情報から、ResoArcの採用製品との照合が済んでいるわけではありません。「未判定」は「影響なし」ではありません。</p></article>
</div>
<div class="ed-note"><strong>最後に、今夜のひと言。</strong><p>「31件を読む」のではなく、「自分に関係する3件を見つける」。そのための新聞です。明日も情報は増えますが、読むべきものは必ずしも増えません。</p></div>
<ul class="source-list">
<li><a href="/security/weather/">SWWW 通常の脆弱性天気予報</a>：全体の数値、検索、技術タグ</li>
<li><a href="https://resoarc.com/api/v1/swww/">SWWW 公開API・XML/RSS</a>：機械向けの提供情報</li>
<li><a href="https://github.com/advisories" target="_blank" rel="noopener noreferrer">GitHub Advisory Database</a>：今回の個別記事の出典</li>
<li><a href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog" target="_blank" rel="noopener noreferrer">CISA KEV</a>：既知の悪用が確認された脆弱性</li></ul>
'''

def document(page_i,body,meta):
    title=SECTIONS[page_i][2]+" | SWWW 脆弱性朝刊 | "+format_date(meta["date"])
    description="SWWWが公表情報を整理した日本語の脆弱性新聞。31件の情報を要約、注目順位、製品別動向、取るべき対応を4面で紹介。"
    return f'''<!doctype html><!--
SPDX-FileCopyrightText: 2026 ResoArc contributors
SPDX-License-Identifier: MIT
-->
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="description" content="{e(description)}">
<meta name="robots" content="noindex,follow">
<title>{e(title)}</title>
<link rel="stylesheet" href="/assets/swww-newspaper.css">
<link rel="alternate" type="application/rss+xml" title="SWWW脆弱性情報RSS" href="/api/v1/swww/rss.xml">
</head><body><a class="skip" href="#content">本文へ</a>
<div class="portal"><div class="portal-inner"><a class="logo" href="/">ResoArc</a>
<span class="edition">SWWW / SECURITY WEATHER WATCH WEB</span>
<a href="/os/">ResoArcOS</a>
<a href="/security/weather/">全件版の脆弱性天気予報を見る ↗</a></div></div>
<main id="content">{body}</main></body></html>'''

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--site",required=True)
    a=ap.parse_args()
    src=json.loads(pathlib.Path(a.input).read_text(encoding="utf-8"))
    assert set(src)=={"metadata","items","technologies"}
    meta=src["metadata"];rows=src["items"];tags=src["technologies"]
    assert meta["quality"]=="OK" and meta["source_count"]>=10
    assert dt.date.fromisoformat(meta["date"]).year>=2026
    assert len(rows)==meta["published_date_count"] and len(rows)>=1
    assert all(r["resoarc_impact"]=="NOT_CONFIRMED" and r["resoarc_response"]=="UNREVIEWED" for r in rows)
    assert len({r["id"] for r in rows})==len(rows)
    for id_ in PRIORITY_IDS+list(ISSUES):
        if id_ not in {r["id"] for r in rows}:
            raise RuntimeError("Missing editorially verified advisory: "+id_)
    out=pathlib.Path(a.site)/"security/weather/newspaper"
    out.mkdir(parents=True,exist_ok=True)
    bodies=[top_story(rows,meta),ranking(rows),tech_page(rows,tags,meta),action_page(rows,meta)]
    page_contents=[page_shell(i,bodies[i],src) for i in range(4)]
    for i,(rel,_,_) in enumerate(SECTIONS):
        dest=out/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(document(i,page_contents[i],meta),encoding="utf-8",newline="\n")
    allbody="".join(page_contents)
    allout=out/"all/index.html"
    allout.parent.mkdir(parents=True,exist_ok=True)
    allout.write_text(document(0,allbody,meta),encoding="utf-8",newline="\n")
    print(json.dumps({"edition":meta["date"],"pages":4,"print_view":1,
       "articles":len(rows),"critical_collected":sum(r["severity"]=="CRITICAL" for r in rows),
       "quality":meta["quality"],"generated_at":meta["generated_at"]},ensure_ascii=False))
if __name__=="__main__":main()
