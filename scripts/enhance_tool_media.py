#!/usr/bin/env python3
"""Build original feature pictograms and embed verified captures into tool pages.

Can be safely rerun. Image captures are generated separately by capture_tool_ui.py.
"""
from __future__ import annotations
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
ICON_DIR=SITE/"assets"/"tool-icons"
ICON_DIR.mkdir(parents=True,exist_ok=True)
ICON={
"hash": ('#e4f2ec','#237669','<rect x="14" y="13" width="36" height="38" rx="7"/><path d="M27 22 23 43M39 22 35 43M19 29h26M17 37h26"/>'),
"csv": ('#e9f1fb','#336b9c','<rect x="12" y="13" width="40" height="38" rx="4"/><path d="M12 25h40M12 37h40M25 13v38M39 13v38"/>'),
"kintone-app-diff": ('#f0eafe','#7454a9','<rect x="9" y="13" width="19" height="37" rx="3"/><rect x="36" y="13" width="19" height="37" rx="3"/><path d="M14 24h9M14 31h6M41 24h9M41 31h7M26 42l9-9M27 33l9 9"/>'),
"kintone-import-check": ('#e9f4e7','#4a825c','<rect x="13" y="11" width="38" height="44" rx="5"/><path d="m20 25 4 4 7-8M34 26h9M20 39h23M20 46h17"/>'),
"kintone-bulk-preview": ('#e8f3f8','#317d9e','<rect x="18" y="14" width="34" height="39" rx="4"/><path d="M25 23h20M25 31h13M25 39h17"/><rect x="11" y="8" width="16" height="12" rx="3"/>'),
"kintone-permission-audit": ('#e7f4f1','#31826f','<path d="M32 9 50 16v13c0 13-7 21-18 26C21 50 14 42 14 29V16L32 9Z"/><path d="m24 32 6 6 12-14"/>'),
"kintone-duplicates": ('#fff0e4','#ae6b32','<rect x="12" y="13" width="29" height="32" rx="4"/><path d="M22 21h11M22 29h11M22 37h9"/><path d="M42 21h5c3 0 5 2 5 5v25c0 3-2 5-5 5H25c-3 0-5-2-5-5v-3"/>'),
"kintone-lookup-audit": ('#ecedfa','#6a6caa','<path d="m26 25 6-6a10 10 0 0 1 14 14l-5 5M38 39l-6 6a10 10 0 0 1-14-14l6-6M25 38l14-14"/>'),
"kintone-cross-aggregate": ('#f6ebf1','#9e5c82','<path d="M12 51h42M16 43V29h9v14M29 43V19h9v24M42 43V12h9v31"/><path d="m16 22 12-8 8 5 11-10"/>'),
"kintone-print-report": ('#eef0f7','#526b93','<rect x="19" y="11" width="26" height="17" rx="2"/><rect x="12" y="27" width="40" height="23" rx="5"/><path d="M20 42h24v13H20zM43 34h3M25 17h14"/>'),
"kintone-auto-number": ('#e7f1fa','#356f98','<rect x="11" y="12" width="42" height="40" rx="6"/><path d="M19 23h26M23 35h6M34 35h7M23 43h18"/>'),
"kintone-tabs": ('#eaeffa','#5d71af','<rect x="10" y="20" width="44" height="31" rx="4"/><path d="M10 27h44M14 15h16l4 5M22 34h20M22 42h13"/>'),
"kintone-conditional": ('#e7f3e9','#497b62','<path d="M13 16h38v12H13zM19 22h9M19 39h26"/><path d="m37 23 4 4 8-8M13 35h12v12H13z"/>'),
"kintone-conditional-format": ('#faebf0','#bd5b7f','<rect x="12" y="12" width="40" height="40" rx="5"/><path d="M12 25h40M25 12v40M39 25v27M18 19h3M31 19h3M45 19h3"/><path d="m29 38 4 4 7-9"/>'),
"kintone-date-calculator": ('#fff1dd','#ad7934','<rect x="11" y="16" width="42" height="36" rx="4"/><path d="M11 26h42M21 10v12M43 10v12M22 36h5M32 36h5M22 44h5M32 44h5"/>'),
"kintone-list-search": ('#e6f5f1','#2f8c7f','<rect x="11" y="12" width="30" height="40" rx="4"/><path d="M18 23h16M18 31h15M18 39h9"/><circle cx="42" cy="41" r="9"/><path d="m49 48 7 7"/>'),
"kintone-grid-editor": ('#e9effb','#5776b6','<rect x="11" y="12" width="42" height="40" rx="4"/><path d="M11 25h42M11 38h42M26 12v40M40 12v40"/><path d="m31 44 4 3 9-10"/>'),
"kintone-kanban": ('#f8ede2','#b17a43','<rect x="9" y="12" width="46" height="41" rx="5"/><path d="M24 12v41M40 12v41"/><rect x="13" y="20" width="7" height="16" rx="1"/><rect x="28" y="20" width="8" height="23" rx="1"/><rect x="44" y="20" width="7" height="10" rx="1"/>'),
}
for slug, (bg, stroke, drawing) in ICON.items():
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" role="img" aria-hidden="true"><rect width="64" height="64" rx="14" fill="{bg}"/><g fill="none" stroke="{stroke}" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round">{drawing}</g></svg>\n'
    (ICON_DIR/(slug+".svg")).write_text(svg,encoding="utf-8")

# Kintone catalog has an accidental break between 3 and 5 product cards.
kintone=SITE/"products/kintone/index.html"
text=kintone.read_text(encoding="utf-8")
boundary='</article></div><div class="product-grid"><article class="product-card">'
if boundary in text:
    text=text.replace(boundary,'</article><article class="product-card">',1)
kintone.write_text(text,encoding="utf-8")

CATALOG=[SITE/"products/index.html",SITE/"products/web/index.html",kintone,SITE/"products/kintone/qa/index.html"]
for file in CATALOG:
    text=file.read_text(encoding="utf-8")
    def add_icon(match):
        card=match.group(0)
        if 'class="tool-feature-icon"' in card:
            return card
        slug=None
        for s in ICON:
            if f'href="/tools/{s}/"' in card or f'/downloads/resoarc-{s.replace("kintone-","")}-signed-qa.zip' in card:
                slug=s
                break
        if slug is None and "kintone/qa" in file.as_posix():
            title_match=re.search(r'<h2>(.*?)</h2>',card,re.S)
            labels={
                "自動採番":"kintone-auto-number","タブ表示":"kintone-tabs",
                "条件付き表示":"kintone-conditional","条件付き書式":"kintone-conditional-format",
                "日付・期間計算":"kintone-date-calculator","検索":"kintone-list-search",
                "一覧編集":"kintone-grid-editor","カンバン":"kintone-kanban",
            }
            if title_match:
                for label,val in labels.items():
                    if label in title_match.group(1): slug=val;break
        if not slug:return card
        icon=f'<img class="tool-feature-icon" src="/assets/tool-icons/{slug}.svg" width="64" height="64" alt="" loading="lazy" decoding="async">'
        heading='<h2>' if '<h2>' in card else '<h3>'
        return card.replace(heading,icon+heading,1)
    text=re.sub(r'<article class="product-card"[^>]*>.*?</article>',add_icon,text,flags=re.S)
    file.write_text(text,encoding="utf-8")

# A real capture is inserted after the hero (not substituted for the tool UI).
FROZEN_WEB8={"kintone-bulk-preview","kintone-app-diff","kintone-permission-audit","kintone-import-check","kintone-duplicates","kintone-lookup-audit","kintone-cross-aggregate","kintone-print-report"}
for slug in ICON:
    if slug in FROZEN_WEB8:
        continue  # Immutable GA v1.0.0 HTML must remain byte-identical to release ZIP.
    file=SITE/"tools"/slug/"index.html"
    if not file.exists():continue
    text=file.read_text(encoding="utf-8")
    prior_preview=re.search(r'<section class="tool-preview-section".*?</section>',text,re.S)
    if prior_preview:
        text=text[:prior_preview.start()]+text[prior_preview.end():]
    is_plugin=slug in {
        "kintone-auto-number","kintone-tabs","kintone-conditional","kintone-conditional-format",
        "kintone-date-calculator","kintone-list-search","kintone-grid-editor","kintone-kanban",
    }
    note=("実装されたプラグイン設定画面を、テスト用kintone APIでブラウザー表示して撮影。実際のkintoneテナントでの動作保証ではありません。"
          if is_plugin else "公開中のWebツールをブラウザーで表示して撮影した画面です。サンプルデータを使用する場合があります。")
    figure=(
       f'<section class="tool-preview-section" aria-label="ツールの画面イメージ"><div class="container">'
       f'<figure class="tool-preview-figure"><div class="tool-preview-heading">'
       f'<img src="/assets/tool-icons/{slug}.svg" class="tool-preview-icon" alt="" width="56" height="56">'
       f'<div><strong>画面キャプチャ</strong><span>{"検証用設定画面" if is_plugin else "ブラウザーでの操作画面"}</span></div></div>'
       f'<a href="/assets/tool-screens/{slug}.webp" target="_blank" rel="noopener noreferrer" aria-label="画面キャプチャを拡大して見る">'
       f'<img class="tool-preview-image" src="/assets/tool-screens/{slug}.webp" alt="{"プラグイン設定画面の検証用キャプチャ" if is_plugin else "Webツール操作画面のキャプチャ"}" width="1120" height="710" loading="lazy" decoding="async"></a>'
       f'<figcaption>{note} <a href="/products/{"kintone" if is_plugin else "web"}/">{"kintoneツール" if is_plugin else "Webツール"}一覧へ ↗</a></figcaption>'
       f'</figure></div></section>'
    )
    main_match=re.search(r'<main[^>]*>',text)
    if not main_match:
        main_match=re.search(r'<main\\b[^>]*>',text)
    match=re.search(r'</section>',text[main_match.end():]) if main_match else None
    if is_plugin and match:
        # Keep the main download / availability call-to-action before the screenshot.
        after_first=main_match.end()+match.end()
        second=re.search(r'</section>',text[after_first:])
        end=after_first+second.end() if second else after_first
        text=text[:end]+figure+text[end:]
    elif not is_plugin and '</main>' in text:
        end=text.rfind('</main>')
        text=text[:end]+figure+text[end:]
    file.write_text(text,encoding="utf-8")

cssfile=SITE/"assets/site-20261015-v10.css"
css=cssfile.read_text(encoding="utf-8")
if "/* ResoArc feature pictograms and real UI previews */" not in css:
    css+='''\n/* ResoArc feature pictograms and real UI previews */
.product-card .tool-feature-icon{display:block;width:60px;height:60px;margin:14px 0 12px;border-radius:14px;flex:none}
.product-card h2{margin-top:0}
.tool-preview-section{padding:12px 0 42px;background:#f5f8f8}
.tool-preview-figure{margin:0 auto;max-width:1120px;padding:22px;background:#fff;border:1px solid #d2ddd9;border-radius:12px}
.tool-preview-heading{display:flex;gap:15px;align-items:center;margin-bottom:18px;color:#18353b}
.tool-preview-icon{width:56px;height:56px;flex:none}
.tool-preview-heading div{display:flex;flex-direction:column;gap:3px}
.tool-preview-heading strong{font-size:18px}
.tool-preview-heading span{font-size:12px;color:#587078}
.tool-preview-figure>a{display:block;border:1px solid #d5dfdf;border-radius:8px;overflow:hidden;background:#f5f8fb}
.tool-preview-image{display:block;width:100%;height:auto;aspect-ratio:1120/710;object-fit:contain}
.tool-preview-figure figcaption{font-size:12px;line-height:1.8;color:#5a6e73;margin-top:14px}
.tool-preview-figure figcaption a{color:#205964;text-decoration:underline}
@media(max-width:640px){.product-card .tool-feature-icon{width:54px;height:54px}.tool-preview-section{padding:8px 0 26px}.tool-preview-figure{padding:12px}.tool-preview-heading strong{font-size:16px}.tool-preview-figure figcaption{font-size:11px}}
'''
    cssfile.write_text(css,encoding="utf-8")
print("MEDIA_STRUCTURE_DONE",len(ICON),"icons",len(list((SITE/"tools").rglob("index.html"))),"tool detail pages")
