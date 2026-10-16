#!/usr/bin/env python3
"""Immutable v1.0.0 Web8 GA verifier, runs without kintone credentials or signing keys."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json, zipfile, sys
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
BASE='resoarc-web8-v1.0.0-source.zip'
PIN='d9bee5d112c706b322037d4c2a595d24d39148b1d84e00856732f48114526374'
ROUTES=['kintone-bulk-preview','kintone-app-diff','kintone-permission-audit','kintone-import-check','kintone-duplicates','kintone-lookup-audit','kintone-cross-aggregate','kintone-print-report']
def check():
 manifest=json.loads((SITE/'downloads/resoarc-web8-v1.0.0-manifest.json').read_text(encoding='utf8'))
 assert manifest['version']=='1.0.0' and manifest['scope']=='8 web utilities only'
 assert len(manifest['tools'])==8 and [v['path'].split('/')[2] for v in manifest['tools']]==ROUTES
 assert manifest['kintonePluginStatus'].startswith('NOT_GA')
 package=(SITE/'downloads'/BASE)
 digest=sha256(package.read_bytes()).hexdigest()
 assert digest==PIN==manifest['sha256'],'Immutable Web8 v1.0.0 ZIP bytes changed'
 assert (SITE/'downloads'/(BASE+'.sha256')).read_text(encoding='ascii')==f'{digest}  {BASE}\n'
 contents={v['path']:v['sha256'] for v in manifest['sources']}
 assert len(contents)==16 and 'LICENSE' in contents and 'docs/WEB8_V1_RELEASE.md' in contents
 with zipfile.ZipFile(package) as z:
  assert set(z.namelist())==set(contents)
  for name in z.namelist():
   path=PurePosixPath(name)
   assert not path.is_absolute() and '..' not in path.parts
   payload=z.read(name)
   assert sha256(payload).hexdigest()==contents[name]
   assert payload==(ROOT/name).read_bytes(),'Tracked source differs from frozen release: '+name
 for route in ROUTES:
  html=(SITE/'tools'/route/'index.html').read_text(encoding='utf8')
  assert 'data-resoarc-web-ga="1.0.0"' in html and '正式版' in html and 'アップロードしません' in html,route
 catalog=(SITE/'products/web/index.html').read_text(encoding='utf8')
 assert catalog.count('正式公開')>=8 and 'resoarc-web8-v1.0.0-source.zip' in catalog
 assert '/products/kintone/qa/' in (SITE/'products/kintone/index.html').read_text(encoding='utf8')
 print('WEB8_GA_V1_0_0_PASS',len(ROUTES),'Web apps,',len(contents),'frozen source files, hash',digest)
if __name__=='__main__':
 try:check()
 except (AssertionError,OSError,KeyError,ValueError,zipfile.BadZipFile) as exc:
  print('WEB8_GA_V1_0_0_FAIL',str(exc),file=sys.stderr);sys.exit(1)
