#!/usr/bin/env python3
"""Loopback-only TrapNet black-box lab. NOT a five-host or LAN-isolation test."""
import argparse
import json
import os
import pathlib
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

URL = 'http://127.0.0.1:8788'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=str(pathlib.Path(__file__).parents[1]))
    ap.add_argument('--out', default='')
    args = ap.parse_args()
    src = pathlib.Path(args.source).resolve()
    results = []
    def record(name, passed, detail):
        results.append({'test': name, 'pass': bool(passed), 'detail': detail})
        print(('PASS' if passed else 'FAIL') + ' ' + name + ' | ' + detail, flush=True)
        if not passed: raise AssertionError(name + ': ' + detail)
    with tempfile.TemporaryDirectory(prefix='trapnet-blackbox-') as tmp:
        work = pathlib.Path(tmp)
        exe = '.exe' if os.name == 'nt' else ''
        bins = {}
        for name in ['hub','sensor','keygen','revoke-sign','feed-sign','guardian','witness','recovery-check']:
            path = work / (name + exe)
            cp = subprocess.run(['go', 'build', '-o', str(path), './cmd/'+name], cwd=src, capture_output=True, text=True, timeout=180)
            record('build_'+name, cp.returncode == 0, cp.stderr[-300:] or 'compiled')
            bins[name] = path
        def run(name,*argv,should=0):
            cp = subprocess.run([str(bins[name]), *[str(a) for a in argv]], cwd=work,
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=20)
            if should is not None and cp.returncode!=should:
                raise AssertionError(name+': exit='+str(cp.returncode)+' out='+cp.stdout[-400:]+' err='+cp.stderr[-400:])
            return cp
        identities=[]
        for i in range(5):
            d=work/('sensor-'+str(i))
            run('keygen','-out',d)
            identities.append({'dir':d,**json.loads((d/'node.json').read_text())})
        feedkey=work/'feedkey'; revkey=work/'revkey'; witnesskey=work/'witnesskey'
        for key in (feedkey,revkey,witnesskey):run('keygen','-out',key)
        allow={n['node_id']:n['public_key'] for n in identities}
        (work/'allowlist.json').write_text(json.dumps(allow))
        v1=work/'revocations-v1.json'; live=work/'revocations.json';v2=work/'revocations-v2.json'
        run('revoke-sign','-key',revkey/'private.hex','-version','1','-out',v1)
        shutil.copyfile(v1,live)
        ledger=work/'ledger.jsonl'
        hub_cmd=[str(bins['hub']),'-allowlist',str(work/'allowlist.json'),'-ledger',str(ledger),
                 '-signed-revocations',str(live),'-revocation-root',str(revkey/'public.hex')]
        # Refuse to use a port owned by another local program.
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', 8788))
        hub = None
        def start_hub():
            nonlocal hub
            hub=subprocess.Popen(hub_cmd,cwd=work,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if hub.poll() is not None:
                    out,err=hub.communicate(timeout=1)
                    raise RuntimeError('HUB startup: '+err.decode(errors='replace')[-500:])
                try:
                    with urllib.request.urlopen(URL+'/health',timeout=.5) as response:
                        if response.status==200:return
                except (OSError,urllib.error.URLError):time.sleep(.08)
            raise RuntimeError('HUB did not become healthy')
        def post(payload,content_type='application/json'):
            req=urllib.request.Request(URL+'/report',data=payload,headers={'Content-Type':content_type},method='POST')
            try:
                with urllib.request.urlopen(req,timeout=5) as r:return r.status
            except urllib.error.HTTPError as err:return err.code
        try:
            start_hub()
            record('hub_loopback_health',True,'GET /health -> 200')
            sensor_procs=[subprocess.Popen([str(bins['sensor']),'-key',str(n['dir']/'private.hex'),'-fingerprint','synthetic-case-'+str(i)],cwd=work,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for i,n in enumerate(identities)]
            sensor_out=[p.communicate(timeout=10) for p in sensor_procs]
            record('five_sensor_processes',all(p.returncode==0 and 'status=202' in out for p,(out,err) in zip(sensor_procs,sensor_out)), '5 distinct keypairs; 5 child processes; HTTP 202')
            rows=[json.loads(line) for line in ledger.read_text().splitlines()]
            record('five_evidence_rows',len(rows)==5,'ledger rows='+str(len(rows)))
            # A registered node can lie: signed evidence remains unverified.
            lie=run('sensor','-key',identities[0]['dir']/'private.hex','-fingerprint','synthetic-false-claim')
            record('registered_false_claim_unverified','status=202' in lie.stdout and 'received_unverified' in lie.stdout,'signed data accepted ONLY as unverified; no action')
            remote=subprocess.run([str(bins['hub']),'-listen','0.0.0.0:8788'],cwd=work,capture_output=True,text=True,timeout=4)
            record('remote_listen_rejected',remote.returncode!=0 and 'only listens' in remote.stderr,'non-loopback listening forbidden')
            original=json.dumps(next(row['evidence'] for row in rows if row['evidence']['report']['node_id']==identities[0]['node_id'])).encode()
            record('replay_rejected',post(original)==409,'HTTP 409')
            altered=json.loads(original);altered['report']['target_port']=9999
            record('tampering_rejected',post(json.dumps(altered).encode())==403,'HTTP 403')
            record('wrong_content_type_rejected',post(original,'text/plain')==415,'HTTP 415')
            record('oversize_rejected',post(b'x'*12000)==400,'HTTP 400')
            stranger=work/'unregistered';run('keygen','-out',stranger)
            unregistered=run('sensor','-key',stranger/'private.hex',should=1)
            record('unknown_node_rejected','status=403' in unregistered.stdout,'HTTP 403')
            run('revoke-sign','-key',revkey/'private.hex','-version','2','-ids',identities[1]['node_id'],'-out',v2)
            shutil.copyfile(v2,work/'new-revocations.json');os.replace(work/'new-revocations.json',live)
            revoked=run('sensor','-key',identities[1]['dir']/'private.hex',should=1)
            record('revoked_node_rejected','status=403' in revoked.stdout,'HTTP 403')
            still_valid=run('sensor','-key',identities[2]['dir']/'private.hex')
            record('unaffected_node_accepts','status=202' in still_valid.stdout,'HTTP 202')
            shutil.copyfile(v1,work/'old-revocations.json');os.replace(work/'old-revocations.json',live)
            failclosed=run('sensor','-key',identities[2]['dir']/'private.hex',should=1)
            record('revocation_rollback_failclosed','status=503' in failclosed.stdout,'HTTP 503')
            shutil.copyfile(v2,work/'good-revocations.json');os.replace(work/'good-revocations.json',live)
            live.rename(work/'revocations-offline.json')
            unavailable=run('sensor','-key',identities[2]['dir']/'private.hex',should=1)
            record('revocation_file_missing_failclosed','status=503' in unavailable.stdout,'HTTP 503')
            (work/'revocations-offline.json').rename(live)
            feed=work/'feed.json'; state=work/'guardian.state'; badfeed=work/'tampered.json'
            run('feed-sign','-key',feedkey/'private.hex','-version','2','-out',feed)
            g=run('guardian','-feed',feed,'-pub',feedkey/'public.hex','-state',state)
            record('guardian_signed_feed','verified informational feed version 2' in g.stdout,'offline signature verified')
            tampered=json.loads(feed.read_text());tampered['feed']['warnings'][0]['summary']='tampered'
            badfeed.write_text(json.dumps(tampered))
            gbad=run('guardian','-feed',badfeed,'-pub',feedkey/'public.hex','-state',state,should=None)
            record('guardian_fake_feed_rejected',gbad.returncode!=0,'tampered signature rejected')
            oldfeed=work/'feed-old.json';run('feed-sign','-key',feedkey/'private.hex','-version','1','-out',oldfeed)
            gold=run('guardian','-feed',oldfeed,'-pub',feedkey/'public.hex','-state',state,should=None)
            record('guardian_rollback_rejected',gold.returncode!=0,'older valid signed version rejected')
            # SIGKILL-like exit; never automatically clear the stale HUB lock.
            hub.kill();hub.wait(timeout=5)
            record('hub_unexpected_death_leaves_lock',(work/'ledger.jsonl.lock').exists(),'fail-closed stale lock retained')
            rejected=subprocess.run(hub_cmd,cwd=work,capture_output=True,text=True,timeout=5)
            record('unsafe_auto_restart_rejected',rejected.returncode!=0,'stale lock prohibits relaunch')
            off=work/'offhost';off.mkdir(); snapshot=off/'evidence.jsonl';shutil.copyfile(ledger,snapshot)
            shutil.copyfile(work/'ledger.jsonl.head',off/'evidence.jsonl.head')
            hist=off/'witness-history.jsonl'
            attested=run('witness','-mode','attest','-ledger',snapshot,'-history',hist,
                         '-key',witnesskey/'private.hex','-bootstrap-history')
            import re
            m=re.search(r'tip=([0-9a-f]{64})',attested.stdout)
            record('external_witness_snapshot',m is not None,'independent signed tip')
            tip=m.group(1)
            verified=run('witness','-mode','verify','-ledger',snapshot,'-history',hist,
                         '-pub',witnesskey/'public.hex','-expected-tip',tip)
            record('external_witness_verifies','VERIFIED rows=' in verified.stdout,'externally pinned tip checks')
            inspect=run('recovery-check','-ledger',snapshot,'-history',hist,
                        '-pub',witnesskey/'public.hex','-expected-tip',tip)
            outcome=json.loads(inspect.stdout)
            record('offline_recovery_does_not_approve_restart',outcome['status']=='fully_witnessed' and outcome['may_start_hub'] is False,'operator review mandatory')
            # EXPLICIT LAB-ONLY operator step after evidence copy; never auto-recover production.
            (work/'ledger.jsonl.lock').unlink()
            start_hub()
            record('lab_restarts_after_manual_review',post(original)==409,'previously acknowledged replay rejected HTTP 409')
            grun=run('guardian','-feed',feed,'-pub',feedkey/'public.hex','-state',state)
            record('guardian_independent_after_hub_recovery',grun.returncode==0,'no network dependency on HUB')
        finally:
            if hub and hub.poll() is None:
                hub.kill()
                hub.wait(timeout=5)
        summary={'schema':'trapnet.loopback-blackbox.v0.1','description':'5 separate Sensor OS processes, one HUB and one Guardian on one host/one loopback namespace; NOT independent 5 hosts','passed':sum(r['pass'] for r in results),'total':len(results),'results':results,'production_deployed':False,'network_exposure':'127.0.0.1 only'}
        dest=pathlib.Path(args.out or './lab-results.json')
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        print('Summary: '+str(summary['passed'])+'/'+str(summary['total'])+' cases successful. '+str(dest))

if __name__=='__main__':main()
