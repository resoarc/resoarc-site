#!/usr/bin/env python3
"""Build deterministic UNSIGNED ResoArc mini v1 candidate sources only.
Never creates signing keys, plugin ZIPs or kintone deployments.
"""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import hashlib, json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'resoarc-mini-v1-mobile16-source-only-20261017.zip'
METADATA=OUT.with_suffix('.qa.json')
for cmd in ([sys.executable,'scaffold.py'],[sys.executable,'bundle_qr.py']):
    subprocess.run(cmd,cwd=ROOT,check=True,timeout=40)
slugs=[p for p in sorted((ROOT/'plugins').iterdir()) if p.is_dir()]
if len(slugs)!=18:raise RuntimeError('Expected exactly 18 mini plugins')
mobile=[]
js_files=[]
for p in slugs:
    m=json.loads((p/'manifest.json').read_text(encoding='utf-8'))
    for section in ('desktop','config','mobile'):
        for category in ('js','css','html'):
            names=m.get(section,{}).get(category,[])
            if isinstance(names,str):names=[names]
            for name in names:
                f=p/name
                if not f.is_file():raise RuntimeError(f'Missing asset: {f}')
    if m.get('mobile'):mobile.append(p.name)
    js_files.extend(p.glob('js/*.js'))
expected=set(['attachment-count','barcode-scan','csv-export','field-help','file-preview','input-template','list-aggregate','lookup-suggest','mail-compose','postal-address','qr-code','record-toc','related-links','reuse-reset','table-row-tools','text-normalizer'])
if set(mobile)!=expected or len(mobile)!=16:raise RuntimeError('Expected precisely 16 approved mobile source candidates')
for f in js_files:
    subprocess.run(['node','--check',str(f)],check=True,timeout=10,capture_output=True)
if (ROOT/'private').exists() or (ROOT/'release').exists():
    raise RuntimeError('Signing secrets or signed distribution found: unsafe source packaging')
allowed=set(['LICENSE','README.md','RELEASE-NOTES-v0.1.2.md','V1-CANDIDATE-STATUS.md',
'catalog.json','release-manifest.json','scaffold.py','package.py','bundle_qr.py',
'site_build.py','build.sh'])
items=[]
for name in ('plugins','runtimes','tests','vendor','scripts'):
    for p in (ROOT/name).rglob('*'):
        if p.is_file() and not any(x in p.parts for x in ('__pycache__','.git','private','release','node_modules')) and not p.name.endswith(('.pyc','.log')):
            items.append(p)
for name in allowed:
    p=ROOT/name
    if p.is_file():items.append(p)
paths=sorted({p.relative_to(ROOT).as_posix():p for p in items}.items())
if len(paths)<150:raise RuntimeError('Missing source files')
with ZipFile(OUT,'w',compression=ZIP_DEFLATED,compresslevel=9) as z:
    for name,p in paths:
        data=p.read_bytes()
        if len(data)>2_000_000:raise RuntimeError('Unexpected large source item')
        entry=ZipInfo(name,date_time=(2026,10,17,0,0,0))
        entry.compress_type=ZIP_DEFLATED
        entry.external_attr=(0o100644<<16)
        z.writestr(entry,data,compress_type=ZIP_DEFLATED,compresslevel=9)
with ZipFile(OUT) as z:
    if len(z.namelist())!=len(paths):raise RuntimeError('Zip entry count mismatch')
    for name,p in paths:
        if z.read(name)!=p.read_bytes():raise RuntimeError('Zip entry content mismatch '+name)
result={
 'status':'unsigned_source_only_not_a_kintone_installable_plugin',
 'path':str(OUT),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),
 'file_count':len(paths),'mini_products':len(slugs),
 'javascript_files':len(js_files),'missing_assets':0,
 'mobile_draft_features':mobile,'mobile_candidate_count':16,'signed':False,'v1_release_approved':False,
 'original_beta_untouched':True,'tenant_e2e':False
}
METADATA.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
