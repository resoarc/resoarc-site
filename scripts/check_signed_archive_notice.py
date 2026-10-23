# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Reproducible signed plugin outer/inner inventory and SHA256 release gate.

Does not edit ZIPs, and does not claim cryptographic signature validation.
Previously published files can have separate-license review pending, but a
changed signed binary or unregistered new signed ZIP fails the gate.
"""
from pathlib import Path
import sys,hashlib,zipfile,io,re,json
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'docs/reuse-signed-archive-register.json'
def digest(blob):return hashlib.sha256(blob).hexdigest()
def scan(path):
    with zipfile.ZipFile(path) as outer:
        names=set(outer.namelist())
        if not {'contents.zip','PUBKEY','SIGNATURE'}.issubset(names):return None
        payload=outer.read('contents.zip')
        with zipfile.ZipFile(io.BytesIO(payload)) as nested:
            inner_files=nested.namelist()
            licenses=[n for n in inner_files if re.search(r'(^|/)(LICENSE|COPYING|NOTICE)(\.|$)',n,re.I)]
            code=[n for n in inner_files if n.endswith(('.js','.css','.html','.json'))]
            spdx=[n for n in code if b'SPDX-License-Identifier:' in nested.read(n)[:4096]]
            srcs=[n for n in code if any(s in nested.read(n).lower() for s in [b'fflate',b'lodash',b'jquery'])]
            return {'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path.read_bytes()),
              'payload_sha256':digest(payload),'contains_signature_files':True,
              'signature_cryptographically_verified':False,'inner_count':len(inner_files),
              'license_files_inside_signed_payload':licenses,'source_files_with_spdx':spdx,
              'third_party_code_signals':srcs,
              'notice_state':'pending_separate_license_evidence' if not licenses else 'embedded_notice_present',
              'source_contents_not_modified':True}
def current():
    out={}
    for p in (ROOT/'site/downloads').glob('*.zip'):
        r=scan(p)
        if r:out[r['path']]=r
    return out
def main():
    actual=current()
    if '--init' in sys.argv:
        assert not DB.exists(), 'Cannot overwrite established baseline'
        report={'schema_version':1,'description':'Immutable signed kintone wrapper inventory; missing license text needs outside notice review, not ZIP mutation.',
          'base_commit':'59c03114e5088825fc0941dd26f8b717261c9bee',
          'files':list(actual.values())}
        DB.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print('ARCHIVE_BASELINE_CREATED',len(actual));return 0
    if not DB.exists():print('ARCHIVE_REGISTER_MISSING');return 2
    registered=json.loads(DB.read_text('utf8'))
    baseline={x['path']:x for x in registered['files']}
    added=sorted(set(actual)-set(baseline))
    lost=sorted(set(baseline)-set(actual))
    changed=[p for p in actual if p in baseline and (
        actual[p]['sha256']!=baseline[p]['sha256'] or
        actual[p]['payload_sha256']!=baseline[p]['payload_sha256'])]
    if added or lost or changed:
        print('SIGNED_ARCHIVE_GATE_FAIL',json.dumps({'unregistered_new':added,'removed':lost,'changed_signatures_or_payload':changed},ensure_ascii=False));return 1
    pending=[x for x in actual.values() if x['notice_state']=='pending_separate_license_evidence']
    print('SIGNED_ARCHIVE_GATE_PASS registered='+str(len(actual))+
        ' unchanged='+str(len(actual))+' pending_internal_notices='+str(len(pending))+
        ' note=metadata_only_not_signature_or_license_validation')
    return 0
if __name__=='__main__':sys.exit(main())
