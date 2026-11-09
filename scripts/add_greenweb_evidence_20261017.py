#!/usr/bin/env python3
# ResoArc: add verified Green Web Foundation external evidence without altering other records.
from pathlib import Path
from datetime import datetime
import requests

root=Path(__file__).resolve().parents[1]
site=root/"site"
idx=site/"index.html"
detail=site/"recognition"/"index.html"
css=site/"assets"/"recognition-20261017.css"
releases=site/"releases"/"index.html"
asset=site/"assets"/"recognition"/"green-web-verified-20261017.png"
api="https://api.thegreenwebfoundation.org/api/v3/greencheck/resoarc.com"
badge="https://app.greenweb.org/api/v3/greencheckimage/resoarc.com?nocache=true"
sess=requests.Session()
data=sess.get(api,timeout=15)
data.raise_for_status()
j=data.json()
assert j.get("green") is True and j.get("url")=="resoarc.com",j
img=sess.get(badge,timeout=20)
img.raise_for_status()
assert img.content[:8]==b"\x89PNG\r\n\x1a\n", (img.status_code,img.headers.get("Content-Type"),img.content[:20])
asset.parent.mkdir(parents=True,exist_ok=True)
asset.write_bytes(img.content)
print("EVIDENCE",j["url"],"green="+str(j["green"]),"hosted_by="+j.get("hosted_by",""),"badgebytes="+str(len(img.content)))

def replace_once(path,anchor,repl,idcheck):
    t=path.read_text(encoding="utf-8")
    if idcheck in t:
        print("ALREADY",str(path))
        return
    assert t.count(anchor)==1, (str(path),t.count(anchor),anchor[:80])
    path.write_text(t.replace(anchor,repl,1),encoding="utf-8",newline="")
    print("UPDATED",str(path))

card='<article class="rec-hub-card rec-dense-card rec-hub-card-quality rec-green-card"><div class="rec-hub-card-top"><img class="rec-green-badge" src="/assets/recognition/green-web-verified-20261017.png" alt="Green Web Foundation公式グリーンホスティング検証バッジ" width="116" height="55"><span class="rec-hub-state rec-hub-state-ok">外部確認済み</span></div><span class="rec-hub-card-eyebrow">GREEN WEB FOUNDATION</span><h4>グリーンホスティング</h4><p>公式APIでresoarc.comのGreen判定を確認。Cloudflareの登録資料に基づくホスティング事業者の評価です。</p><div class="rec-hub-grade">GREEN <small>verified host</small></div><a class="rec-hub-card-link" href="https://api.thegreenwebfoundation.org/api/v3/greencheck/resoarc.com" target="_blank" rel="noopener noreferrer">公式判定を確認 <span aria-hidden="true">↗</span></a></article>\n'
anchor='</div></div>\n<div class="rec-hub-group" role="group" aria-labelledby="rec-hub-community">'
replace_once(idx,anchor,card+anchor,'rec-green-card')
# Give exactly four quality cards a balanced desktop row.
t=idx.read_text(encoding="utf-8")
if 'class="rec-hub-grid rec-hub-quality-grid"' not in t:
    pos=t.index('aria-labelledby="rec-hub-quality"')
    grid=t.index('<div class="rec-hub-grid">',pos)
    t=t[:grid]+t[grid:].replace('<div class="rec-hub-grid">','<div class="rec-hub-grid rec-hub-quality-grid">',1)
    idx.write_text(t,encoding="utf-8",newline="")

audit='<article class="rec-audit-card"><span class="rec-audit-source">GREEN WEB FOUNDATION</span><div class="rec-audit-value rec-green-audit-value"><img src="/assets/recognition/green-web-verified-20261017.png" alt="Green Web Foundationの公式バッジ：グリーンホスティングを確認" width="145" height="69"></div><h3>グリーンホスティングの検証</h3><p>2026年10月17日の公式API検査で、resoarc.comは <strong>green: true</strong> と判定されました。ホスト名はCloudflare。登録されたホスティング提供事業者の環境情報に基づく検査であり、サイト独自の温室効果ガス排出量がゼロであることを意味しません。</p><a href="https://api.thegreenwebfoundation.org/api/v3/greencheck/resoarc.com" target="_blank" rel="noopener noreferrer">公式APIの検証結果を見る ↗</a></article>\n'
anchor2='</div>\n<div class="rec-disclaimer">評価日：2026年10月17日'
replace_once(detail,anchor2,audit+anchor2,'rec-green-audit-value')
styles="""
/* Four balanced verified quality cards, preserving the original cards' styles. */
.rec-green-badge {width:116px;height:55px;object-fit:contain;object-position:left center;max-width:100%;}
.rec-green-audit-value {display:flex;align-items:center;min-height:78px;}
.rec-green-audit-value img {display:block;width:145px;height:auto;max-width:100%;object-fit:contain;}
@media (min-width: 1180px) {.rec-hub-quality-grid {grid-template-columns:repeat(4,minmax(0,1fr));}}
@media (min-width: 740px) and (max-width: 1179px) {.rec-hub-quality-grid {grid-template-columns:repeat(2,minmax(0,1fr));}}
"""
t=css.read_text(encoding="utf-8")
if '.rec-green-badge' not in t:
    css.write_text(t.rstrip()+"\n"+styles,encoding="utf-8",newline="")
    print("UPDATED CSS")
# Record it transparently in release log.
rentry='<div class="release-entry"><div><time datetime="2026-10-17">2026.10.17</time><span>EXTERNAL QUALITY / GREEN WEB</span></div><div><h2>Green Web Foundationの外部判定を公開</h2><p>resoarc.comが公式Green Web Check APIでgreen: trueと判定された記録を公開しました。これはホスティング提供事業者の情報に基づく検査であり、ResoArc独自のカーボンニュートラル認定ではありません。<a href="/recognition/#security-evidence">根拠と公式バッジを見る ↗</a></p></div></div>\n'
t=releases.read_text(encoding="utf-8")
if 'EXTERNAL QUALITY / GREEN WEB' not in t:
    mark='<div class="release-entry">'
    assert t.count(mark)>=1
    releases.write_text(t.replace(mark,rentry+mark,1),encoding="utf-8",newline="")
    print("UPDATED RELEASES")
print("DONE")
