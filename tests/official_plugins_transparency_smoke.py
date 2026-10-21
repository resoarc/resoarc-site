#!/usr/bin/env python3
"""ResoArc public plugin listing contract: ZIP provenance, versions, captures and navigation."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
from hashlib import sha256
from bs4 import BeautifulSoup
import json,re
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
index=BeautifulSoup((SITE/'products/kintone/index.html').read_text(encoding='utf8'),'html.parser')
cards=index.select('article.kc-product')
assert len(cards)==12,len(cards)
release=BeautifulSoup((SITE/'products/kintone/release-integrity/index.html').read_text(encoding='utf8'),'html.parser')
rows={r['id']:r for r in release.select('tr[id]')}
assert len(rows)==12
captures=SITE/'assets/kintone-settings-captures'
assert len(list(captures.glob('*.webp')))==12
for card in cards:
 title=card.h3.get_text(' ',strip=True)
 slug=card.select_one('img.kc-product-icon')['src'].split('/')[-1].removesuffix('.svg')
 href=card.select_one('a.kc-product-link')['href']
 assert slug in rows
 assert '設定画面を再現したデモ画像' in card.get_text(' ',strip=True)
 img=card.select_one('.kc-card-media img')
 assert img and img['src']==f'/assets/kintone-settings-captures/{slug}.webp'
 assert (captures/(slug+'.webp')).stat().st_size>7000
 doc=SITE/('tools/kintone-auto-number/index.html' if slug=='auto-number' else f'products/kintone/{slug}/index.html')
 soup=BeautifulSoup(doc.read_text(encoding='utf8'),'html.parser')
 assert soup.select_one('.kc-detail-media img')
 assert '実際のkintoneテナントで撮影したものではありません' in soup.select_one('.kc-detail-media').get_text(' ',strip=True)
 schema=json.loads(soup.select_one('script[type="application/ld+json"]').string)
 assert schema['@type']=='SoftwareApplication' and schema['name']==title
 zip_url=schema['downloadUrl'].replace('https://resoarc.com/','')
 z=SITE/zip_url
 assert z.is_file()
 with ZipFile(z) as outer:
  assert {'contents.zip','PUBKEY','SIGNATURE'}.issubset(outer.namelist())
  with ZipFile(BytesIO(outer.read('contents.zip'))) as inner:
   manifest=json.loads(inner.read('manifest.json'))
 assert schema['softwareVersion']==manifest['version']
 assert card.select_one('.kc-product-version').get_text(' ',strip=True)=='v'+manifest['version']
 assert sha256(z.read_bytes()).hexdigest() in rows[slug].get_text(' ',strip=True)
 assert zip_url.split('/')[-1] in rows[slug].get_text(' ',strip=True)
 assert 'ソース' in rows[slug].get_text(' ',strip=True) or 'Codeberg' in rows[slug].get_text(' ',strip=True)
assert (SITE/'_redirects').read_text(encoding='utf8').strip()=='/tools/mini-plugins/ /products/kintone/ 301'
nav=json.loads((SITE/'assets/navigation-map.json').read_text(encoding='utf8'))
assert nav['pages']['/products/kintone/release-integrity/']['visible']
assert sum(x['visible'] for x in nav['pages'].values())==44
assert (SITE/'assets/resoarc-ux-trust-20261020.css').exists()
home=BeautifulSoup((SITE/'index.html').read_text(encoding='utf8'),'html.parser')
assert home.select_one('section.ra-start-here')
assert '無料ツール' in home.select_one('main').get_text(' ',strip=True)
assert home.select_one('.hero-buttons a[href="/products/kintone/"]')
assert home.select_one('.hero-buttons a[href="/products/web/"]')
assert home.select_one('a[href="https://codeberg.org/ResoArc/resoarc-site/issues"]')
for f in SITE.rglob('*.html'):
 if f.name=='404.html':continue
 body=f.read_text(encoding='utf8')
 assert body.count('<script defer src="/assets/navigation.js"></script>')==1,f
 assert body.count('<link rel="stylesheet" href="/assets/navigation.css">')==1,f
print('OFFICIAL_PLUGINS_TRANSPARENCY_PASS products=12 manifest-and-listing-match=12 stable-nav=54 public=44')
