#!/usr/bin/env python3
"""Integrate ResoArcOS into the GitHub-controlled Cloudflare Pages site/ tree.

Do not publish from a local dist/ folder: the GitHub-connected site/ is the
source of truth, and unrelated ResoArc tools are continuously updated there.
Preserves existing page contents; adds OS navigation and versioned assets.
"""
from pathlib import Path
import hashlib
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
SOURCE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else None
if SOURCE is None or not (SOURCE/"os"/"index.html").is_file():
    raise SystemExit("Usage: python scripts/integrate_resoarcos_site.py <verified-site-dist>")
assert SITE.is_dir()
zipfile=SOURCE/"downloads"/"resoarcos-pc-v0.1.0-dev-source.zip"
expected="72b427a8ef08ab388dc70ad2f1b14bcb2a7517b8f5edd0ebe67c8d934a93bb20"
assert hashlib.sha256(zipfile.read_bytes()).hexdigest()==expected,"Source ZIP checksum mismatch"
copy=[
    "os/index.html",
    "assets/resoarcos-20261016.css",
    "assets/fonts/noto-serif-jp-v10.woff2",
    "downloads/resoarcos-pc-v0.1.0-dev-source.zip",
    "downloads/resoarcos-pc-v0.1.0-dev-source.zip.sha256",
    "downloads/resoarcos-pc-v0.1.0-dev-iso-SHA256.txt",
]
for rel in copy:
    src=SOURCE/rel
    dst=SITE/rel
    assert src.is_file(),src
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)

desktop='<a href="/os/"><span>ResoArcOS</span><small>OS</small></a>'
mobile='<a href="/os/"><span>ResoArcOS</span><small>PC版</small></a>'
footer='<a href="/os/">ResoArcOS</a>'
pages=list(SITE.rglob("*.html"))
assert len(pages)>=30, "Expected all existing ResoArc tool pages"
changed=0
for file in pages:
    body=file.read_text(encoding="utf-8")
    original=body
    for start_tag,end_tag,addition in (
        ('<nav class="desktop-nav"','</nav>',desktop),
        ('<nav class="mobile-panel"','</nav>',mobile),
        ('<div class="footer-nav"','</footer>',footer),
    ):
        start=body.index(start_tag)
        end=body.index(end_tag,start)
        part=body[start:end]
        if addition not in part:
            if start_tag.startswith('<div'):
                anchor='<a href="/products/">'
                assert anchor in part,file
                part=part.replace(anchor,addition+anchor,1)
            else:
                part+=addition
            body=body[:start]+part+body[end:]
    assert 'href="/os/"' in body
    if body!=original:
        file.write_text(body,encoding="utf-8",newline="\n")
        changed+=1

sitemap=SITE/"sitemap.xml"
s=sitemap.read_text(encoding="utf-8")
entry='<url><loc>https://resoarc.com/os/</loc></url>'
if entry not in s:
    assert '</urlset>' in s
    s=s.replace('</urlset>',entry+'</urlset>')
    sitemap.write_text(s,encoding="utf-8",newline="\n")
llms=SITE/"llms.txt"
s=llms.read_text(encoding="utf-8")
entry='- https://resoarc.com/os/ : ResoArcOS PC developer preview (not production-ready)\n'
if entry not in s:
    s=s.rstrip()+"\n"+entry
    llms.write_text(s,encoding="utf-8",newline="\n")
assert len(list(SITE.rglob("*.html")))==len(pages)
print("INTEGRATED",len(pages),"pages, modified",changed,"OS source SHA256",expected)
