# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""One-time explicit-path mapping restore. New unrecognized media fail closed."""
import subprocess,re,json,collections,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
toml=root/'REUSE.toml'
source=toml.read_text('utf8').split('# New files audited for 2026-10-23; exact paths, no fallback globbing.')[0].rstrip()
old=set(json.loads('"'+s+'"') for s in re.findall(r'^\s*"(.*?)"\s*,?\s*$',source,re.M))
tracked=set(subprocess.check_output(['git','ls-files'],cwd=root).decode('utf8').splitlines())
added={x for x in ['scripts/prepare_reuse.py','scripts/audit_release_archives.py','docs/reuse-archive-inventory.json',
'scripts/reuse_release_gate.py','.github/workflows/reuse-compliance.yml','site/assets/reuse-status.js',
'site/recognition/reuse-status.json','docs/REUSE_COMPLIANCE.md','site/assets/reuse-status.css','scripts/prepare_reuse.py','scripts/check_signed_archive_notice.py','docs/CODEBERG_REUSE_ACTIONS_SETUP.md','docs/reuse-signed-archive-register.json','site/recognition/reuse-signed-archives.json','site/downloads/RESOARC_SIGNED_PLUGIN_LICENSE_NOTICE_20261023.md','docs/REUSE_LEGAL_REVIEW.json'] if (root/x).exists()}
code_ext={'.html','.css','.js','.json','.md','.txt','.py','.yml','.yaml','.xml','.mjs','.svg'}
groups=collections.defaultdict(list)
review=[]
for f in sorted((tracked|added)-old):
 p=root/f
 if not p.exists() or p.stat().st_size==0 or f in {'LICENSE','REUSE.toml'} or f.startswith('LICENSES/'):continue
 path=Path(f);ext=path.suffix.lower()
 label=None;holder='2026 ResoArc Open Technology Project'
 if f.startswith(('site/assets/kintone-settings-captures/','site/assets/development/')) and ext in {'.png','.webp','.jpg'}:
  label='LicenseRef-ResoArc-Screenshots'
 elif f.startswith('site/assets/recognition/') and ext in {'.svg','.png','.webp','.ico'}:
  label='LicenseRef-Service-Marks';holder='NOASSERTION'
 elif f.startswith('site/assets/') and (f.startswith('site/assets/resoarc-') or f.startswith('site/assets/glitter-planet-')) and ext in {'.png','.webp','.svg'}:
  label='LicenseRef-ResoArc-Brand-Art'
 elif f.startswith('site/downloads/') and ext=='.zip':
  label='MIT'
  review.append(f)
 elif ext in code_ext or f.startswith('site/downloads/') and ext in {'','.sha256'} or f=='site/_redirects':
  label='MIT'
 if not label:
  print('UNCLASSIFIED',f);sys.exit(2)
 groups[(label,holder)].append(f)
lic=(root/'LICENSES'/'LicenseRef-ResoArc-Brand-Art.txt')
lic.write_text('ResoArc original brand graphics and marks.\nCopyright (c) 2026 ResoArc Open Technology Project.\nThe website source MIT license does not automatically grant the right to present a\nResoArc name, logo or trademark as one’s own or imply endorsement. The underlying\nimage may contain AI-assisted artistic elements. Third-party rights are reserved.\n',encoding='utf8')
append=['','# New files audited for 2026-10-23; exact paths, no fallback globbing.']
for (label,holder),files in sorted(groups.items()):
 append.extend(['[[annotations]]','path = ['])
 append.extend('  '+json.dumps(x,ensure_ascii=False)+',' for x in files)
 append.extend([']','precedence = "override"','SPDX-FileCopyrightText = '+json.dumps(holder),'SPDX-License-Identifier = '+json.dumps(label),''])
toml.write_text((source.rstrip()+'\n'+'\n'.join(append)).rstrip()+'\n',encoding='utf8')
(root/'docs'/'REUSE_LEGAL_REVIEW.json').write_text(json.dumps({
 'status':'release_archives_require_separate_licensing_review',
 'explanation':'REUSE lint confirms file-level metadata; it does not grant redistribution rights or ensure ZIP contents carry notices.',
 'pending_archive_paths':review,'pending_count':len(review)},ensure_ascii=False,indent=2),encoding='utf8')
print('EXACT_PATHS_ANNOTATED',sum(map(len,groups.values())),'ADDITIONAL_ARCHIVE_REVIEW',len(review))
