#!/usr/bin/env python3
# Publish independent Internet.nl measurement as a transparent, non-badge assessment.
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[1]
site=root/"site"
index=site/"index.html"
detail=site/"recognition/index.html"
releases=site/"releases/index.html"
css=site/"assets/recognition-20261017.css"
icon=site/"assets/recognition/internetnl-favicon-20261017.png"
report="https://internet.nl/site/resoarc.com/4355764/"
s=requests.Session()
r=s.get(report,timeout=15)
r.raise_for_status()
assert "73%" in r.text and "resoarc.com" in r.text
logo=s.get("https://internet.nl/static/favicon.png",timeout=15)
logo.raise_for_status()
assert logo.content.startswith(b"\x89PNG\r\n\x1a\n")
icon.write_bytes(logo.content)
print("INTERNETNL",report,"73%","favicon",len(logo.content))
card='<article class="rec-hub-card rec-dense-card rec-hub-card-quality rec-internetnl-card"><div class="rec-hub-card-top"><img class="rec-hub-logo" src="/assets/recognition/internetnl-favicon-20261017.png" alt="Internet.nlの公式サイトアイコン" width="58" height="58"><span class="rec-hub-state rec-hub-state-pending">改善中</span></div><span class="rec-hub-card-eyebrow">INTERNET.NL / INTERNET STANDARDS</span><h4>インターネット標準への対応</h4><p>外部診断でIPv6・RPKIが合格。DNSSEC・一部TLS設定は改善課題として結果を公開しています。</p><div class="rec-hub-grade">73% <small>検査時点の得点</small></div><a class="rec-hub-card-link" href="'+report+'" target="_blank" rel="noopener noreferrer">公式診断結果を見る <span aria-hidden="true">↗</span></a></article>\n'
anchor='</div></div>\n<div class="rec-hub-group" role="group" aria-labelledby="rec-hub-community">'
t=index.read_text(encoding="utf-8")
if "rec-internetnl-card" not in t:
 assert t.count(anchor)==1,t.count(anchor)
 index.write_text(t.replace(anchor,card+anchor,1),encoding="utf-8",newline="")
 print("UPDATED_TOP")
audit='<article class="rec-audit-card rec-internetnl-audit"><span class="rec-audit-source">INTERNET.NL / INTERNET STANDARDS</span><div class="rec-audit-value">73% <span>改善中</span></div><h3>インターネット標準への対応状況</h3><p>2026年10月17日の外部サイト診断では73%。IPv6とRPKIの検査に合格し、DNSSEC、HSTS、暗号スイートなど一部の必須項目は未達です。公式100%バッジは取得していません。点数は診断時点の記録で、設定改善後は変わる可能性があります。</p><a href="'+report+'" target="_blank" rel="noopener noreferrer">公式の詳細診断を見る ↗</a></article>\n'
anchor2='</div>\n<div class="rec-disclaimer">評価日：2026年10月17日'
t=detail.read_text(encoding="utf-8")
if "rec-internetnl-audit" not in t:
 assert t.count(anchor2)==1,t.count(anchor2)
 t=t.replace(anchor2,audit+anchor2,1)
 t=t.replace('既存の<a href="https://www.bestpractices.dev/en/projects/15597"', '既存の<a href="https://www.bestpractices.dev/en/projects/15597"',1)
 t=t.replace("の管理権限を確認中。Passing / Silver / Gold の各バッジは未取得です。","の管理権限を確認中。Baseline Level 1は公式公開データで17%（2026年10月17日確認）。Passing / Silver / GoldおよびBaseline各レベルのバッジは未取得です。",1)
 detail.write_text(t,encoding="utf-8",newline="")
 print("UPDATED_DETAIL")
styles="""
/* Six quality verification records: full 3-by-2 desktop grid; 2-by-3 tablet grid. */
@media (min-width:1100px) {
 .rec-hub-quality-grid,.rec-audit-grid-5 {grid-template-columns:repeat(3,minmax(0,1fr));}
 .rec-hub-quality-grid > article,.rec-audit-grid-5 > article,
 .rec-hub-quality-grid > article:nth-child(n+4),.rec-audit-grid-5 > article:nth-child(n+4) {grid-column:auto;}
}
@media (min-width:740px) and (max-width:1099px) {
 .rec-hub-quality-grid,.rec-audit-grid-5 {grid-template-columns:repeat(2,minmax(0,1fr));}
 .rec-hub-quality-grid > article:last-child:nth-child(odd),
 .rec-audit-grid-5 > article:last-child:nth-child(odd) {grid-column:auto;}
}
"""
t=css.read_text(encoding="utf-8")
if "Six quality verification records" not in t:
 css.write_text(t.rstrip()+"\n"+styles,encoding="utf-8",newline="")
 print("UPDATED_CSS")
rentry='<div class="release-entry"><div><time datetime="2026-10-17">2026.10.17</time><span>INTERNET STANDARDS / EVALUATION</span></div><div><h2>Internet.nlでの公開診断73%を記録</h2><p>IPv6・RPKI合格、DNSSEC・TLS設定等の未達も含め、公開診断結果への恒久リンクを掲載しました。100%バッジは未取得です。<a href="/recognition/#security-evidence">根拠と改善項目を見る ↗</a></p></div></div>\n'
t=releases.read_text(encoding="utf-8")
if "INTERNET STANDARDS / EVALUATION" not in t:
 releases.write_text(t.replace('<div class="release-entry">',rentry+'<div class="release-entry">',1),encoding="utf-8",newline="")
 print("UPDATED_RELEASES")
print("DONE")
