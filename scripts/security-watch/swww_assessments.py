#!/usr/bin/env python3
'''Privacy boundary for vulnerability reviews: private details never enter the public SWWW feed.'''
from __future__ import annotations
import datetime as dt
import html
import json
from pathlib import Path

RESPONSES = {
    'UNREVIEWED': '未審査',
    'INVESTIGATING': '調査中',
    'PLANNED': '対策予定',
    'MITIGATING': '対策中',
    'REMEDIATED': '対応済み',
    'MONITORING': '経過監視',
    'NOT_APPLICABLE': '対象外',
    'BLOCKED': '対応保留',
}
IMPACTS = {'NOT_CONFIRMED':'未判定','AFFECTED':'影響確認','NOT_AFFECTED':'影響なしを確認'}
DIFFICULTIES = ('easy','moderate','hard','unknown')

def get_review(assessments, key, advisory_id):
    if not isinstance(assessments,dict):return {}
    review=assessments.get(key)
    if not isinstance(review,dict):review=assessments.get(advisory_id)
    return review if isinstance(review,dict) else {}

def public_projection(review):
    # Explicit disclosure + human reviewer + timestamp + evidence required.
    # NEVER serialize private hostnames, assets, notes, owners, or fix commands.
    if (not isinstance(review,dict) or review.get('public_approved') is not True
        or not str(review.get('reviewed_by','')).strip()
        or not str(review.get('reviewed_at','')).strip()
        or not str(review.get('evidence_ref','')).strip()):
        return {}
    if not str(review['reviewed_at']).startswith('20'):
        return {}
    impact=review.get('resoarc_impact','NOT_CONFIRMED')
    response=review.get('response_status','UNREVIEWED')
    difficulty=review.get('difficulty','unknown')
    if impact not in IMPACTS:impact='NOT_CONFIRMED'
    if response not in RESPONSES:response='UNREVIEWED'
    if difficulty not in DIFFICULTIES or not str(review.get('difficulty_evidence','')).strip():
        difficulty='unknown'
    # Claims of remediation must be supported by a recorded verification.
    if response=='REMEDIATED' and not str(review.get('verification_ref','')).strip():
        response='INVESTIGATING'
    return {'resoarc_impact':impact,'response_status':response,'difficulty':difficulty}

def private_register(public_report, assessments, triage, operations):
    # Kept under mode 0700 private directory, NEVER copied to site/ or today.json.
    latest=public_report.get('date')
    rows=[]
    for item in public_report.get('items',[]):
        if item.get('date')!=latest and item.get('kev_date')!=latest:
            continue
        review=get_review(assessments,item.get('key',''),item.get('id',''))
        rows.append({
            'id':item.get('id'),'source':item.get('source'),'severity':item.get('severity'),
            'title':item.get('title'),
            'impact': review.get('resoarc_impact','NOT_CONFIRMED') if review.get('resoarc_impact') in IMPACTS else 'NOT_CONFIRMED',
            'response': review.get('response_status','UNREVIEWED') if review.get('response_status') in RESPONSES else 'UNREVIEWED',
            'difficulty': review.get('difficulty','unknown') if review.get('difficulty') in DIFFICULTIES else 'unknown',
            'affected_asset':str(review.get('affected_asset',''))[:200],
            'internal_owner':str(review.get('internal_owner',''))[:100],
            'investigation_notes':str(review.get('investigation_notes',''))[:1000],
            'remediation':str(review.get('remediation',''))[:1000],
            'evidence_ref':str(review.get('evidence_ref',''))[:200],
            'difficulty_evidence':str(review.get('difficulty_evidence',''))[:400],
            'verification_ref':str(review.get('verification_ref',''))[:200],
            'reviewed_at':str(review.get('reviewed_at',''))[:60],
            'public_approved':review.get('public_approved') is True,
        })
    if not isinstance(operations,list):operations=[]
    safe_ops=[]
    for event in operations:
        if not isinstance(event,dict):continue
        safe_ops.append({k:str(event.get(k,''))[:900] for k in
                         ('date','title','status','scope','notes','verification_ref')})
    return {
      'schema_version':1,'visibility':'PRIVATE_NEVER_PUBLISH',
      'date':latest,'generated_at':public_report.get('generated_at'),
      'count_today':len(rows),
      'impact_counts':{k:sum(x['impact']==k for x in rows) for k in IMPACTS},
      'response_counts':{k:sum(x['response']==k for x in rows) for k in RESPONSES},
      'backlog_p1':int(triage.get('counts',{}).get('P1',0) or 0),
      'backlog_p2':int(triage.get('counts',{}).get('P2',0) or 0),
      'entries':rows,'operations':safe_ops,
      'disclaimer':'対応記録は調査員の根拠付き評価です。一般情報源に掲載されてもResoArcへの影響は確定しません。'
    }

def private_html(register):
    esc=lambda x:html.escape(str(x or ''),quote=True)
    lines=[]
    for r in register['entries']:
        lines.append('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in
          (r['id'],r['severity'],IMPACTS[r['impact']],RESPONSES[r['response']],r['difficulty'],
           r['affected_asset'] or '記録なし',r['internal_owner'] or '未割当',
           r['investigation_notes'] or '未記録',r['remediation'] or '未記録',r['evidence_ref'] or 'なし'))+'</tr>')
    ops=[]
    for o in register['operations']:
        ops.append('<tr>'+''.join('<td>'+esc(o.get(k))+'</td>' for k in
          ('date','title','status','scope','notes','verification_ref'))+'</tr>')
    style='''body{font:15px/1.6 system-ui,sans-serif;background:#f5f7f9;color:#18304c;margin:0}
    main{max-width:1200px;margin:35px auto;padding:0 20px}h1{font-size:26px}h2{font-size:20px;margin-top:36px}
    .tag{display:inline-block;color:white;background:#18304c;padding:5px 12px}
    .box{background:#fff;border:1px solid #d5dee8;padding:20px;margin-top:20px}
    .scroll{overflow:auto}table{border-collapse:collapse;width:100%;background:#fff;min-width:1000px}
    th,td{padding:9px 12px;border-bottom:1px solid #d5dee8;text-align:left;vertical-align:top}
    th{background:#ebf0f5}small{color:#586c81}'''
    return ('''<!doctype html><html lang="ja"><head><meta charset="utf-8">
      <meta name="robots" content="noindex,nofollow,noarchive">
      <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
      <title>ResoArc SWWW 内部評価台帳</title><style>'''+style+'''</style></head><body><main>
      <span class="tag">PRIVATE / 社内向け・非公開</span><h1>SWWW / ResoArc影響・対応状況</h1>
      <p>観測日：'''+esc(register['date'])+'''　審査対象：'''+esc(register['count_today'])+'''件</p>
      <div class="box">未判定：'''+esc(register['impact_counts']['NOT_CONFIRMED'])+'''件／影響確認：'''+esc(register['impact_counts']['AFFECTED'])+'''件
      ／対応済み：'''+esc(register['response_counts']['REMEDIATED'])+'''件／未審査：'''+esc(register['response_counts']['UNREVIEWED'])+'''件</div>
      <p><small>これはVPSの保護された領域に生成する内部台帳です。公開サイトへアップロードしないでください。
      「未判定」は安全確認を意味しません。対応履歴はCVE影響判定と独立しています。</small></p>
      <h2>日付別の審査リスト</h2><div class="scroll"><table><thead><tr>
      <th>ID</th><th>重大度</th><th>ResoArc影響</th><th>対応</th><th>難易度</th>
      <th>対象資産</th><th>担当</th><th>調査メモ</th><th>修正内容</th><th>根拠</th>
      </tr></thead><tbody>'''+''.join(lines)+'''</tbody></table></div>
      <h2>基盤への対応履歴（CVE別の影響確定とは別）</h2>
      <div class="scroll"><table><thead><tr><th>日付</th><th>作業</th><th>状態</th><th>範囲</th><th>内容</th><th>確認根拠</th>
      </tr></thead><tbody>'''+''.join(ops)+'''</tbody></table></div>
      </main></body></html>''')
