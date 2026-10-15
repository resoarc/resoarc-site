#!/usr/bin/env python3
"""Idempotently connect the ResoArc website to its public GitHub source."""
from pathlib import Path
import sys

URL = "https://github.com/resoarc/resoarc-site"
FOOTER_ANCHOR = '<a href="/sitemap.xml">サイトマップ</a>'
FOOTER_LINK = f'<a href="{URL}" rel="noopener noreferrer">GitHub・公開ソース</a>'
HOME_SECTION = f'''<section class="section inner-section"><div class="container split">
<div class="kicker"><span class="kicker-no">04</span><span class="kicker-en">OPEN SOURCE &amp; AI</span><span class="kicker-jp">公開と自由な検証</span></div>
<div><h2>中身まで、公開する。</h2>
<p class="section-lead">無償の技術を、誰でも読み、確かめ、育てられるように。</p>
<p>Webサイトとツールの公開ソース、変更履歴、検証手順をGitHubで公開しています。ResoArcが権利を持つコード・文章はMIT Licenseで提供し、AIによる解析、取り込み、改変にも利用できます。第三者素材にはそれぞれの条件が適用されます。</p>
<a class="inline-link" href="{URL}" rel="noopener noreferrer"><span>公開ソースと検証手順を見る</span><span aria-hidden="true">↗</span></a>
</div></div></section>
'''

def update(site: Path):
    if not (site / "index.html").exists():
        raise SystemExit(f"Not a static ResoArc site: {site}")
    touched = []
    for path in sorted(site.rglob("*.html")):
        old = path.read_text(encoding="utf-8")
        new = old
        if FOOTER_LINK not in new:
            if new.count(FOOTER_ANCHOR) != 1:
                raise SystemExit(f"Footer anchor missing or duplicated: {path}")
            new = new.replace(FOOTER_ANCHOR, FOOTER_ANCHOR + FOOTER_LINK, 1)
        rel = path.relative_to(site).as_posix()
        if rel == "index.html" and 'OPEN SOURCE &amp; AI' not in new:
            mark = '<section class="closing">'
            if new.count(mark) != 1:
                raise SystemExit("Closing section not found")
            new = new.replace(mark, HOME_SECTION + mark, 1)
        if rel == "project/index.html":
            new = new.replace('現在はWebサイトと初期ツールの公開に向けた準備段階です。',
                              '現在、Webサイトと初期ツールのソースを公開しています。実装と検証手順はGitHubから確認できます。')
        if rel == "license/index.html":
            mark = "<p><a href='/licenses/RESOARC-MIT.txt'>"
            link = f'<p><a class="inline-link" href="{URL}" rel="noopener noreferrer">公開ソース・ライセンス・AI利用方針をGitHubで確認する ↗</a></p>'
            if link not in new:
                if new.count(mark) != 1:
                    raise SystemExit("License link location not found")
                new = new.replace(mark, link + mark, 1)
        if new != old:
            path.write_text(new, encoding="utf-8", newline="")
            touched.append(rel)
    print(f"{site}: {len(touched)} HTML files changed")
    return touched

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        update(Path(arg))
