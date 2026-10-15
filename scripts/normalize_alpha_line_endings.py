#!/usr/bin/env python3
"""Keep alpha source trees LF-only before writing reproducible ZIP archives."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SLUGS=['conditional-format','date-calculator','list-search','grid-editor','kanban']
EXTENSIONS={'.json','.md','.js','.css','.html','.cjs','.txt'}
fixed=[]
for slug in SLUGS:
    folder=ROOT/'plugins'/slug/'v0.1.0-alpha'
    for path in folder.rglob('*'):
        if not path.is_file() or path.suffix not in EXTENSIONS:
            continue
        contents=path.read_bytes()
        normalized=contents.replace(b'\r\n',b'\n')
        if normalized!=contents:
            path.write_bytes(normalized)
            fixed.append(path.relative_to(ROOT).as_posix())
print('LF normalization:',len(fixed),'text files')
