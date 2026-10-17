#!/usr/bin/env python3
from pathlib import Path
import requests
p=Path(__file__).resolve().parents[1]/"site/releases/index.html"
live=requests.get("https://resoarc.com/releases/",timeout=15)
live.raise_for_status()
s=live.text
key="WEB SECURITY / STAGED HSTS"
if key not in s:
    entry='<div class="release-entry"><div><time datetime="2026-10-18">2026.10.18</time><span>'+key+'</span></div><div><h2>HTTPS強制ポリシーを段階的に強化</h2><p>全ページでHTTPSによる正常応答を確認し、HSTSの有効期間を5分から1週間に延長しました。サブドメイン一括適用とプリロードは行っていません。公式診断の未達項目は引き続き公開し、十分な運用確認後に次の段階を検討します。<a href="/recognition/#security-evidence">外部診断を見る ↗</a></p></div></div>'
    anchor='<div class="release-entry">'
    assert anchor in s
    s=s.replace(anchor,entry+"\n"+anchor,1)
assert s.count(key)==1,s.count(key)
p.write_text(s,encoding="utf8",newline="")
print("RELEASES_OK",len(s),"entries",s.count('<div class="release-entry">'))
