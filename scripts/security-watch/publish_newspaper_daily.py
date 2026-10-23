#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc contributors
# SPDX-License-Identifier: MIT
"""Daily ResoArc newspaper publishing with fail-closed quality and release checks.

Operator-PC execution only (requires existing SSH and Wrangler authentication).
No Cloudflare or database secrets stored here; no changes to global freeze guard.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,pathlib,re,shutil,subprocess,sys,tempfile,time,urllib.request
from zoneinfo import ZoneInfo

SCRIPT=pathlib.Path(__file__).resolve()
# Runs in an approved site git repo or at a standalone operator path.
ROOT=pathlib.Path(os.environ.get("SWWW_WORK_ROOT",str(pathlib.Path.home()/"Documents/ResoArc/security-weather-watch-20261022")))
LOG=ROOT/"publication-logs/newspaper-daily.log"
VPS="gitmirror@153.121.46.31:/srv/resoarc/git/resoarc-site.git"
CODEBERG="git@codeberg.org:ResoArc/resoarc-site.git"
MAIN_URL="https://resoarc.com"
WRANGLER=pathlib.Path.home()/"AppData/Local/npm-cache/_npx/32026684e21afda6/node_modules/.bin/wrangler.cmd"
MAX_AGE_MIN=190
LOCK_FILE=ROOT/"publication-logs/newspaper.lock"
EXCLUDE=(".git","__pycache__",".pytest_cache")
ALLOWED_PREFIX=("site/security/weather/newspaper/",)
ALLOWED_FILES={"site-manifest.sha256","site/assets/navigation-map.json"}
JST=dt.timezone(dt.timedelta(hours=9))

def now():return dt.datetime.now(JST)
def log(*parts):
    LOG.parent.mkdir(parents=True,exist_ok=True)
    line=now().isoformat(timespec="seconds")+" "+ " ".join(map(str,parts))
    print(line,flush=True)
    with LOG.open("a",encoding="utf-8") as f:f.write(line+"\n")
def command(args,timeout=100,cwd=None,env=None):
    proc=subprocess.run(args,text=True,encoding="utf-8",errors="replace",capture_output=True,
                        cwd=cwd,env=env,timeout=timeout)
    if proc.returncode:raise RuntimeError(str(args[:3])+": "+proc.stderr.strip()[-600:])
    return proc.stdout
def git_ssh_env():
    k=ROOT.parent/"secure/vps_gitmirror_ed25519"
    if not k.exists():raise RuntimeError("Approved VPS repository key missing")
    env=os.environ.copy()
    env["GIT_SSH_COMMAND"]='ssh -4 -i "'+str(k)+'" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=12'
    return env
def vps_sha(env):
    return command(["git","ls-remote",VPS,"refs/heads/main"],env=env,timeout=40).strip().split()[0]
def codeberg_sha():
    return command(["git","ls-remote","https://codeberg.org/ResoArc/resoarc-site.git","refs/heads/main"],timeout=60).strip().split()[0]
def sha(b):return hashlib.sha256(b).hexdigest()
def http(path):
    req=urllib.request.Request(MAIN_URL+path,headers={"User-Agent":"ResoArc-SWWW-DailyPublisher/1.0","Cache-Control":"no-cache"})
    with urllib.request.urlopen(req,timeout=30) as r:
        if r.status!=200:raise RuntimeError("Public website status "+str(r.status))
        return r.read()
def sanitize_cf(content):
    return re.sub(rb'<script\s+type="module"\s+src="https://static\.cloudflareinsights\.com/beacon\.min\.js/[^"]+"[^>]*></script>\s*',b'',content)
def compare_static_site(site):
    # Prevent replacing concurrently deployed official pages with older source.
    for route in ("","os/","products/kintone/"):
        relative=(route+"index.html")
        source=(site/relative).read_bytes()
        live=sanitize_cf(http("/"+route+"?newspaper-guard="+str(int(time.time()))))
        if sha(source)!=sha(live):
            raise RuntimeError("Public site differs from Git source: "+relative)
    for rel in ("assets/navigation.js","assets/site-20261015-v10.css"):
        source=(site/rel).read_bytes()
        live=http("/"+rel+"?newspaper-guard="+str(int(time.time())))
        if sha(source)!=sha(live):
            raise RuntimeError("Public asset differs from Git source: "+rel)
def public_edition():
    try:
        edition=json.loads(http("/security/weather/newspaper/edition.json?revision="+str(int(time.time()))))
        return edition.get("edition_date")
    except Exception:
        return None
def export_vps():
    raw=command(["ssh","-4","-o","BatchMode=yes","-o","ConnectTimeout=12",
                 "mole-vps","python3","/opt/resoarc-swww-api/export_newspaper_public.py"],timeout=65)
    data=json.loads(raw)
    m=data["metadata"]
    if m["quality"]!="OK" or int(m["source_count"])<10:
        raise ValueError("Latest report did not pass source-quality checks")
    report_day=dt.date.fromisoformat(m["date"])
    ts=dt.datetime.fromisoformat(m["generated_at"])
    age=(now()-ts.astimezone(JST)).total_seconds()/60
    if report_day!=now().date() or age<0 or age>MAX_AGE_MIN:
        raise ValueError("Fresh quality-approved newspaper data not available today")
    rows=data["items"]
    if len(rows)!=m["published_date_count"]:
        raise ValueError("Public export incomplete")
    if len(rows)>700:raise ValueError("Daily record cap exceeded")
    prohibited=("internal_owner","affected_asset","investigation_notes","verification_ref",
                "weather-assessments","security-weather-operations")
    encoded=json.dumps(data,ensure_ascii=False)
    if any(secret in encoded for secret in prohibited):
        raise ValueError("Private data marker rejected")
    return data
def run_py(repo,script):
    output=command([sys.executable,"-X","utf8",str(repo/script)],cwd=repo,timeout=135)
    log("QA",script,output.strip().splitlines()[-1])
def deploy(site,commit):
    if not WRANGLER.is_file():raise FileNotFoundError("Cloudflare Wrangler login unavailable")
    out=command(["cmd.exe","/d","/c",str(WRANGLER),"pages","deploy",str(site),
             "--project-name","resoarc","--branch","main","--commit-hash",commit,
             "--commit-dirty=true"],timeout=450)
    if "Deployment complete!" not in out or "Compiled Worker successfully" not in out:
        raise RuntimeError("Cloudflare deployment did not confirm success")
    log("PAGES_DEPLOYED",out.strip().splitlines()[-1])
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    LOG.parent.mkdir(parents=True,exist_ok=True)
    if LOCK_FILE.exists():
        # No overlapping executions or accidental two simultaneous deploys.
        raise RuntimeError("Publisher lock exists. Inspect task logs before removing it.")
    # Atomic local lock.
    fd=os.open(str(LOCK_FILE),os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        if not (ROOT.parent/"coordination/PRODUCTION_FREEZE.flag").is_file():
            raise RuntimeError("Production freeze guard missing unexpectedly")
        report=export_vps()
        day=report["metadata"]["date"]
        git_env=git_ssh_env()
        source_sha=vps_sha(git_env)
        code_sha=codeberg_sha()
        if source_sha!=code_sha:raise RuntimeError("VPS and Codeberg main mismatch")
        log("APPROVED_INPUT",day,"items",len(report["items"]),"sources",report["metadata"]["source_count"])
        with tempfile.TemporaryDirectory(prefix="swww-newspaper-") as temp:
            repo=pathlib.Path(temp)/"resoarc-site"
            command(["git","clone","--quiet","--depth","1","--branch","main",VPS,str(repo)],
                    timeout=125,env=git_env)
            local_sha=command(["git","rev-parse","HEAD"],cwd=repo).strip()
            if local_sha!=source_sha:raise RuntimeError("Main changed during checkout")
            site=repo/"site"
            compare_static_site(site)
            previous_file=site/"security/weather/newspaper/edition.json"
            previous=json.loads(previous_file.read_text(encoding="utf-8"))["edition_date"] if previous_file.exists() else ""
            if previous>day:raise ValueError("Cannot replace newer issue")
            if previous<day:
                input_path=pathlib.Path(temp)/"newspaper-public-input.json"
                input_path.write_text(json.dumps(report,ensure_ascii=False),encoding="utf-8")
                script=repo/"scripts/security-watch/generate_newspaper_daily.py"
                command([sys.executable,"-X","utf8",str(script),"--input",str(input_path),
                         "--site",str(site)],cwd=repo,timeout=60)
                run_py(repo,"scripts/build_navigation.py")
                run_py(repo,"scripts/update_manifest.py")
                run_py(repo,"scripts/verify_site.py")
                changed=command(["git","status","--porcelain","--untracked-files=all"],cwd=repo)
                # Staged/generated changes must only touch the newspaper subtree,
                # manifest and navigation metadata; refuse unrelated releases.
                paths=[line[3:].strip().strip('"') for line in changed.splitlines() if line]
                unexpected=[file for file in paths if not file.startswith(ALLOWED_PREFIX) and file not in ALLOWED_FILES]
                if unexpected:raise RuntimeError("Unapproved release paths: "+repr(unexpected[:8]))
                log("GENERATED",day,"files",len(paths))
                if not args.dry_run:
                    command(["git","add","--","site/security/weather/newspaper",
                             "site/assets/navigation-map.json","site-manifest.sha256"],cwd=repo)
                    command(["git","-c","user.name=ResoArc","-c","user.email=opensource@resoarc.com",
                             "commit","-m","Publish SWWW morning newspaper "+day],cwd=repo)
                    final_sha=command(["git","rev-parse","HEAD"],cwd=repo).strip()
                else:final_sha=local_sha
            else:
                log("EDITION_ALREADY_IN_GIT",day)
                final_sha=local_sha
            if args.dry_run:
                log("DRY_RUN_SUCCESS","no remote writes")
                return
            pub=public_edition()
            if pub==day and previous==day:
                log("ALREADY_LIVE",day)
                return
            compare_static_site(site)
            if previous<day:
                if source_sha!=vps_sha(git_env) or source_sha!=codeberg_sha():
                    raise RuntimeError("Official main advanced since staging; stop")
                command(["git","push","origin","HEAD:refs/heads/main"],cwd=repo,env=git_env,timeout=120)
                secure=ROOT.parent/"secure"
                key=secure/"codeberg_resoarc_ed25519"
                hostfile=secure/"codeberg_known_hosts"
                if not key.exists() or not hostfile.exists():raise RuntimeError("Approved Codeberg SSH configuration missing")
                cenv=os.environ.copy()
                cenv["GIT_SSH_COMMAND"]='ssh -4 -i "'+str(key)+'" -o UserKnownHostsFile="'+str(hostfile)+'" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15'
                command(["git","push",CODEBERG,"HEAD:refs/heads/main"],cwd=repo,env=cenv,timeout=150)
                if final_sha!=codeberg_sha():raise RuntimeError("Codeberg sync verification failed")
                log("SOURCES_SYNCED",final_sha[:10])
            deploy(site,final_sha)
            for _ in range(6):
                if public_edition()==day:
                    log("PUBLICATION_VERIFIED",day)
                    return
                time.sleep(8)
            raise RuntimeError("Cloudflare deployment complete but edition date not verified")
    finally:
        try:LOCK_FILE.unlink()
        except FileNotFoundError:pass

if __name__=="__main__":
    try:main()
    except Exception as exc:
        log("FAILED",type(exc).__name__,str(exc)[:450])
        sys.exit(1)
