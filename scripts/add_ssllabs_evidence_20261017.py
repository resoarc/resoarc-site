#!/usr/bin/env python3
# Add only public Qualys SSL Labs grade from the official API.
from pathlib import Path
import requests
root=Path(__file__).resolve().parents[1]
site=root/"site"
index=site/"index.html"
detail=site/"recognition/index.html"
releases=site/"releases/index.html"
css=site/"assets/recognition-20261017.css"
icon=site/"assets/recognition/ssllabs-favicon-20261017.ico"
s=requests.Session()
r=s.get("https://api.ssllabs.com/api/v3/analyze?host=resoarc.com&fromCache=on&maxAge=24",timeout=15)
r.raise_for_status()
d=r.json()
grades=[x.get("grade") for x in d.get("endpoints",[])]
assert d.get("status")=="READY" and len(grades)>=4 and set(grades)=={"A+"},(d.get("status"),grades)
res=s.get("https://www.ssllabs.com/favicon.ico",timeout=15)
res.raise_for_status()
assert res.content[:4]==b"\x00\x00\x01\x00"
icon.write_bytes(res.content)
print("SSL_OFFICIAL",d["status"],grades,"icon",len(res.content))
card='<article class="rec-hub-card rec-dense-card rec-hub-card-quality rec-ssllabs-card"><div class="rec-hub-card-top"><img class="rec-hub-logo" src="/assets/recognition/ssllabs-favicon-20261017.ico" alt="Qualys SSL LabsのWebサイトアイコン" width="58" height="58"><span class="rec-hub-state rec-hub-state-ok">外部検査済み</span></div><span class="rec-hub-card-eyebrow">QUALYS SSL LABS</span><h4>HTTPS / TLS構成</h4><p>公式のSSL Server Testで4エンドポイントすべてA+を確認。現在の配信経路のTLS設定に対する外部評価です。</p><div class="rec-hub-grade">A+ <small>4 / 4 endpoints</small></div><a class="rec-hub-card-link" href="https://www.ssllabs.com/ssltest/analyze.html?d=resoarc.com" target="_blank" rel="noopener noreferrer">公式検査を表示 <span aria-hidden="true">↗</span></a></article>\n'
anchor='</div></div>\n<div class="rec-hub-group" role="group" aria-labelledby="rec-hub-community">'
t=index.read_text(encoding="utf-8")
if 'rec-ssllabs-card' not in t:
 assert t.count(anchor)==1,t.count(anchor)
 index.write_text(t.replace(anchor,card+anchor,1),encoding="utf-8",newline="")
 print("UPDATED_TOP")
audit='<article class="rec-audit-card rec-ssllabs-audit"><span class="rec-audit-source">QUALYS SSL LABS</span><div class="rec-audit-value">A+ <span>4 / 4 endpoints</span></div><h3>HTTPS / TLSの外部評価</h3><p>2026年10月17日、公式SSL Labs APIの <strong>READY</strong> な結果において、resoarc.comのIPv4・IPv6計4エンドポイントがいずれもA+。これはCDN経由のTLS構成に関する時点評価であり、アプリケーション全体の脆弱性診断・製品認証ではありません。</p><a href="https://www.ssllabs.com/ssltest/analyze.html?d=resoarc.com" target="_blank" rel="noopener noreferrer">公式のSSL Server Testを見る ↗</a></article>\n'
anchor2='</div>\n<div class="rec-disclaimer">評価日：2026年10月17日'
t=detail.read_text(encoding="utf-8")
if 'rec-ssllabs-audit' not in t:
 assert t.count(anchor2)==1,t.count(anchor2)
 t=t.replace(anchor2,audit+anchor2,1)
 assert t.count('<div class="rec-audit-grid">')==1
 t=t.replace('<div class="rec-audit-grid">','<div class="rec-audit-grid rec-audit-grid-5">',1)
 detail.write_text(t,encoding="utf-8",newline="")
 print("UPDATED_DETAIL")
styles="""
/* Balanced 3+2 responsive layout after verified SSL Labs check. */
@media (min-width:1100px) {
 .rec-hub-quality-grid,.rec-audit-grid-5 {grid-template-columns:repeat(6,minmax(0,1fr));}
 .rec-hub-quality-grid > article,.rec-audit-grid-5 > article {grid-column:span 2;}
 .rec-hub-quality-grid > article:nth-child(n+4),.rec-audit-grid-5 > article:nth-child(n+4) {grid-column:span 3;}
}
@media (min-width:740px) and (max-width:1099px) {
 .rec-hub-quality-grid,.rec-audit-grid-5 {grid-template-columns:repeat(2,minmax(0,1fr));}
 .rec-hub-quality-grid > article:last-child:nth-child(odd),.rec-audit-grid-5 > article:last-child:nth-child(odd) {grid-column:span 2;}
}
"""
t=css.read_text(encoding="utf-8")
if "Balanced 3+2 responsive layout" not in t:
 css.write_text(t.rstrip()+"\n"+styles,encoding="utf-8",newline="")
 print("UPDATED_CSS")
rentry='<div class="release-entry"><div><time datetime="2026-10-17">2026.10.17</time><span>EXTERNAL SECURITY / SSL LABS</span></div><div><h2>SSL LabsのHTTPS/TLS評価4件でA+を確認</h2><p>公式APIでresoarc.comのIPv4・IPv6の4エンドポイントすべてがA+と確認された検査結果を掲載しました。配信経路のTLS構成の評価であり、製品全体のセキュリティ認証ではありません。<a href="/recognition/#security-evidence">評価内容を見る ↗</a></p></div></div>\n'
t=releases.read_text(encoding="utf-8")
if "EXTERNAL SECURITY / SSL LABS" not in t:
 assert '<div class="release-entry">' in t
 releases.write_text(t.replace('<div class="release-entry">',rentry+'<div class="release-entry">',1),encoding="utf-8",newline="")
 print("UPDATED_RELEASES")
print("DONE")
