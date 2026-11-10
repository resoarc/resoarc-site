from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
os=ROOT/"site/os/index.html"
html=os.read_text(encoding="utf-8")
pattern=r'<p><a\s+class="inline-link"\s+href="/source/#os">[^<]*</a></p>'
found=re.findall(pattern,html)
assert len(found)==2,("Expected 2 redirected ISO links, found",len(found))
ISO="https://github.com/resoarc/resoarc-site/releases/download/resoarcos-pc-v0.1.0-dev-20261016/resoarcos-pc-v0.1.0-dev-amd64.iso"
replacement=(
'<p class="source-note">過去のISO配布先（現在アクセスできません）：'
'<code class="source-url">'+ISO+'</code></p>'
'<p><a class="inline-link" href="/source/#os">代替ソースZIPと提供状況を見る ↗</a></p>'
)
html=re.sub(pattern, lambda m: replacement if m.start()==re.search(pattern,html).start() else "", html,count=2)
os.write_text(html,encoding="utf-8")
css=ROOT/"site/assets/site-20261015-v10.css"
txt=css.read_text(encoding="utf-8")
if ".source-url{" not in txt:
 txt+='\n.source-url{white-space:normal;overflow-wrap:anywhere;word-break:break-word;font-size:11px}\n'
 css.write_text(txt,encoding="utf-8")
print("OS_SOURCE_STATUS_FIXED")
