#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Build a deterministic qAIUIck v0.3 beta source archive from existing v0.2 + Quick API.

This does not overwrite or mutate the immutable v0.2 distribution.
"""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from io import BytesIO
import sys

root=Path(__file__).resolve().parents[1]
site=root/'site'
old=site/'downloads/qaiuick-v0.2-beta-source.zip'
new=site/'downloads/qaiuick-v0.3-beta-source.zip'
prefix0='qAIUIck-v0.2-beta/'
prefix1='qAIUIck-v0.3-beta/'
entries={}
with ZipFile(old) as src:
    if src.testzip() is not None: raise RuntimeError('Original ZIP corrupt')
    for name in src.namelist():
        if not name.startswith(prefix0) or name.endswith('/'):
            raise RuntimeError('Unexpected original package item: '+name)
        path=prefix1+name[len(prefix0):]
        raw=src.read(name)
        if path.endswith('README.md'):
            raw=(raw.decode('utf-8').replace('v0.2','v0.3')+
                 '\n\n## Quick API v0.3 (recommended for tiny apps)\n\n'
                 'Start with `examples/quick-todo/`; see `docs/QUICK_API.md`. '
                 'The legacy `createApp` and `createStore` APIs remain supported.\n').encode('utf-8')
        entries[path]=raw

entries[prefix1+'src/quick.js']=(site/'assets/qaiuick/quick.js').read_bytes()
entries[prefix1+'docs/QUICK_API.md']=(root/'docs/QAIUICK_QUICK_API.md').read_bytes()
entries[prefix1+'examples/quick-todo/index.html']=b'''<!doctype html>
<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>qAIUIck Quick Todo</title><link rel="stylesheet" href="../../src/qaiuick.css">
<main id="app" class="q-page">
  <h1>Quick Todo</h1>
  <section class="q-panel q-stack">
    <h2>Todo <span q-text="count"></span></h2>
    <form q-submit="add" class="q-form">
      <label>Memo <input q-model="draft" required></label>
      <button>\xe8\xbf\xbd\xe5\x8a\xa0</button>
    </form>
    <ul class="q-list"><template q-each="items" q-as="item">
      <li><span q-text="item.title"></span><button q-action="remove" q-arg="item.id">\xe5\x89\x8a\xe9\x99\xa4</button></li>
    </template></ul>
    <p q-show="empty">\xe3\x81\xbe\xe3\x81\xa0\xe3\x83\xa1\xe3\x83\xa2\xe3\x81\xaf\xe3\x81\x82\xe3\x82\x8a\xe3\x81\xbe\xe3\x81\x9b\xe3\x82\x93</p>
  </section>
</main><script type="module" src="./main.js"></script>
'''
entries[prefix1+'examples/quick-todo/main.js']=b'''import { quickApp } from '../../src/quick.js';
quickApp({
  key: 'example-quick-todo',
  data: { draft: '' },
  sample: [{ id: 'hello', title: 'Try qAIUIck' }],
});
'''
if len(entries)!=len(set(entries)):raise RuntimeError('Duplicate archive items')
with ZipFile(new,'w',compression=ZIP_DEFLATED,compresslevel=9) as dst:
    for name,data in sorted(entries.items()):
        zi=ZipInfo(name,date_time=(2026,11,10,0,0,0))
        zi.compress_type=ZIP_DEFLATED
        zi.external_attr=0o644 << 16
        dst.writestr(zi,data,compress_type=ZIP_DEFLATED,compresslevel=9)
blob=new.read_bytes()
digest=sha256(blob).hexdigest()
(new.with_suffix(new.suffix+'.sha256')).write_text(f'{digest}  {new.name}\n',encoding='ascii',newline='\n')
with ZipFile(new) as check:
    assert check.testzip() is None
    assert check.read(prefix1+'src/quick.js')==(site/'assets/qaiuick/quick.js').read_bytes()
    assert check.read(prefix1+'docs/QUICK_API.md')==(root/'docs/QAIUICK_QUICK_API.md').read_bytes()
    assert len(check.namelist())==len(entries)
print('QAIUICK_PACKAGE_OK', 'entries',len(entries),'bytes',len(blob),'sha256',digest)
