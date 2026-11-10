# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Fail-closed REUSE 3.3 gate. Optionally output machine-readable evidence outside site root."""
import argparse,subprocess,sys,json,datetime,pathlib,os
root=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--report',default='')
args=parser.parse_args()
command=[sys.executable,'-m','reuse','lint','--json']
try:
 result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=180)
except Exception as exc:
 result=None
 data={'status':'error','cause':'reuse_tool_unavailable','detail':str(exc)}
else:
 try:
  detail=json.loads(result.stdout)
 except Exception:
  detail={'stdout':result.stdout[-6000:]}
 data={'status':'pass' if result.returncode==0 else 'fail','cause':'none' if result.returncode==0 else 'reuse_lint_failed',
       'exit_code':result.returncode,'details':detail,'stderr':result.stderr[-3000:]}
try: sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
except Exception: sha='unknown'
data.update({'target_commit':sha,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'spec_version':'3.3','tool_version':'6.2.0'})
if args.report:
 out=pathlib.Path(args.report);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(f"REUSE_GATE {data['status']} {sha[:12]} {data['cause']}")
if data['status']!='pass':
 print(json.dumps({k:data.get('details',{}).get(k) for k in ('summary','non_compliant','recommendations')} if isinstance(data.get('details'),dict) else data,ensure_ascii=False)[:4500])
 sys.exit(1)
