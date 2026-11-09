#!/usr/bin/env python3
"""Publish explanatory screenshots without mutating immutable Web8 v1.0.0 tool HTML."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
GALLERY=SITE/"products/web/screens/index.html"
GALLERY.parent.mkdir(parents=True,exist_ok=True)
NAMES={
"kintone-app-diff":"設定JSON差分比較",
"kintone-import-check":"kintone CSV取込前診断",
"kintone-bulk-preview":"一括更新・変更前プレビュー",
"kintone-permission-audit":"kintone権限定義の可視化",
"kintone-duplicates":"重複レコード候補の検出",
"kintone-lookup-audit":"ルックアップ不整合診断",
"kintone-cross-aggregate":"アプリ横断集計",
"kintone-print-report":"ブラウザー帳票・PDF保存",
}
WEB_CATALOG=SITE/"products/web/index.html"
source=WEB_CATALOG.read_text(encoding="utf-8")
# Preserve the main site header and footer, including accessibility and menu.
start=source.index('<main id="main">')
end=source.rindex('</main>')+len('</main>')
prefix=source[:start].replace("Webツール一覧 | ResoArc","Webツールの画面キャプチャ | ResoArc")
prefix=prefix.replace('href="https://resoarc.com/products/web/"','href="https://resoarc.com/products/web/screens/"')
prefix=prefix.replace('content="https://resoarc.com/products/web/"','content="https://resoarc.com/products/web/screens/"')
suffix=source[end:]
parts=[
'<main id="main"><section class="inside-hero"><div class="container inside-hero-inner">',
'<div class="kicker"><span class="kicker-no">02</span><span class="kicker-en">SCREENSHOTS</span><span class="kicker-jp">画面キャプチャ</span></div>',
'<h1>実際の画面から、<br>使い方をイメージする。</h1>',
'<p>ResoArcのWeb解析ツールをサンプルデータで操作したブラウザー画面です。各ツールは静的なWebページで動作します。</p>',
'</div><span class="inside-watermark" aria-hidden="true">ResoArc.</span></section>',
'<nav class="category-nav container" aria-label="ツール一覧へ戻る"><a href="/products/web/"><strong>Webツール一覧</strong><small>各ツールの機能を比較</small><span aria-hidden="true">↗</span></a>',
'<a href="/products/"><strong>すべてのツール</strong><small>Webとkintoneプラグイン</small><span aria-hidden="true">↗</span></a></nav>',
'<section class="section inner-section"><div class="container">',
'<div class="kicker"><span class="kicker-no">01</span><span class="kicker-en">REAL UI</span><span class="kicker-jp">ツール別スクリーンショット</span></div>',
'<p class="catalog-lede">下の画像は公開中の各Webツールをブラウザー上で動かして撮影したものです。画面の入力例・診断結果はサンプルデータです。現在のバージョンで一部表示が異なる場合があります。</p>',
'<div class="tool-screen-gallery">',
]
for slug,title in NAMES.items():
    parts.append(
        f'<article class="tool-gallery-item" id="{slug}"><div class="tool-gallery-heading">'
        f'<img src="/assets/tool-icons/{slug}.svg" width="56" height="56" alt="" loading="lazy">'
        f'<div><h2>{title}</h2><p>実際のWebツール画面・サンプルデータによる操作結果</p></div></div>'
        f'<a href="/assets/tool-screens/{slug}.webp" target="_blank" rel="noopener noreferrer" aria-label="{title}の画面を拡大する">'
        f'<img class="tool-gallery-image" src="/assets/tool-screens/{slug}.webp" width="1120" height="710" alt="{title}のブラウザー操作画面" loading="lazy" decoding="async"></a>'
        f'<p><a class="inline-link" href="/tools/{slug}/">ツールを使ってみる ↗</a></p></article>'
    )
parts.append('</div></div></section></main>')
GALLERY.write_bytes((prefix+''.join(parts)+suffix).encode("utf-8"))
# Link a screenshot only from its own product card.
# IMPORTANT: Match one entire <article> at a time. A regex starting from the
# first <article> and searching for a later tool href can silently match several
# cards, causing triangular repeated links (52 rather than the required 8).
text=WEB_CATALOG.read_text(encoding="utf-8")
card_pattern=re.compile(r'<article class="product-card"[^>]*>.*?</article>',re.S)
screen_link_pattern=re.compile(r'<a\b[^>]*class="tool-gallery-link"[^>]*>.*?</a>',re.S)
parts=[]
cursor=0
matched_slugs=[]
for match in card_pattern.finditer(text):
    parts.append(text[cursor:match.start()])
    card=match.group(0)
    tool_links=re.findall(r'href="/tools/([a-z0-9-]+)/"',card)
    if len(tool_links)!=1:
        raise RuntimeError("expected exactly one primary tool per card: "+repr(tool_links))
    slug=tool_links[0]
    # Remove only gallery links, leaving the tool CTA and all other markup intact.
    card=screen_link_pattern.sub('',card)
    if slug in NAMES:
        href=f'/products/web/screens/#{slug}'
        card=card.replace('</article>',
            f'<a class="tool-gallery-link" href="{href}">画面キャプチャを見る ↗</a></article>',1)
        matched_slugs.append(slug)
    parts.append(card)
    cursor=match.end()
parts.append(text[cursor:])
if set(matched_slugs)!=set(NAMES) or len(matched_slugs)!=len(NAMES):
    raise RuntimeError("gallery links do not cover the expected 8 unique tools: "+str(matched_slugs))
text=''.join(parts)
if len(screen_link_pattern.findall(text))!=len(NAMES):
    raise RuntimeError("must have exactly one screenshot link per supported tool")
WEB_CATALOG.write_bytes(text.encode("utf-8"))
cssfile=SITE/"assets/site-20261015-v10.css"
css=cssfile.read_text(encoding="utf-8")
if "/* Web8 GA screenshot gallery */" not in css:
    css+='''\n/* Web8 GA screenshot gallery */
.tool-gallery-link{font-size:12px;color:#2d6571;text-decoration:underline;text-underline-offset:3px;margin-top:12px;display:inline-block}
.tool-screen-gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:26px;margin-top:28px}
.tool-gallery-item{background:#fff;border:1px solid #d3dfe7;border-radius:10px;padding:20px;scroll-margin-top:105px;min-width:0}
.tool-gallery-heading{display:flex;gap:15px;align-items:center;margin-bottom:16px}
.tool-gallery-heading img{flex:none;width:56px;height:56px}
.tool-gallery-heading h2{font-size:19px;margin:0 0 5px}
.tool-gallery-heading p{font-size:12px;color:#61727e;margin:0}
.tool-gallery-item>a:has(img){display:block;overflow:hidden;border-radius:5px;border:1px solid #d9e1e5}
.tool-gallery-image{display:block;width:100%;height:auto;aspect-ratio:1120/710;object-fit:contain}
.tool-gallery-item>p{margin:16px 0 0}
@media(max-width:780px){.tool-screen-gallery{grid-template-columns:1fr}.tool-gallery-heading h2{font-size:17px}}
'''
    cssfile.write_text(css,encoding="utf-8")
# Make the gallery discoverable to crawlers and users.
site_map=SITE/"sitemap.xml"
xml=site_map.read_text(encoding="utf-8")
url="https://resoarc.com/products/web/screens/"
if url not in xml:
    xml=xml.replace("</urlset>",f'<url><loc>{url}</loc></url></urlset>')
    site_map.write_text(xml,encoding="utf-8")
print("WEB8_GA_GALLERY_READY",len(NAMES),"immutable pages unchanged")
