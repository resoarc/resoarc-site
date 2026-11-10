#!/usr/bin/env python3
"""Turn Cloudflare runtime email obfuscation back into author-source links before Pages upload."""
from pathlib import Path
import re,html,requests
root=Path(__file__).resolve().parents[1]/"site"
def decode(encoded):
    data=bytes.fromhex(encoded)
    return bytes(n^data[0] for n in data[1:]).decode("utf-8")
found=[]
for p in root.rglob("*.html"):
    original=p.read_text(encoding="utf-8")
    def repl(match):
        block=match.group()
        token=re.search(r'data-cfemail=["\x27]([a-f0-9]+)["\x27]',block,re.I)
        assert token,(p,block[:80])
        email=decode(token.group(1))
        assert email.lower().endswith("@resoarc.com"), (str(p),email)
        found.append((p.relative_to(root).as_posix(),email))
        return '<a href="mailto:'+html.escape(email,quote=True)+'">'+html.escape(email)+'</a>'
    updated=re.sub(r'<a\b[^>]*href="/cdn-cgi/l/email-protection[^"]*"[^>]*>.*?</a>',repl,original,flags=re.S|re.I)
    updated=re.sub(r'<script\b[^>]*src="/cdn-cgi/scripts/[^"]*email-decode\.min\.js"[^>]*></script>',"",updated,flags=re.I)
    if updated!=original:
        p.write_text(updated,encoding="utf-8",newline="")
    assert "/cdn-cgi/l/email-protection" not in updated, p
print("DEOBFUSCATED",found)
# This Cloudflare-controlled endpoint is not an authored site asset.
runtime=root/"cdn-cgi"
if runtime.exists():
    for file in sorted(runtime.rglob("*"),reverse=True):
        if file.is_file():file.unlink()
        elif file.is_dir():file.rmdir()
    runtime.rmdir()
    print("REMOVED_RUNTIME_CDN_CGI_ASSETS")
res=requests.get("https://resoarc.com/.well-known/security.txt",timeout=15)
res.raise_for_status()
assert "Contact: mailto:security@resoarc.com" in res.text
target=root/".well-known"/"security.txt"
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(res.content)
print("SECURITY_POLICY_SYNCED",len(res.content))
