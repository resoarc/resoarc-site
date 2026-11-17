#!/usr/bin/env python3
"""Strict direct dependency gate: nine original plugin manifests plus one reviewed RC mirror."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOC=(ROOT/'docs/DIRECT_DEPENDENCIES.md').read_text('utf8')
REVIEW=ROOT/'docs/compliance/SHEET_RC1_DIRECT_DEPENDENCIES_20261118.json'
OLD=(
 'plugins/auto-number/package.json',
 'plugins/auto-number/v1.1.0-beta/package.json',
 'plugins/conditional-format/v0.1.0-alpha/package.json',
 'plugins/conditional/v0.1.0-alpha/package.json',
 'plugins/date-calculator/v0.1.0-alpha/package.json',
 'plugins/grid-editor/v0.1.0-alpha/package.json',
 'plugins/kanban/v0.1.0-alpha/package.json',
 'plugins/list-search/v0.1.0-alpha/package.json',
 'plugins/tabs/v0.1.0-beta/package.json',
)
RC='apps/sheet/rc1-src/package.json'
LOCK='apps/sheet/rc1-src/package-lock.json'
errors=[]
def error(msg):errors.append(msg)
try:
 tracked=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines())
 packages={p for p in tracked if p.endswith('/package.json')}
 expected=set(OLD)|{RC}
 if packages!=expected:
  error('Unreviewed npm package manifests: added='+str(sorted(packages-expected))+' removed='+str(sorted(expected-packages)))
 for path in OLD:
  try:
   obj=json.loads((ROOT/path).read_text('utf8'))
   if path not in DOC:error('Legacy manifest lacks documentation: '+path)
   if obj.get('dependencies') or obj.get('devDependencies'):
    error('Originally dependency-free manifest now has dependencies: '+path)
  except Exception as e:error('Original manifest check failed '+path+': '+str(e))
 if RC not in DOC:error('RC manifest not documented: '+RC)
 if not REVIEW.is_file():error('Reviewed RC dependency inventory is missing')
 else:
  audit=json.loads(REVIEW.read_text('utf8'))
  if audit.get('manifest_path')!=RC or audit.get('lock_path')!=LOCK:error('Reviewed paths mismatch')
  if len(audit.get('direct_dependencies',[]))!=9:error('Reviewed direct dependency count changed')
  raw=(ROOT/RC).read_bytes();lockraw=(ROOT/LOCK).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=audit.get('manifest_sha256'):
   error('RC manifest changed: dependency review required')
  if hashlib.sha256(lockraw).hexdigest()!=audit.get('lock_sha256'):
   error('RC lockfile changed: dependency review required')
  manifest=json.loads(raw);lock=json.loads(lockraw)
  pkg=lock.get('packages',{})
  if manifest.get('private') is not True or manifest.get('version')!='1.0.0-rc.1':
   error('RC private/package identity changed')
  if lock.get('version')!=manifest.get('version') or pkg.get('',{}).get('version')!=manifest.get('version'):
   error('RC package/lock root version mismatch')
  if lock.get('lockfileVersion')!=audit.get('lockfileVersion'):error('RC lockfileVersion drift')
  if len(pkg)!=audit.get('lock_package_entries'):error('RC locked package count drift')
  reviewed={(x['role'],x['name']):x for x in audit['direct_dependencies']}
  actual={}
  for role,key in [('runtime','dependencies'),('development','devDependencies')]:
   for name,spec in manifest.get(key,{}).items():
    actual[(role,name)]=spec
    if (role,name) not in reviewed:
     error('New direct dependency: '+role+' '+name);continue
    x=reviewed[(role,name)];record=pkg.get('node_modules/'+name,{})
    if spec!=x['manifest_spec'] or record.get('version')!=x['locked_version']:
     error('RC dependency spec/locked version drift: '+name)
    if record.get('integrity')!=x['lock_integrity'] or record.get('resolved')!=x['lock_registry_url']:
     error('RC dependency integrity/registry drift: '+name)
  if set(actual)!=set(reviewed):
   error('Reviewed direct dependency set mismatch')
except Exception as e:
 error('Dependency gate exception: '+type(e).__name__+': '+str(e))
print('Npm package manifests: ',len(packages))
print('RC directly reviewed runtime/dev dependencies: 7/2, SHA-256 and npm SRI pinned')
for item in errors:print('FAIL:',item,file=sys.stderr)
sys.exit(1 if errors else 0)
