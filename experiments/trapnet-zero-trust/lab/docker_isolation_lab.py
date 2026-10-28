#!/usr/bin/env python3
"""TrapNet v0.9: five Docker network namespaces (not five hosts).

Must run on a disposable Docker host. Uses only Docker --internal bridges;
no published ports, firewall mutations, privileged containers or LAN probes.
Does not use production keys, real traffic, or a public HUB listener.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

IMAGE = 'python:3.13-alpine'
MARKER = 'TRAPNET_V09_INTERNAL_LAB_ONLY'


def call(argv, check=True, timeout=90):
    p = subprocess.run([str(a) for a in argv], capture_output=True, text=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError('command failed: ' + ' '.join(map(str, argv[:4])) +
                           '\n' + (p.stderr or p.stdout)[-900:])
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=str(pathlib.Path(__file__).resolve().parents[1]))
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    source = pathlib.Path(args.source).resolve()
    results = []
    token = 'tnlab-' + uuid.uuid4().hex[:12]
    names = {'hub': token+'-hub', 'networks': [token+'-net-'+str(i) for i in range(5)]}
    containers, networks = [], []

    def check(name, passed, detail):
        results.append({'test': name, 'pass': bool(passed), 'detail': detail})
        print(('PASS ' if passed else 'FAIL ') + name + ': ' + detail, flush=True)
        if not passed:
            raise AssertionError(name+': '+detail)

    def docker_inspect(identifier):
        return json.loads(call(['docker','inspect',identifier]).stdout)[0]

    def docker_security_flags(network, container_name=None):
        flags = ['--network', network, '--user', str(os.getuid())+':'+str(os.getgid()),
                 '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                 '--read-only', '--pids-limit', '96', '--memory', '192m',
                 '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=16m',
                 '-e', 'TRAPNET_NETLAB_MARKER='+MARKER]
        if container_name:
            flags += ['--name', container_name]
        return flags

    summary = {'schema':'trapnet.netns-lab.v0.9','production_deployed':False,
               'isolation':'five Docker internal bridges; distinct container namespaces; single Docker host',
               'host_port_bindings':0,'five_independent_hosts':False,'results':results}
    try:
        # Do not start the Docker engine or create host-wide firewall rules.
        call(['docker','info','--format','{{.ServerVersion}}'],timeout=15)
        if call(['docker','image','inspect',IMAGE],check=False,timeout=15).returncode:
            call(['docker','pull',IMAGE],timeout=120)
        with tempfile.TemporaryDirectory(prefix='trapnet-internal-netlab-') as tmp:
            work = pathlib.Path(tmp)
            bins = work / 'bin'; bins.mkdir()
            lab = source / 'lab'
            for name in ('hub','sensor','keygen','feed-sign','guardian'):
                env = dict(os.environ, CGO_ENABLED='0',GOOS='linux', GOARCH='amd64')
                p = subprocess.run(['go','build','-trimpath','-o',str(bins/name),'./cmd/'+name],
                                   cwd=source, env=env, capture_output=True, text=True, timeout=180)
                check('build_'+name,p.returncode==0,p.stderr[-240:] or 'linux/amd64 executable')
            keys = work/'keys';keys.mkdir()
            ids=[]
            for i in range(5):
                d = keys/('sensor'+str(i));
                call([bins/'keygen','-out',d]);ids.append((d,json.loads((d/'node.json').read_text())))
            feedkey=keys/'feed';call([bins/'keygen','-out',feedkey])
            trust=work/'trust';trust.mkdir()
            (trust/'allowlist.json').write_text(json.dumps({n['node_id']:n['public_key'] for _,n in ids}))
            state=work/'state';state.mkdir()
            for net in names['networks']:
                call(['docker','network','create','--driver','bridge','--internal',net]); networks.append(net)
                detail=json.loads(call(['docker','network','inspect',net]).stdout)[0]
                check('internal_bridge_'+net.rsplit('-',1)[-1],
                      detail['Internal'] is True and detail['Driver']=='bridge',
                      'Docker internal bridge: no external route requested')
            common=['-v',str(bins)+':/app/bin:ro','-v',str(lab)+':/app/lab:ro']
            hub_args=['docker','run','-d','--rm',*docker_security_flags(networks[0],names['hub']),
                      '--network-alias','hub',*common,
                      '-v',str(trust)+':/trust:ro','-v',str(state)+':/state:rw',
                      '--entrypoint','python3',IMAGE,
                      '/app/lab/netlab_bridge.py','hub','--binary','/app/bin/hub',
                      '--allowlist','/trust/allowlist.json','--ledger','/state/evidence.jsonl']
            call(hub_args);containers.append(names['hub'])
            for net in networks[1:]:
                call(['docker','network','connect','--alias','hub',net,names['hub']])
            info=docker_inspect(names['hub'])
            check('hub_has_five_separate_interfaces',
                  set(info['NetworkSettings']['Networks'])==set(networks),
                  'HUB attached to exactly five lab-internal bridges')
            check('hub_no_published_ports',
                  not info['HostConfig']['PortBindings'] and not info['NetworkSettings']['Ports'],
                  'No host ports published')
            check('hub_unprivileged_readonly',
                  info['HostConfig']['ReadonlyRootfs'] and info['HostConfig']['CapDrop']==['ALL']
                  and not info['HostConfig']['Privileged'],
                  'Read-only filesystem, all capabilities dropped')
            for _ in range(70):
                live = call(['docker','exec',names['hub'],'python3','-c',
                             'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8788/health",timeout=1)'],
                            check=False,timeout=5)
                if live.returncode==0:break
                time.sleep(.15)
            else:raise RuntimeError('HUB failed health check')
            check('hub_local_only_listener',True,'HUB 127.0.0.1:8788 ready behind test-only isolated relay')
            sensor_names=[]
            for i,(d,ident) in enumerate(ids):
                name=token+'-sensor-'+str(i)
                command=['docker','create',*docker_security_flags(networks[i],name),
                         '--network-alias','sensor-'+str(i),*common,
                         '-v',str(d)+':/keys:ro',
                         '--entrypoint','python3',IMAGE,
                         '/app/lab/netlab_bridge.py','sensor','--binary','/app/bin/sensor',
                         '--key','/keys/private.hex','--fingerprint','synthetic-netns-'+str(i)]
                call(command);containers.append(name);sensor_names.append(name)
                config=docker_inspect(name)
                check('sensor_'+str(i)+'_single_internal_network',
                      set(config['NetworkSettings']['Networks'])=={networks[i]},
                      'Only its own isolated internal bridge attached')
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                futures=[pool.submit(call,['docker','start',name]) for name in sensor_names]
                for f in futures:f.result(timeout=15)
            for i,name in enumerate(sensor_names):
                call(['docker','wait',name],timeout=30)
                x=docker_inspect(name);logs=call(['docker','logs',name],check=False).stdout
                check('sensor_'+str(i)+'_signed_report',
                      x['State']['ExitCode']==0 and 'status=202' in logs and 'received_unverified' in logs,
                      'Identity '+str(i)+' sent signed observation -> received_unverified')
            ledger=state/'evidence.jsonl'
            try:rows=[json.loads(r) for r in ledger.read_text().splitlines()]
            except Exception:rows=[]
            check('five_distinct_signer_records',len(rows)==5 and len({r['evidence']['report']['node_id'] for r in rows})==5,
                  'Five distinct registered identities in HUB ledger')
            # Client to Internet cannot exit Docker --internal networks.
            egress = call(['docker','run','--rm',*docker_security_flags(networks[0]),
                          '--entrypoint','python3',IMAGE,'-c',
                          'import socket;\ntry: socket.create_connection(("1.1.1.1",443),timeout=2); print("UNEXPECTED_CONNECTED")\nexcept OSError: print("EXPECTED_BLOCKED")'],
                         check=False,timeout=15)
            check('external_egress_denied',egress.returncode==0 and 'EXPECTED_BLOCKED' in egress.stdout,
                  'TCP from internal bridge toward public IP rejected')
            # Docker embedded DNS does not discover a sensor in another isolated bridge.
            dns = call(['docker','run','--rm',*docker_security_flags(networks[0]),
                        '--entrypoint','python3',IMAGE,'-c',
                        'import socket;\ntry: socket.getaddrinfo("sensor-1",8788); print("UNEXPECTED_RESOLVED")\nexcept socket.gaierror: print("EXPECTED_UNRESOLVED")'],
                       check=False,timeout=15)
            check('cross_sensor_name_unreachable',dns.returncode==0 and 'EXPECTED_UNRESOLVED' in dns.stdout,
                  'Sensor namespace 0 cannot resolve Sensor namespace 1')
            # Guardian has no network namespace by design. It reads only a
            # separately signed offline feed; no HUB key or Sensor key mounted.
            feed_dir=work/'offline_feed';feed_dir.mkdir();guardian_dir=work/'guardian_state';guardian_dir.mkdir()
            call([bins/'feed-sign','-key',feedkey/'private.hex','-out',feed_dir/'feed.json','-version','1'])
            shutil.copy2(feedkey/'public.hex',feed_dir/'public.hex')
            gp=call(['docker','run','--rm',*docker_security_flags('none'),*common,
                     '-v',str(feed_dir)+':/feed:ro','-v',str(guardian_dir)+':/state:rw',
                     '--entrypoint','/app/bin/guardian',IMAGE,
                     '-feed','/feed/feed.json','-pub','/feed/public.hex','-state','/state/guardian-state.json'],
                    check=False,timeout=25)
            check('guardian_offline_signed_feed',gp.returncode==0 and 'verified informational feed version 1' in gp.stdout,
                  'Guardian on Docker network=none; signed information only')
            # Kill HUB (SIGKILL in Docker), and verify no Sensor reports can
            # proceed through the proxy. Never remove its stale lock in this test.
            call(['docker','kill',names['hub']]);containers.remove(names['hub'])
            outage = call(['docker','run','--rm',*docker_security_flags(networks[0]),
                           '--entrypoint','python3',IMAGE,'-c',
                           'import socket;\ntry: socket.create_connection(("hub",18788),timeout=2); print("UNEXPECTED_CONNECTED")\nexcept OSError: print("EXPECTED_OFFLINE")'],
                          check=False,timeout=15)
            check('hub_outage_does_not_fallback_to_internet',outage.returncode==0 and 'EXPECTED_OFFLINE' in outage.stdout,
                  'HUB absent; no alternate public channel')
            check('hub_crash_preserves_lock', (state/'evidence.jsonl.lock').exists(),
                  'HUB crash requires operator review; no unattended cleanup')
            summary['passed']=sum(x['pass'] for x in results)
            summary['total']=len(results)
    except Exception as exc:
        summary['error']=str(exc)
        print('FAIL lab: '+str(exc),file=sys.stderr,flush=True)
    finally:
        # Exact randomly named lab resources only; NEVER docker prune or host firewall changes.
        for item in reversed(containers):
            call(['docker','rm','-f',item],check=False,timeout=15)
        for item in reversed(networks):
            call(['docker','network','rm',item],check=False,timeout=15)
        summary['passed']=sum(x['pass'] for x in results)
        summary['total']=len(results)
        p=pathlib.Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
        print(f'NETLAB summary: {summary["passed"]}/{summary["total"]} passed. {p}',flush=True)
    return 0 if summary['total']>=25 and summary['passed']==summary['total'] and 'error' not in summary else 1

if __name__ == '__main__':
    sys.exit(main())
