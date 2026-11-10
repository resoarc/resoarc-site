#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Deterministic qAIUIck 0.4 beta source package, layering v0.3 without mutation."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
import json

root=Path(__file__).resolve().parents[1]
site=root/'site'
old=site/'downloads/qaiuick-v0.3-beta-source.zip'
target=site/'downloads/qaiuick-v0.4-beta-source.zip'
old_prefix='qAIUIck-v0.3-beta/'
prefix='qAIUIck-v0.4-beta/'
files={}
with ZipFile(old) as z:
    if z.testzip() is not None:raise ValueError('Source v0.3 archive corrupt')
    for name in z.namelist():
        if name.endswith('/') or not name.startswith(old_prefix):raise ValueError('Unexpected archive entry '+name)
        dest=prefix+name[len(old_prefix):]
        content=z.read(name)
        if name.endswith('/README.md'):
            content=content.decode('utf8').replace('v0.3','v0.4').encode('utf8')
        if name.endswith('/package.json'):
            pkg=json.loads(content.removesuffix(bytes((92, 110))))
            pkg['version']='0.4.0'
            pkg['scripts']['check']+=' && node --check src/spec.js && node --check src/define.js'
            content=(json.dumps(pkg,ensure_ascii=False,indent=2)+'\n').encode('utf8')
        files[dest]=content

for name in ('spec.js','define.js','define.css'):
    files[prefix+'src/'+name]=(site/'assets/qaiuick'/name).read_bytes()
files[prefix+'docs/SPEC_FIRST.md']=(root/'docs/QAIUICK_SPEC_FIRST.md').read_bytes()
cli=(root/'tools/qaiuick_spec.mjs').read_text('utf8').replace('../site/assets/qaiuick/spec.js','../src/spec.js')
files[prefix+'tools/qaiuick_spec.mjs']=cli.encode('utf8')
for demo in ('inventory','tickets'):
    demo_root=site/'assets/qaiuick-spec'
    files[prefix+f'examples/spec-{demo}/spec.js']=(demo_root/(demo+'.spec.js')).read_bytes()
    files[prefix+f'examples/spec-{demo}/baseline.json']=(demo_root/('baseline-'+demo+'.json')).read_bytes()
    files[prefix+f'examples/spec-{demo}/main.js']=(f"import {{ defineApp }} from '../../src/define.js';\nimport {{ spec }} from './spec.js';\ndefineApp({{ ...spec, baseline: './baseline.json' }});\n").encode('utf8')
    files[prefix+f'examples/spec-{demo}/index.html']=(f'''<!doctype html>
<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>qAIUIck Spec-first {demo}</title>
<link rel="stylesheet" href="../../src/qaiuick.css">
<link rel="stylesheet" href="../../src/define.css">
<main class="q-page"><div id="app"></div></main>
<script type="module" src="./main.js"></script>
</html>''').encode('utf8')
readme=prefix+'README.md'
files[readme]+=('''

## Spec-first UI generator (v0.4)

The new `defineApp()` produces forms, search, tables, validation, local
persistence, and a JSON design inspector from one specification.
Open `examples/spec-inventory/index.html` through a local web server.
See `docs/SPEC_FIRST.md` for custom action hooks and AI review.
Generate a snapshot with
`node tools/qaiuick_spec.mjs snapshot examples/spec-inventory/spec.js baseline.json`.
`quickApp()`, `createApp()`, and `createStore()` remain compatible.
''').encode('utf8')
with ZipFile(target,'w',compression=ZIP_DEFLATED,compresslevel=9) as z:
    for name,content in sorted(files.items()):
        info=ZipInfo(name,date_time=(2026,11,10,0,0,0))
        info.compress_type=ZIP_DEFLATED
        info.external_attr=0o644<<16
        z.writestr(info,content,compress_type=ZIP_DEFLATED,compresslevel=9)
content=target.read_bytes()
digest=sha256(content).hexdigest()
(target.with_suffix(target.suffix+'.sha256')).write_text(f'{digest}  {target.name}\n','ascii',newline='\n')
with ZipFile(target) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(files)
    assert z.read(prefix+'src/define.js')==(site/'assets/qaiuick/define.js').read_bytes()
    assert json.loads(z.read(prefix+'package.json'))['version']=='0.4.0'
print('QAIUICK_V04_BUNDLE_OK',len(files),'files',len(content),'bytes','SHA256',digest)
