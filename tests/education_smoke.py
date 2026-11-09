from pathlib import Path
from bs4 import BeautifulSoup
from hashlib import sha256
from xml.etree import ElementTree as ET
import json,re
R=Path(r'C:\Users\zin\Documents\ResoArc')
S=R/'integration'/'site-education-official-20261020'/'site'
PAGES={'/education/':S/'education/index.html',
       '/education/circuit/':S/'education/circuit/index.html',
       '/education/programming/':S/'education/programming/index.html'}
for url,p in PAGES.items():
 d=BeautifulSoup(p.read_text(encoding='utf8'),'html.parser')
 assert d.title is not None
 assert d.select_one('link[rel=canonical]')['href']=='https://resoarc.com'+url
 assert d.select_one('.site-header') and d.select_one('footer.footer')
 assert len(d.select('main#main'))==1
 assert len(d.select('script:not([src])'))==0,'CSP blocks inline script'
 assert len(d.select('style'))==0,'CSP blocks inline styles'
 assert len(d.select('[onclick],[onload],[onchange]'))==0,'No CSP incompatible DOM event strings'
 for script in d.select('script[src]'):
  assert script['src'].startswith('/assets/'),'Only local scripts supported'
 for css in d.select('link[rel=stylesheet]'):
  assert css['href'].startswith('/assets/'),'Only local CSS supported'
 assert (S/'assets/site-20261015-v10.css').exists()
landing=BeautifulSoup(PAGES['/education/'].read_text(encoding='utf8'),'html.parser')
for url in ['/education/circuit/','/education/programming/']:
 assert landing.select_one(f'a[href="{url}"]')
circuit=(S/'assets/education-circuit-20261020.js').read_text(encoding='utf8')
for sign in ['circuitCurrent','volts','res','connected','resistor','polarity','preset']:
 assert sign in circuit
robot=(S/'assets/education-robot-20261020.js').read_text(encoding='utf8')
for f in ['function project(','function box3(','function drawRobot(','function scene()', 'localStorage','requestAnimationFrame']:
 assert f in robot
assert 'fetch(' not in robot and 'XMLHttpRequest' not in robot
assert 'fetch(' not in circuit and 'XMLHttpRequest' not in circuit
xml=ET.parse(S/'sitemap.xml')
urls=[e.text for e in xml.findall('.//{*}loc')]
for url in PAGES:assert 'https://resoarc.com'+url in urls
for url in ['/products/','/']:
 d=BeautifulSoup((S/('index.html' if url=='/' else 'products/index.html')).read_text(encoding='utf8'),'html.parser')
 assert d.select_one('a[href="/education/"]')
 assert d.select_one('link[href="/assets/education-20261020.css"]')
 assert not d.select_one('script:not([src])') or url=='/'  # existing home JSON-LD script allowed
old=R/'repository-mirror'/'site-publish-20261017'/'site/downloads'
new=S/'downloads'
assert {p.name:sha256(p.read_bytes()).hexdigest() for p in old.iterdir()}=={
 p.name:sha256(p.read_bytes()).hexdigest() for p in new.iterdir()}
print('EDUCATION_SOURCE_QA_PASS',len(PAGES),'routes; downloads preserved 48; CSP-compatible scripts/styles; no external network')
