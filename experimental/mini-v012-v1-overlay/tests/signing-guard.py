import sys,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if (root/'private').exists() or (root/'release').exists():raise RuntimeError('Unexpected output dirs before test')
r=subprocess.run([sys.executable,'package.py'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace',timeout=20)
if r.returncode==0:raise RuntimeError('Signing unexpectedly succeeded')
if not ('Missing ORIGINAL signing key' in r.stderr):raise RuntimeError('Wrong signing failure type: '+r.stderr[-500:])
if (root/'private').exists() or (root/'release').exists():raise RuntimeError('Signing wrote data before rejection')
print(json.dumps({'fail_closed':True,'return_code':r.returncode,'created_private_keys':False,'created_distribution':False}))
