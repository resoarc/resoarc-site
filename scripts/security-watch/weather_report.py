#!/usr/bin/env python3
"""ResoArc SWWW: private vulnerability weather forecasts, stdlib-only.

Reads existing Security Watch collector output. Never publishes or sends mail.
Daily counts refer to SOURCE PUBLICATION DATES (CISA's dateAdded for KEV),
not all industry vulnerabilities or affected ResoArc products.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

JST = ZoneInfo('Asia/Tokyo')
UTC = dt.timezone.utc
SOURCES = ('CISA', 'GitHub', 'PHP', 'OSV')
EXTRA_SOURCES = ('NVD', 'JPCERT', 'CISA Alerts', 'JVN', 'Ubuntu', 'Debian', 'CERT-EU', 'CIS', 'EPSS')
DIFFICULTY = {'easy': '軽微', 'moderate': '中程度', 'hard': '難しい', 'unknown': '要調査'}
ALLOWED_HOSTS = {'www.cisa.gov', 'github.com', 'www.php.net', 'osv.dev', 'nvd.nist.gov', 'www.jpcert.or.jp', 'jvndb.jvn.jp', 'jvn.jp', 'ubuntu.com', 'www.debian.org', 'cert.europa.eu', 'www.cisecurity.org'}
DISPLAY_LIMIT = 250


def read_json(path: Path, fallback=None):
    try:
        with path.open(encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return fallback if fallback is not None else {}


def atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.swww-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def to_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def day_of(raw: object):
    if not isinstance(raw, str) or not raw.strip():
        return None
    raw = raw.strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
        try:
            return dt.date.fromisoformat(raw)
        except ValueError:
            return None
    try:
        p = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if p.tzinfo is None:
            return None
        return p.astimezone(JST).date()
    except ValueError:
        return None


def age_minutes(checked, now):
    try:
        t = dt.datetime.fromisoformat(checked.replace('Z', '+00:00'))
        if not t.tzinfo:
            return None
        return max(0, int((now.astimezone(UTC) - t.astimezone(UTC)).total_seconds() // 60))
    except (TypeError, ValueError, AttributeError):
        return None


def valid_url(raw):
    if not isinstance(raw, str):
        return '#'
    url = urlparse(raw)
    return raw if url.scheme == 'https' and url.hostname in ALLOWED_HOSTS and not url.username and not url.password else '#'


def clean(raw, size=200):
    return re.sub(r'[\x00-\x1f\x7f\s]+', ' ', str(raw or '')).strip()[:size]


def advisory_key(row):
    return ':'.join(str(row.get(k, '') or '') for k in ('source', 'id', 'package', 'version'))


def normalize_item(row, assessments):
    key = advisory_key(row)
    review = assessments.get(key, {})
    if not isinstance(review, dict):
        review = {}
    difficulty = review.get('difficulty', 'unknown')
    if difficulty not in DIFFICULTY:
        difficulty = 'unknown'
    severity = str(row.get('severity') or 'UNASSESSED').upper()
    exploited = (row.get('source') == 'CISA KEV' and row.get('status') == 'known-exploited-in-wild')
    known_impact = review.get('resoarc_impact', 'NOT_CONFIRMED')
    if known_impact not in ('NOT_CONFIRMED', 'NOT_AFFECTED', 'AFFECTED'):
        known_impact = 'NOT_CONFIRMED'
    incident = review.get('confirmed_victim_count')
    if type(incident) is not int or incident < 0:
        incident = None
    return {
        'key': key, 'id': clean(row.get('id'), 100),
        'title': clean(row.get('title'), 200), 'source': clean(row.get('source'), 70),
        'date': (day_of(row.get('published')) or dt.date.min).isoformat(),
        'severity': severity if severity in ('KEV', 'CRITICAL', 'HIGH', 'MODERATE', 'LOW', 'UNASSESSED') else 'UNASSESSED',
        'url': valid_url(row.get('url')), 'exploited_in_wild': exploited,
        'resoarc_impact': known_impact, 'difficulty': difficulty,
        'difficulty_label': DIFFICULTY[difficulty],
        'confirmed_victim_count': incident,
        'impact_level': clean(review.get('impact_level') or ('重大（一般的な潜在リスク）' if severity in ('KEV', 'CRITICAL') else '高（一般的な潜在リスク）' if severity == 'HIGH' else '要調査'), 50),
        'package': clean(row.get('package'), 90),
        'summary': clean(row.get('summary'), 300),
        'scope': clean(row.get('scope'), 40),
        'cvss_score': row.get('cvss_score') if type(row.get('cvss_score')) in (int,float) else None,
        'epss': None, 'epss_percentile': None, 'source_refs': [clean(row.get('source'), 70)],
        'kev_date': None,
    }


def weather_for(items, day, healthy):
    if not healthy:
        return {'code': 'unknown', 'icon': '◌', 'label': '観測不能', 'subtitle': '情報源の一部が取得できません', 'score': None}
    recent = [x for x in items if x['date'] == day.isoformat() or x.get('kev_date') == day.isoformat()]
    kev = sum(1 for x in recent if x.get('kev_date') == day.isoformat())
    critical = sum(1 for x in recent if x['severity'] == 'CRITICAL')
    high = sum(1 for x in recent if x['severity'] == 'HIGH')
    other = sum(1 for x in recent if x['severity'] not in ('KEV', 'CRITICAL', 'HIGH'))
    # Cap lower-severity volume: high NVD feed throughput alone is not a typhoon.
    score = kev * 5 + critical * 4 + high * 2 + min(other, 3)
    if kev >= 3 or score >= 22:
        return {'code': 'storm', 'icon': '⛈', 'label': '暴風警報級', 'subtitle': '新たな高リスク情報が集中しています', 'score': score}
    if kev >= 1 or score >= 10:
        return {'code': 'rain-heavy', 'icon': '☈', 'label': '大雨・警戒', 'subtitle': '優先して確認したい新着があります', 'score': score}
    if score >= 4:
        return {'code': 'rain', 'icon': '☂', 'label': '雨', 'subtitle': '重要な新着情報が複数あります', 'score': score}
    if score >= 1:
        return {'code': 'cloud', 'icon': '☁', 'label': 'くもり', 'subtitle': '新着情報を点検してください', 'score': score}
    return {'code': 'clear', 'icon': '☀', 'label': '晴れ間', 'subtitle': '対象情報源で本日付の重要新着はありません', 'score': 0}


def build_report(queue, triage, assessments, now=None, refresh_failed=False, extra=None):
    now = now or dt.datetime.now(JST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=JST)
    today = now.astimezone(JST).date()
    yesterday = today - dt.timedelta(days=1)
    raw = queue.get('items') if isinstance(queue, dict) else None
    if not isinstance(raw, list):
        raw = []
    # Base Security Watch and supplemental feeds are independent. Group by CVE ID
    # to avoid one flaw being counted multiple times; keep KEV *addition* dates.
    base_rows = [r for r in raw if isinstance(r, dict) and r.get('id')]
    extra = extra if isinstance(extra, dict) else None
    additional = [r for r in (extra.get('items', []) if extra else [])
                  if isinstance(r, dict) and r.get('id')]
    groups = {}
    for original in base_rows + additional:
        item = normalize_item(original, assessments)
        cve_id = re.fullmatch(r'CVE-\d{4}-\d{4,}', item['id'], flags=re.I)
        canonical = item['id'].upper() if cve_id else item['key']
        old = groups.get(canonical)
        if old is None:
            if item['exploited_in_wild']:
                item['kev_date'] = item['date']
            groups[canonical] = item
            continue
        if item['source'] not in old['source_refs']:
            old['source_refs'].append(item['source'])
        old['exploited_in_wild'] = old['exploited_in_wild'] or item['exploited_in_wild']
        if item['exploited_in_wild']:
            old['kev_date'] = item['date']
        old['date'] = max(old['date'], item['date'])
        if item['source'] == 'NVD':
            if item['cvss_score'] is not None: old['cvss_score'] = item['cvss_score']
        # Do not turn an unassessed item into CRITICAL merely because it is KEV.
        sev = {'CRITICAL': 5, 'HIGH': 4, 'MODERATE': 3, 'LOW': 2, 'UNASSESSED': 1, 'KEV': 0}
        if sev.get(item['severity'], 0) > sev.get(old['severity'], 0):
            old['severity'] = item['severity']
            old['impact_level'] = item['impact_level']
        if old['resoarc_impact'] == 'NOT_CONFIRMED' and item['resoarc_impact'] != 'NOT_CONFIRMED':
            old['resoarc_impact'] = item['resoarc_impact']
            old['difficulty'] = item['difficulty']
            old['difficulty_label'] = item['difficulty_label']
            old['confirmed_victim_count'] = item['confirmed_victim_count']
        if len(item['summary']) > len(old['summary']): old['summary'] = item['summary']
    rows = list(groups.values())
    scores = extra.get('epss', {}) if extra and isinstance(extra.get('epss'), dict) else {}
    for item in rows:
        sc = scores.get(item['id'], {}) if item['id'].startswith('CVE-') else {}
        if isinstance(sc, dict) and type(sc.get('epss')) in (int, float):
            item['epss'] = sc['epss']
            item['epss_percentile'] = sc.get('percentile')
    rows.sort(key=lambda x: (max(x['date'], x['kev_date'] or ''),
                              {'CRITICAL': 5, 'HIGH': 4, 'KEV': 3}.get(x['severity'], 0)),reverse=True)
    source_status = queue.get('sources') if isinstance(queue.get('sources'), dict) else {}
    source_errors = queue.get('errors') if isinstance(queue.get('errors'), list) else []
    checked_at = queue.get('checked_at')
    age = age_minutes(checked_at, now)
    base_healthy = (queue.get('status') == 'FETCHED_UNREVIEWED'
               and all(source_status.get(x) == 'OK' for x in SOURCES)
               and not source_errors and age is not None and age <= 150
               and not refresh_failed)
    extras_status = extra.get('sources', {}) if extra else {}
    extras_age = age_minutes(extra.get('checked_at'), now) if extra else None
    extra_healthy = (not extra or
                     (extras_age is not None and extras_age <= 150 and
                      all(extras_status.get(x) == 'OK' for x in EXTRA_SOURCES)))
    quality = 'DEGRADED' if not base_healthy else 'PARTIAL' if not extra_healthy else 'OK'
    # Missing supplemental observations must never generate a false all-clear.
    healthy = base_healthy
    today_rows = [x for x in rows if x['date'] == today.isoformat() or x['kev_date'] == today.isoformat()]
    yesterday_rows = [x for x in rows if x['date'] == yesterday.isoformat() or x['kev_date'] == yesterday.isoformat()]
    all_kev = sum(x['exploited_in_wild'] for x in rows)
    confirmed_victims = [x['confirmed_victim_count'] for x in today_rows if x['confirmed_victim_count'] is not None]
    forecast = weather_for(rows, today, healthy)
    yesterday_forecast = weather_for(rows, yesterday, healthy)
    if quality == 'PARTIAL':
        for wx in (forecast,yesterday_forecast):
            if wx['code'] == 'clear':
                wx.update({'code':'unknown','icon':'◌','label':'一部観測不能',
                           'subtitle':'欠測により安全と判断できません','score':None})
            elif wx['code'] != 'unknown':
                wx['subtitle'] += '（一部欠測の暫定予報）'
    difficulty_counts = {k: sum(x['difficulty'] == k for x in today_rows) for k in DIFFICULTY}
    by_day = []
    for days_ago in range(6, -1, -1):
        day = today - dt.timedelta(days=days_ago)
        sample = [x for x in rows if x['date'] == day.isoformat() or x['kev_date'] == day.isoformat()]
        by_day.append({'date': day.isoformat(), 'count': len(sample),
                       'kev': sum(x['kev_date']==day.isoformat() for x in sample),
                       'critical': sum(x['severity'] == 'CRITICAL' for x in sample),
                       'high': sum(x['severity'] == 'HIGH' for x in sample)})
    return {
        'schema_version': 1, 'brand': 'ResoArc SWWW',
        'title': 'Security Weather Watch Web', 'date': today.isoformat(),
        'yesterday': yesterday.isoformat(), 'generated_at': now.astimezone(JST).isoformat(),
        'checked_at': checked_at, 'age_minutes': age,
        'quality': quality,
        'source_status': {**{k: source_status.get(k, 'MISSING') for k in SOURCES},
                          **{k: extras_status.get(k, 'NOT_CONFIGURED' if not extra else 'MISSING') for k in EXTRA_SOURCES}},
        'source_errors_count': len(source_errors) + len(extra.get('errors', {}) if extra else {}),
        'source_count': len(SOURCES) + (len(EXTRA_SOURCES) if extra else 0),
        'coverage_note': 'CISA KEV・GitHub・PHP・OSV・NVD・JPCERT/CC・JVN・CISA注意喚起・Ubuntu USN・Debian DSA・CERT-EU・CIS・FIRST EPSSを横断観測。件数は収集範囲内での参考値で、世界全CVEの網羅ではありません。',
        'today': {'weather': forecast, 'new': len(today_rows),
                  'kev': sum(x['kev_date']==today.isoformat() for x in today_rows),
                  'critical': sum(x['severity'] == 'CRITICAL' for x in today_rows),
                  'high': sum(x['severity'] == 'HIGH' for x in today_rows),
                  'difficulty': difficulty_counts,
                  'confirmed_victims': sum(confirmed_victims) if confirmed_victims and len(confirmed_victims) == len(today_rows) else None,
                  'confirmed_victim_data_items': len(confirmed_victims),
                  'resoarc_impact_confirmed': sum(x['resoarc_impact'] == 'AFFECTED' for x in today_rows),
                  'resoarc_impact_unreviewed': sum(x['resoarc_impact'] == 'NOT_CONFIRMED' for x in today_rows)},
        'yesterday_summary': {'new': len(yesterday_rows), 'kev': sum(x['kev_date']==yesterday.isoformat() for x in yesterday_rows),
                              'weather': yesterday_forecast},
        'observed': {'total': len(rows), 'kev_14day': all_kev,
                     'priority_p1_outstanding': int(triage.get('counts', {}).get('P1', 0) or 0),
                     'priority_p2_outstanding': int(triage.get('counts', {}).get('P2', 0) or 0)},
        'bulletins': [x for x in (extra.get('bulletins', []) if extra else []) if isinstance(x,dict)][:100],
        'bulletin_count': len(extra.get('bulletins', []) if extra else []),
        'epss_enriched': sum(x['epss'] is not None for x in rows),
        'epss_high_count': sum(x['epss'] is not None and x['epss'] >= 0.5 for x in rows),
        'source_meta': extra.get('source_meta', {}) if extra else {},
        'sources_partial': [k for k,v in extras_status.items() if v != 'OK'],
        'trend': by_day, 'items': rows[:DISPLAY_LIMIT], 'items_displayed': min(len(rows), DISPLAY_LIMIT),
        'published_site': False,
        'disclaimer': 'EPSSは今後30日以内の悪用確率の推定値であって実際の悪用件数ではありません。CISA KEVは悪用確認情報であり、被害者数ではありません。P1は内部審査優先度です。掲載だけでResoArc製品への影響は確定しません。',
    }


def render_page(report, template):
    raw_json = json.dumps(report, ensure_ascii=False, separators=(',', ':'))
    safe_json = (raw_json.replace('<', '\\u003c').replace('>', '\\u003e')
                 .replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))
    return template.replace('__SWWW_DATA__', safe_json)


def main(argv=None):
    p = argparse.ArgumentParser(description='SWWW private daily vulnerability weather page')
    p.add_argument('--out', type=Path, required=True, help='existing private Security Watch output dir')
    p.add_argument('--template', type=Path, default=Path(__file__).resolve().with_name('weather_template.html'))
    p.add_argument('--date', help='YYYY-MM-DD (test/replay)')
    p.add_argument('--refresh', action='store_true', help='run existing collector first, never public deploy')
    args = p.parse_args(argv)
    refresh_failed = False
    if args.refresh:
        parent = Path(__file__).resolve().parent
        inventory = parent / 'inventory-public.json'
        cmd = [sys.executable, str(parent / 'run_cycle.py'), '--out', str(args.out), '--inventory-json', str(inventory)]
        try:
            finished = subprocess.run(cmd, timeout=230, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            refresh_failed = finished.returncode != 0
        except (OSError, subprocess.TimeoutExpired):
            refresh_failed = True
    if args.refresh:
        cmd = [sys.executable, str(Path(__file__).resolve().with_name('weather_sources.py')),
               '--out', str(args.out)]
        try:
            finished = subprocess.run(cmd, timeout=380, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # source failures are represented in its JSON output; do not drop partial results.
            if finished.returncode not in (0, 2): refresh_failed = True
        except (OSError, subprocess.TimeoutExpired):
            refresh_failed = True
    if args.date:
        given_date = dt.date.fromisoformat(args.date)
        now = dt.datetime.combine(given_date, dt.time(9, 10), tzinfo=JST)
    else:
        now = dt.datetime.now(JST)
    report = build_report(read_json(args.out / 'review-queue.json'),
                          read_json(args.out / 'triage-state.json'),
                          read_json(args.out / 'weather-assessments.json'),
                          now=now, refresh_failed=refresh_failed,
                          extra=read_json(args.out / 'security-weather-extras.json') or None)
    template = args.template.read_text(encoding='utf-8')
    page = render_page(report, template)
    target = args.out / 'security-weather'
    day = report['date']
    atomic_write(target / 'index.html', page)
    atomic_write(target / 'today.json', to_json(report))
    atomic_write(target / ('weather-' + day + '.json'), to_json(report))
    if report['quality'] in ('OK','PARTIAL'):
        atomic_write(target / ('daily-' + day + '.html'), page)
    print(json.dumps({'quality': report['quality'], 'date': day,
                      'today': report['today']['new'], 'observed_total': report['observed']['total'],
                      'output': str(target), 'publication': 'HOLD'}, ensure_ascii=False))
    return 0 if report['quality'] in ('OK','PARTIAL') else 2

if __name__ == '__main__':
    raise SystemExit(main())