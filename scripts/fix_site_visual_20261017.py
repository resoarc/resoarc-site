#!/usr/bin/env python3
"""Fix responsive layout and provide an honest on-site fallback for unavailable GitHub.
Starts from a synchronized live snapshot. Does not touch immutable Web8 v1 sources.
"""
from pathlib import Path
import re
from html import escape

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
FROZEN={f"tools/{s}/index.html" for s in (
 "kintone-bulk-preview","kintone-app-diff","kintone-permission-audit","kintone-import-check",
 "kintone-duplicates","kintone-lookup-audit","kintone-cross-aggregate","kintone-print-report"
)}
CSS=SITE/"assets/site-20261015-v10.css"
css=CSS.read_text(encoding="utf8")
TAG="/* Site responsive and source-availability polish 2026-10-17 */"
if TAG not in css:
 css+='''\n'''+TAG+'''
/* CSP-safe alternatives to ignored inline styles on 5 plugin preview pages. */
pre.suite-result{display:block;box-sizing:border-box;max-width:100%;min-width:0;overflow-x:auto;overflow-y:hidden;
  white-space:pre;overflow-wrap:normal;background:#17343d;color:#fff;padding:16px;border-radius:5px;
  scrollbar-width:thin;scrollbar-color:#88acb6 #17343d}
/* Better affordance on compact devices while preserving the existing typography. */
@media(max-width:640px){
 .kicker{white-space:normal;flex-wrap:wrap;row-gap:7px}
 .inside-hero h1{font-size:clamp(24px,7.15vw,34px);line-height:1.44;text-wrap:balance;overflow-wrap:anywhere}
 .update-row strong a,.no-more a{display:inline-block;padding:6px 0;line-height:1.65}
 .catalog-status-note{line-height:1.85}
}
.catalog-status-note{color:#4a6470;font-size:13px;line-height:1.9;max-width:72ch;margin:16px 0 0}
.source-availability{background:#f0f5f7;border-top:1px solid #d4e2e9;border-bottom:1px solid #d4e2e9}
.source-availability-inner{display:flex;align-items:center;gap:14px 20px;flex-wrap:wrap;padding:17px 0;
 color:#284655;font-size:13px;line-height:1.75}
.source-availability-inner a,.source-card a{color:#205771;text-decoration:underline;text-underline-offset:4px;font-weight:700}
.source-availability-inner strong{font-weight:800}
.source-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin:26px 0}
.source-card{padding:27px;background:white;border:1px solid #d2dfe6;border-radius:8px;min-width:0}
.source-card h2{font-size:21px;margin:0 0 10px;color:#18394d}
.source-card p{font-size:13px;line-height:1.9}
.source-card ul{list-style:none;padding:0;margin:18px 0 0}
.source-card li{border-top:1px solid #e3e9ef;padding:11px 0;font-size:13px;line-height:1.65}
.source-card li a{display:inline-block;padding:3px 0;overflow-wrap:anywhere}
.source-note{font-size:13px;line-height:1.85;padding:18px 24px;background:#edf4f7;border-left:3px solid #43718a}
@media(max-width:720px){.source-grid{grid-template-columns:1fr}.source-card{padding:20px}}
@media(max-width:380px){.source-availability-inner{font-size:12px}}
/* The release journal remains scannable even when entries are long. */
@media(max-width:640px){
 .release-entry{padding-top:22px;padding-bottom:24px;overflow-wrap:anywhere}
 .release-entry p{line-height:1.9}
}
'''
 CSS.write_text(css,encoding="utf8")

# Correct the misleading category heading: only one plugin is formally released.
kfile=SITE/"products/kintone/index.html"
txt=kfile.read_text(encoding="utf8")
txt=txt.replace('<span class="kicker-en">AVAILABLE</span><span class="kicker-jp">公開製品</span>',
                '<span class="kicker-en">RELEASE & PREVIEW</span><span class="kicker-jp">公開製品・開発版</span>',1)
txt=txt.replace('<div class="product-grid"><article class="product-card">',
                '<p class="catalog-status-note">正式公開中のプラグインと、実機検証前のβ版・開発α版をまとめています。各カードの状態表示を確認し、本番環境には検証版を導入しないでください。</p><div class="product-grid"><article class="product-card">',1)
kfile.write_text(txt,encoding="utf8")

# A prominent but quiet route to available public source archives.
banner=('''<section class="source-availability" aria-label="公開ソースの案内"><div class="container source-availability-inner">
<strong>公開ソースについて</strong><span>GitHubのResoArcリポジトリは現在外部から参照できません。利用可能な代替ソースZIPを案内しています。</span>
<a href="/source/">公開ソース・提供状況を見る ↗</a></div></section>''')
home=SITE/"index.html"
txt=home.read_text(encoding="utf8")
if 'class="source-availability"' not in txt:
 idx=txt.find('</section>',txt.find('<main'))
 if idx<0:raise RuntimeError("Home hero section not found")
 idx+=len('</section>')
 txt=txt[:idx]+banner+txt[idx:]
 home.write_text(txt,encoding="utf8")

# Source availability hub; links only to local files verified in this checkout.
archives=[
 ('Web診断8機能 v1.0.0 正式版','/downloads/resoarc-web8-v1.0.0-source.zip'),
 ('Raspberry Pi 初回セットアップ α版','/downloads/resoarcos-pi-firstboot-v0.2.1-alpha-source.zip'),
 ('ResoArcOS PC 開発プレビュー','/downloads/resoarcos-pc-v0.1.0-dev-source.zip'),
 ('条件付き書式 α版','/downloads/resoarc-conditional-format-v0.1.0-alpha-source.zip'),
 ('日付・期間計算 α版','/downloads/resoarc-date-calculator-v0.1.0-alpha-source.zip'),
 ('Excel風一覧編集 α版','/downloads/resoarc-grid-editor-v0.1.0-alpha-source.zip'),
 ('高機能検索 α版','/downloads/resoarc-list-search-v0.1.0-alpha-source.zip'),
 ('カンバン表示 α版','/downloads/resoarc-kanban-v0.1.0-alpha-source.zip')
]
for label,url in archives:
 if not (SITE/url.lstrip('/')).is_file():raise RuntimeError("Missing actual source archive: "+url)
def item(a):
 label,url=a
 return '<li><a href="'+escape(url)+'" download>'+escape(label)+' ソースZIP ↘</a></li>'
hero='''<main id="main"><section class="inside-hero"><div class="container inside-hero-inner">
<div class="kicker"><span class="kicker-no">07</span><span class="kicker-en">SOURCE & AVAILABILITY</span><span class="kicker-jp">公開ソース</span></div>
<h1>使えるソースを、<br>わかりやすい場所に。</h1>
<p>GitHubの復旧状況にかかわらず、確認可能なソースと配布の状態を案内します。</p></div>
<span class="inside-watermark" aria-hidden="true">ResoArc.</span></section>
<section class="section inner-section"><div class="container"><div class="source-note"><strong>2026年10月17日時点</strong>
GitHubのResoArcリポジトリとGitHub Releasesが閲覧できないため、一部の外部リンクは開けません。
下記のファイルはこのサイト内から直接取得できます。GitHubの障害・制限の理由について、確認できていないことは断定しません。</div>
<div class="source-grid">
<article class="source-card" id="web"><h2>Webツールのソース</h2><p>正式版8種類の検査用ソースアーカイブです。元の正式版ソースや配布物の整合性は変更していません。</p><ul>'''+item(archives[0])+'''</ul><p><a href="/products/web/">Webツール一覧へ ↗</a></p></article>
<article class="source-card" id="os"><h2>ResoArcOS ソース</h2><p>PC版・Raspberry Pi版の開発ソースです。<strong>PC版のISOはGitHub Releases側のため現在このサイトから取得できません。</strong>ソースZIPをそのままSDカードに書き込める完成IMGと誤認しないでください。</p><ul>'''+''.join(item(x) for x in archives[1:3])+'''</ul><p><a href="/os/">OS製品の説明へ ↗</a></p></article>
<article class="source-card" id="kintone"><h2>kintoneプラグイン</h2><p>α版ソースはここから取得できます。自動採番・タブ表示などのプラグインZIPは製品ページで案内します。全プラグインの完全な公開ソースの代替ではありません。</p><ul>'''+''.join(item(x) for x in archives[3:])+'''</ul><p><a href="/products/kintone/">プラグイン一覧・配布状況へ ↗</a></p></article>
<article class="source-card"><h2>透明性と提供状況</h2><p>GitHub上で公開しているはずの内容を、ここで全量復旧できたとは表明しません。提供済みのダウンロードは引き続き保持し、GitHubが復旧した段階でソースとの継続性・公開履歴を照合します。</p>
<p><a href="/releases/">更新履歴を確認 ↗</a></p><p><a href="/principles/">品質・検証方針 ↗</a></p></article>
</div></div></section></main>'''
# Reuse latest brand layout, replacing only main and SEO fields.
tpl=(SITE/"products/index.html").read_text(encoding="utf8")
tpl=re.sub(r'<main\b[^>]*>.*?</main>',hero,tpl,count=1,flags=re.S)
tpl=re.sub(r'<title>[^<]*</title>','<title>公開ソース・提供状況 | ResoArc</title>',tpl,count=1)
tpl=re.sub(r'(<meta name="description" content=")[^"]*(")',r'\g<1>ResoArcの公開ソースZIPとGitHub提供状況。Webツール、kintone開発版、ResoArcOSの利用可能なソースを案内。\2',tpl,count=1)
tpl=tpl.replace('https://resoarc.com/products/','https://resoarc.com/source/')
(SITE/"source").mkdir(exist_ok=True)
(SITE/"source/index.html").write_text(tpl,encoding="utf8")

# Redirect visitors to working internal source/status page for editable HTML only.
pattern=re.compile(r'<a\b(?P<before>[^>]*?)href="https://github\.com/resoarc/resoarc-site(?P<suffix>[^"]*)"(?P<after>[^>]*)>(?P<label>.*?)</a>',re.S)
num=0
for file in SITE.rglob('*.html'):
 relative=file.relative_to(SITE).as_posix()
 if relative in FROZEN:continue
 html=file.read_text(encoding="utf8")
 def repl(m):
  global num
  num+=1
  suf=m.group('suffix')
  href='/source/#os' if '/releases/' in suf else '/source/#kintone' if '/plugins/' in suf else '/source/'
  lbl=m.group('label')
  if '/releases/' in suf:
   lbl="GitHub Releasesの提供状況・代替案内 ↗"
  elif '/plugins/' in suf:
   lbl="ソース・配布状況を確認 ↗"
  elif "GitHub" in lbl:
   lbl="公開ソース・GitHub状況 ↗"
  else:
   lbl="公開ソースの提供状況 ↗"
  attrs=(m.group('before')+m.group('after')).replace('rel="noopener noreferrer"','')
  return '<a '+attrs+'href="'+href+'">'+lbl+'</a>'
 updated=pattern.sub(repl,html)
 if updated!=html:file.write_text(updated,encoding="utf8")
print("EDITABLE_GITHUB_LINKS_REDIRECTED",num,"preserved frozen pages",len(FROZEN))

# Newly created source page should have working footer route too.
for name in ('sitemap.xml','llms.txt'):
 f=SITE/name;txt=f.read_text(encoding='utf8')
 if name=='sitemap.xml' and 'https://resoarc.com/source/' not in txt:
  txt=txt.replace('</urlset>','<url><loc>https://resoarc.com/source/</loc></url></urlset>')
 elif name=='llms.txt' and '/source/' not in txt:
  txt+='\n- Public source availability: https://resoarc.com/source/\n'
 f.write_text(txt,encoding='utf8')
# Add a verified release-note entry; the homepage already reads entries from this page.
rfile=SITE/"releases/index.html";txt=rfile.read_text(encoding='utf8')
if "スマートフォン表示の整合性" not in txt:
 new='''<div class="release-entry"><div><time datetime="2026-10-17">2026.10.17</time><span>SITE UX / SOURCE</span></div><div><h2>スマートフォン表示の整合性と公開ソース案内を改善</h2><p>設定例の横はみ出しと見出しの改行を修正し、kintoneの正式版・開発版の区別を明確化しました。GitHubへアクセスできない間も取得できるソースZIPを確認できるようにしています。<a href="/source/">公開ソース・提供状況を見る ↗</a></p></div></div>'''
 m=re.search(r'<div class="release-entry">',txt)
 if not m:raise RuntimeError("Release list not found")
 txt=txt[:m.start()]+new+txt[m.start():]
 rfile.write_text(txt,encoding='utf8')
print("SITE_UX_FIXED")
