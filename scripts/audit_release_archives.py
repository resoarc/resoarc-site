# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Inventory release archive license indicators without treating this as a legal clearance."""
import sys,zipfile,re,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','ls-files','-z'],cwd=root).split(b'\0')
report=[]
for item in files:
 if not item:continue
 rel=item.decode('utf-8')
 if not rel.lower().endswith('.zip'):continue
 p=root/rel
 if not p.is_file():continue
 a={'path':rel,'size':p.stat().st_size,'archives_accessible':True}
 try:
  with zipfile.ZipFile(p) as z:
   names=z.namelist()
   a['entries']=len(names)
   a['license_files']=[x for x in names if re.search(r'(^|/)(license|copying|notice)(\.|$)',x,re.I)][:20]
   a['third_party_indicators']=[x for x in names if re.search(r'(^|/)(vendor|third.?party|node_modules|fonts)/',x,re.I)][:12]
   a['package_names']=[x for x in names if re.search(r'package\.json$|plugin\.json$|manifest\.json$',x,re.I)][:15]
   a['archive_license_review']='VERIFY_PER_ARCHIVE'
 except Exception as exc:
  a['archives_accessible']=False;a['error']=str(exc)
 report.append(a)
dest=root/'docs'/'reuse-archive-inventory.json'
dest.write_text(json.dumps({'note':'Automated technical inventory, not a grant of redistribution rights','archives':report},ensure_ascii=False,indent=2),encoding='utf8')
print('ARCHIVES',len(report),'NO_LICENSE_DOC',sum(not x.get('license_files') for x in report),'VENDOR_INDICATORS',sum(bool(x.get('third_party_indicators')) for x in report))
for x in report:
 if x.get('third_party_indicators') or not x.get('license_files'):
  print(('REVIEW '+x['path']+' FILES='+str(x.get('entries'))+' LICENSES='+str(len(x.get('license_files',[])))+' VENDOR='+str(len(x.get('third_party_indicators',[])))))
