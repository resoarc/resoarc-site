#!/usr/bin/env python3
"""Verify that published alpha-source ZIPs exactly match audited repository source."""
import sys,json
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
SLUGS=['conditional-format','date-calculator','list-search','grid-editor','kanban']
failures=[]
for slug in SLUGS:
    folder=ROOT/'plugins'/slug/'v0.1.0-alpha'
    manifest=json.loads((folder/'src/manifest.json').read_text(encoding='utf-8'))
    if manifest['config']['js']!=['js/core.js','js/config.js']:
        failures.append(slug+': config core load order is invalid')
    if 'rule-list' not in (folder/'src/html/config.html').read_text(encoding='utf-8'):
        failures.append(slug+': missing form')
    archive=ROOT/'site/downloads'/f'resoarc-{slug}-v0.1.0-alpha-source.zip'
    expected={f'{slug}-v0.1.0-alpha/'+file.relative_to(folder).as_posix():file.read_bytes()
              for file in folder.rglob('*') if file.is_file() and file.suffix!='.pyc'}
    with ZipFile(archive) as z:
        names=z.namelist()
        if set(names)!=set(expected):
            failures.append(slug+': archive file list differs from source')
        for name in names:
            if name.startswith('/') or '..' in Path(name).parts:
                failures.append(slug+': unsafe zip path '+name)
            if name in expected and z.read(name)!=expected[name]:
                failures.append(slug+': archive content differs '+name)
    print(f'{slug}: {len(expected)} source files verified')
if failures:
    print('FAIL:',*failures,sep='\n - ')
    sys.exit(1)
print('PASS: five alpha source archives exactly match the repository')
