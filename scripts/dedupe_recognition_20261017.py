from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
f=root/"site/index.html"
s=f.read_text(encoding="utf-8")
p=r'<article class="[^"]*\brec-green-card\b[^"]*">.*?</article>\s*'
m=list(re.finditer(p,s,re.S))
print("GREEN_CARDS_BEFORE",len(m))
assert len(m)>=1
for x in reversed(m[1:]):
    s=s[:x.start()]+s[x.end():]
f.write_text(s,encoding="utf-8",newline="")
helper=root/"scripts/add_greenweb_evidence_20261017.py"
old=helper.read_text(encoding="utf-8")
old=old.replace("card+anchor,'class=\"rec-green-card\"')","card+anchor,'rec-green-card')")
helper.write_text(old,encoding="utf-8",newline="")
from bs4 import BeautifulSoup
h=BeautifulSoup(s,"html.parser")
cards=h.select(".rec-hub-quality-grid > article")
counts=[len(h.select(".rec-green-card")),len(h.select(".rec-ssllabs-card")),len(h.select(".rec-internetnl-card"))]
print("TOTAL_CARDS",len(cards),"COUNTS_GREEN_SSL_INTERNET",counts)
assert len(cards)==6 and counts==[1,1,1]
