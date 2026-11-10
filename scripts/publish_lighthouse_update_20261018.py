#!/usr/bin/env python3
"""Publish dated, qualified Lighthouse self-test measurements in canonical static site."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/"site"
index=root/"index.html"
rel=root/"releases/index.html"
release_id="SITE QUALITY / LIGHTHOUSE SELF-AUDIT"
entry='<div class="release-entry"><div><time datetime="2026-10-18">2026.10.18</time><span>'+release_id+'</span></div><div><h2>Lighthouse診断に基づきサイトの視認性と表示安定性を改善</h2><p>文字のコントラスト・補足文字のサイズとアクセシブルな表記を改善しました。Lighthouse CLI 12.8.2（Chrome・モバイル相当のシミュレーション）による2026年10月18日の本番URL一回の検査ではPerformance 82、Accessibility 100、Best Practices 93、SEO 100でした。変更前の同じ方式の診断はそれぞれ77、95、89、100。得点は計測条件により変動し、外部認証や常時の性能保証を意味しません。CSPは厳格な設定を維持しています。</p><p><a href="/recognition/">実績・外部評価の根拠を見る ↗</a></p></div></div>\n'
s=rel.read_text(encoding="utf8")
if release_id not in s:
    assert s.count('<div class="release-entry">')>=1
    rel.write_text(s.replace('<div class="release-entry">',entry+'<div class="release-entry">',1),encoding="utf8",newline="")
    print("RELEASES_UPDATED")
else:print("RELEASES_ALREADY")
news_id="LIGHTHOUSE / ACCESSIBILITY"
news='<div class="update-row"><time datetime="2026-10-18">2026.10.18</time><span>'+news_id+'</span><strong><a href="/releases/">Webサイトの視認性を改善。Lighthouseでアクセシビリティ100点を記録 ↗</a></strong></div>'
s=index.read_text(encoding="utf8")
if news_id not in s:
    begin=s.index('<div class="updates-items">')
    end=s.index('<p class="no-more">',begin)
    segment=s[begin:end]
    assert segment.count('<div class="update-row">')>=5
    segment=segment.replace('<div class="update-row">',news+'<div class="update-row">',1)
    # Keep the original six-item public news density.
    last=segment.rfind('<div class="update-row">')
    if segment.count('<div class="update-row">')>6:
        segment=segment[:last]
    s=s[:begin]+segment+s[end:]
    index.write_text(s,encoding="utf8",newline="")
    print("TOP_NEWS_UPDATED")
else:print("TOP_NEWS_ALREADY")
