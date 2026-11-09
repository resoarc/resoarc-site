#!/usr/bin/env python3
"""SWWW additional public intelligence feeds (read-only, private output only).

NVD: new CVEs with CVSS; JPCERT/CISA: separate bulletins; JVN: optional RSS;
FIRST EPSS: probabilistic exploitation enrichment (NOT confirmed incidents).
Never publishes or reports a product as affected without review.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UTC = dt.timezone.utc
UA = 'ResoArc-SWWW/0.2 (read-only public advisory feeds; https://resoarc.com/)'
NVD = 'https://services.nvd.nist.gov/rest/json/cves/2.0'
NVD_FEED = 'https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-recent.json.gz'
NVD_META = 'https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-recent.meta'
MAX_DECOMPRESSED = 64_000_000
JPCERT = 'https://www.jpcert.or.jp/rss/jpcert.rdf'
JVN = 'https://jvn.jp/rss/jvn.rdf'
UBUNTU = 'https://ubuntu.com/security/notices/rss.xml'
DEBIAN = 'https://www.debian.org/security/dsa.rdf'
CERTEU = 'https://cert.europa.eu/publications/security-advisories-rss'
CIS = 'https://www.cisecurity.org/feed/advisories'
CISA_ALERTS = 'https://www.cisa.gov/cybersecurity-advisories/all.xml'
EPSS = 'https://api.first.org/data/v1/epss'
CVE_RE = re.compile(r'\bCVE-\d{4}-\d{4,}\b', re.I)
MAX_DOWNLOAD = 9_000_000
MAX_NVD_PAGES = 6
PAGE_SIZE = 500


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.swww-source-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def get(url: str):
    if not url.startswith('https://'):
        raise ValueError('HTTPS required')
    req=urllib.request.Request(url,headers={'User-Agent':UA, 'Accept':'application/json,application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.1'})
    with urllib.request.urlopen(req, timeout=58 if url.startswith(NVD + '?') else 23) as r:
        data=r.read(MAX_DOWNLOAD+1)
        if len(data)>MAX_DOWNLOAD: raise ValueError('feed exceeds size bound')
        return data


def clip(x, n=270):
    return re.sub(r'\s+', ' ', str(x or '')).strip()[:n]


def datestr(x):
    if not x:return ''
    v=str(x)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):return v
    try:
        return dt.datetime.fromisoformat(v.replace('Z','+00:00')).astimezone(UTC).isoformat().replace('+00:00','Z')
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(v).astimezone(UTC).isoformat().replace('+00:00','Z')
        except (ValueError, TypeError, OverflowError):
            return ''


def nvd_severity(metrics):
    for kind in ('cvssMetricV40','cvssMetricV31','cvssMetricV30','cvssMetricV2'):
        for item in metrics.get(kind, []):
            if not isinstance(item,dict):continue
            cvss=item.get('cvssData',{})
            try:score=float(cvss.get('baseScore'))
            except (TypeError,ValueError):continue
            label=('CRITICAL' if score>=9 else 'HIGH' if score>=7 else 'MODERATE' if score>=4 else 'LOW')
            return label,score
    return 'UNASSESSED',None


def parse_nvd_cve(item):
    cve=item.get('cve',{})
    cid=str(cve.get('id',''))
    if not CVE_RE.fullmatch(cid):return None
    if cve.get('vulnStatus') in ('Rejected','REJECTED'):return None
    severity,cvss=nvd_severity(cve.get('metrics',{}))
    descriptions=cve.get('descriptions',[])
    en=next((x.get('value','') for x in descriptions if x.get('lang')=='en'), '')
    ja=next((x.get('value','') for x in descriptions if x.get('lang')=='ja'), '')
    title=clip(ja or en or cid,155)
    return {'id':cid,'title':title,'summary':clip(en or ja,400),'source':'NVD',
            'published':datestr(cve.get('published')),'severity':severity,'cvss_score':cvss,
            'url':'https://nvd.nist.gov/vuln/detail/'+cid,'scope':'industry',
            'status':'published-advisory','affected':'ResoArcへの影響未確認',
            'package':'','version':''}


def fetch_nvd_feed(now):
    """Verify NVD's official recent (8-day) gzip feed against its SHA256 metadata.

    No mirror or unsigned community reconstruction is considered an official feed.
    """
    raw_meta=get(NVD_META).decode('ascii',errors='strict')
    fields={}
    for line in raw_meta.splitlines():
        if ':' in line:
            key,value=line.split(':',1)
            fields[key.strip()]=value.strip()
    digest=fields.get('sha256','')
    if not re.fullmatch(r'[a-fA-F0-9]{64}',digest):
        raise ValueError('NVD meta has no SHA256')
    modified=dt.datetime.fromisoformat(fields.get('lastModifiedDate','')).astimezone(UTC)
    age_h=(now-modified).total_seconds()/3600
    if age_h < -2 or age_h>72:
        raise ValueError('NVD recent feed meta stale or future')
    compressed=get(NVD_FEED)
    if int(fields.get('gzSize',-1))!=len(compressed):
        raise ValueError('NVD gzip size differs from signed metadata')
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as feed:
        plain=feed.read(MAX_DECOMPRESSED+1)
    if len(plain)>MAX_DECOMPRESSED or int(fields.get('size',-1))!=len(plain):
        raise ValueError('NVD uncompressed size invalid')
    if hashlib.sha256(plain).hexdigest().lower()!=digest.lower():
        raise ValueError('NVD SHA256 mismatch')
    data=json.loads(plain)
    vulns=data.get('vulnerabilities')
    if data.get('format')!='NVD_CVE' or not isinstance(vulns,list):
        raise ValueError('NVD 2.0 feed schema unexpected')
    count=int(data.get('totalResults',len(vulns)))
    if count!=len(vulns):
        raise ValueError('NVD recent feed incomplete')
    rows=[item for raw in vulns if (item:=parse_nvd_cve(raw)) is not None]
    return rows,{'total':count,'truncated':False,'days':8,
                 'method':'OFFICIAL_SHA256_VERIFIED_GZIP',
                 'feed_modified_at':modified.isoformat(),
                 'feed_age_hours':round(max(0,age_h),1),
                 'integrity':'SHA256_OK'}


def fetch_nvd(now,days=2):
    try:
        return fetch_nvd_feed(now)
    except (OSError,ValueError,KeyError,EOFError,gzip.BadGzipFile) as exc:
        # A smaller API window is strictly a degraded fallback, not full coverage.
        rows, detail=fetch_nvd_api(now,days)
        detail.update({'truncated':True,'method':'NVD_API_LIMITED_FALLBACK',
                       'feed_failure':type(exc).__name__})
        return rows,detail


def fetch_nvd_api(now, days=2):
    start=now-dt.timedelta(days=days)
    params={'pubStartDate':start.strftime('%Y-%m-%dT%H:%M:%S.000')+'+00:00',
            'pubEndDate':now.strftime('%Y-%m-%dT%H:%M:%S.000')+'+00:00',
            'resultsPerPage':str(PAGE_SIZE)}
    rows=[];total=None
    for page in range(MAX_NVD_PAGES):
        params['startIndex']=str(page*PAGE_SIZE)
        url=NVD+'?'+urllib.parse.urlencode(params)
        try:
            raw=json.loads(get(url).decode('utf-8'))
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            if rows:
                return rows, {'total':total,'truncated':True,'days':days, 'reason':type(exc).__name__}
            raise
        if 'vulnerabilities' not in raw or not isinstance(raw['vulnerabilities'],list):
            raise ValueError('NVD response lacks vulnerabilities')
        total=int(raw.get('totalResults',len(raw['vulnerabilities'])))
        for obj in raw['vulnerabilities']:
            item=parse_nvd_cve(obj)
            if item:rows.append(item)
        if len(raw['vulnerabilities'])<PAGE_SIZE or (page+1)*PAGE_SIZE>=total:
            return rows,{'total':total,'truncated':False,'days':days}
    return rows,{'total':total,'truncated':True,'days':days}


def text_at(element, tag):
    for node in element.iter():
        if node.tag.rsplit('}',1)[-1].lower()==tag.lower():
            return ''.join(node.itertext()).strip()
    return ''


def parse_rss(raw,source,max_items=90):
    root=ET.fromstring(raw)
    if root.tag.rsplit('}',1)[-1].lower() not in ('rss','rdf'):
        raise ValueError('not RSS/RDF (possible maintenance page)')
    items=[]
    for entry in root.iter():
        if entry.tag.rsplit('}',1)[-1]!='item':continue
        title=clip(text_at(entry,'title'),230)
        url=text_at(entry,'link').strip()
        if not url.startswith('https://'):url='#'
        description=clip(re.sub(r'<[^>]+>',' ',html.unescape(text_at(entry,'description'))),450)
        published=datestr(text_at(entry,'date') or text_at(entry,'pubDate'))
        ids=sorted(set(x.upper() for x in CVE_RE.findall(title+' '+description)))
        key=ids[0] if len(ids)==1 else clip(text_at(entry,'identifier') or url,180)
        if not title or not published or not key:continue
        items.append({'id':key,'cves':ids[:20], 'title':title,'summary':description,
                      'source':source,'published':published,'url':url,'kind':'BULLETIN',
                      'severity':'UNASSESSED','exploitation_claim':'NOT_VERIFIED'})
        if len(items)>=max_items:break
    return items


def fetch_epss(cves):
    result={}
    # Limit the enrichment to a disclosed subset, track coverage separately.
    for i in range(0,len(cves),45):
        subset=cves[i:i+45]
        query=urllib.parse.urlencode({'cve':','.join(subset)})
        info=json.loads(get(EPSS+'?'+query).decode('utf-8'))
        if info.get('status')!='OK' or not isinstance(info.get('data'),list):
            raise ValueError('EPSS schema mismatch')
        for r in info['data']:
            cve=r.get('cve')
            if cve not in subset:continue
            try:
                score=float(r['epss']);pct=float(r['percentile'])
                if not (0<=score<=1 and 0<=pct<=1):continue
                result[cve]={'epss':round(score,6),'percentile':round(pct,6),'date':r.get('date','')}
            except (KeyError,ValueError,TypeError):pass
    return result


def build_sources(now=None, existing=None, fetcher=get, prior=None):
    global get
    # dependency injection for tests; restored even if a source fails
    previous=get;get=fetcher
    try:
        clock=now or dt.datetime.now(UTC)
        if clock.tzinfo is None:clock=clock.replace(tzinfo=UTC)
        stat={};errors={};bulletins=[];rows=[];meta={}
        prior = prior if isinstance(prior,dict) else {}
        last_verified_at = prior.get('nvd_last_verified_at')

        adapters = (
            ('NVD',lambda:fetch_nvd(clock)),
            ('JPCERT',lambda:(parse_rss(get(JPCERT),'JPCERT/CC'),{})),
            ('CISA Alerts',lambda:(parse_rss(get(CISA_ALERTS),'CISA Alerts'),{})),
            ('JVN',lambda:(parse_rss(get(JVN),'JVN'),{})),
            ('Ubuntu',lambda:(parse_rss(get(UBUNTU),'Ubuntu USN'),{})),
            ('Debian',lambda:(parse_rss(get(DEBIAN),'Debian DSA'),{})),
            ('CERT-EU',lambda:(parse_rss(get(CERTEU),'CERT-EU'),{})),
            ('CIS',lambda:(parse_rss(get(CIS),'CIS'),{})),
        )
        # Fetch independent public domains concurrently; NVD pages remain sequential.
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {name: pool.submit(fn) for name, fn in adapters}
            for name, fn in adapters:
                try:
                    data, detail = futures[name].result()
                    if name == 'NVD':
                        rows = data
                        if not detail.get('truncated'):
                            last_verified_at = clock.isoformat().replace('+00:00','Z')
                    else:
                        bulletins.extend(data)
                    stat[name] = 'TRUNCATED' if detail.get('truncated') else 'OK'
                    meta[name] = {'count':len(data), **detail}
                    if detail.get('truncated'):
                        errors[name] = 'NVD partial pages or collection cap'
                except (OSError, ValueError, KeyError, ET.ParseError, urllib.error.HTTPError) as exc:
                    stat[name] = 'ERROR'
                    meta[name] = {'count':None}
                    errors[name] = type(exc).__name__
                    if name == 'NVD':
                        last = prior.get('nvd_last_verified_at') or prior.get('checked_at')
                        try:
                            last_dt = dt.datetime.fromisoformat(str(last).replace('Z','+00:00')).astimezone(UTC)
                            age = (clock-last_dt).total_seconds()
                        except (ValueError,TypeError,OverflowError):
                            age = 10**12
                        cached = [x for x in prior.get('items',[])
                                  if isinstance(x,dict) and x.get('source')=='NVD']
                        if 0 <= age <= 72*3600 and cached:
                            rows = cached
                            last_verified_at=last
                            stat[name]='STALE'
                            meta[name]={'count':len(cached),'last_verified_at':last,
                                        'cached_age_hours':round(age/3600,1),
                                        'method':'VERIFIED_PREVIOUS_SNAPSHOT'}
        # EPSS is enrichment, not an independent volume of new CVEs.
        bulletins.sort(key=lambda x:x.get('published',''),reverse=True)
        candidates=[]
        candidates.extend(x['id'] for x in (existing or []) if isinstance(x,dict) and CVE_RE.fullmatch(str(x.get('id',''))))
        candidates.extend(x['id'] for x in sorted(rows,key=lambda r:({'CRITICAL':3,'HIGH':2,'MODERATE':1}.get(r.get('severity'),0),r.get('published','')),reverse=True)[:180])
        unique=list(dict.fromkeys(candidates))[:180]
        try:
            probs=fetch_epss(unique) if unique else {}
            stat['EPSS']='OK';meta['EPSS']={'requested':len(unique),'matched':len(probs),'scope':'selected CVEs only'}
        except (OSError,ValueError,KeyError,urllib.error.HTTPError) as e:
            probs={};stat['EPSS']='ERROR';errors['EPSS']=type(e).__name__
            meta['EPSS']={'requested':len(unique),'matched':0}
        return {'schema_version':2,'checked_at':clock.isoformat().replace('+00:00','Z'),
                'sources':stat,'source_meta':meta,'errors':errors,
                'nvd_last_verified_at':last_verified_at,
                'items':rows,'bulletins':bulletins[:320], 'epss':probs,
                'notice':'Read-only public intelligence. CVE data and KEV are not evidence of ResoArc product exposure or victim counts.'}
    finally:
        get=previous


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--out',required=True,type=Path,help='private security watch output directory')
    a=p.parse_args(argv)
    q={}
    try:q=json.loads((a.out/'review-queue.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):pass
    prior={}
    try:prior=json.loads((a.out/'security-weather-extras.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):pass
    report=build_sources(existing=q.get('items',[]),prior=prior)
    path=a.out/'security-weather-extras.json'
    atomic_json(path,report)
    print(json.dumps({'statuses':report['sources'],'nvd':len(report['items']),
                      'bulletins':len(report['bulletins']),'epss':len(report['epss']),
                      'publication':'HOLD'},ensure_ascii=False))
    # JVN may be under maintenance. Keep data usable, but clearly mark partial coverage.
    return 0 if all(v=='OK' for v in report['sources'].values()) else 2

if __name__=='__main__':raise SystemExit(main())