#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc contributors
# SPDX-License-Identifier: MIT
"""Generate future SWWW newspaper issues from reviewed public facts, not imaginary headlines.

For Oct 23 the first edition remains carefully edited; later issues use a
transparent rule-based editorial policy. Never invent a patch version, actual
exploit, victim, or ResoArc exposure. Quality failures do not alter any page.
"""
from __future__ import annotations
import argparse,collections,datetime as dt,hashlib,html,json,pathlib,re,shutil,sys
from urllib.parse import urlsplit
import generate_newspaper as paper

FIRST_DATE="2026-10-23"
SEVERITY={"CRITICAL":4,"HIGH":3,"MEDIUM":2,"LOW":1,"UNKNOWN":0}
IMPACT=[
 ("遠隔コード実行の可能性","remote code execution","rce","arbitrary code execution","command injection"),
 ("認証回避・認可の問題","authentication bypass","authorization bypass","auth bypass","token forgery","privilege bypass"),
 ("SQLインジェクションの可能性","sql injection"),
 ("権限昇格の可能性","privilege escalation","elevation of privilege"),
 ("クロスサイトスクリプティング（XSS）","cross-site scripting","xss"),
 ("サービス停止・過負荷の可能性","denial of service","dos","resource exhaustion","uncontrolled resource consumption","cpu spin","quadratic"),
 ("情報漏えい・不正な読み取り","information disclosure","sensitive information","data exposure","out-of-bounds read","memory disclosure"),
 ("不正なファイル操作","arbitrary file","path traversal","directory traversal","file write"),
 ("メモリ安全性の問題","buffer overflow","heap-buffer-overflow","use-after-free","memory corruption"),
 ("検証・入力処理の問題","injection","prototype pollution","validation","improper input"),
]
POPULAR=["Java","Oracle","Linux","Windows","PHP","Python","Node.js","Chrome","WordPress","Next.js","React","Django","Pillow","PostgreSQL","Apache"]

def label(row):
    title=str(row.get("title") or "")
    head=title.split(":",1)[0].strip()
    if not head or re.match(r"^(CVE|GHSA)-",head,re.I) or len(head)>52:
        tags=row.get("technologies",[])
        head=(tags[0].get("label","") if tags else "") or str(row.get("source","公開ソフトウェア"))
    return head[:52].strip() or "公開ソフトウェア"

def category(row):
    text=" ".join(str(row.get(k) or "") for k in ("title","summary")).lower()
    for entry in IMPACT:
        if any(word in text for word in entry[1:]):
            return entry[0]
    return "セキュリティ上の問題"

def story(row,short=False):
    name=label(row)
    problem=category(row)
    sev=str(row.get("severity","UNKNOWN"))
    desc="公開元の情報では「"+name+"」に関する「"+problem+"」が報告されています。"
    if sev in ("CRITICAL","HIGH"):
        desc+="SWWWでは重大度"+sev+"として収録されています。"
    desc+="対象バージョンと発生条件、修正・回避方法はリンク先の公式情報で確認してください。"
    if short:desc=desc[:170]
    return {
       "head":name+"："+problem,
       "blurb":desc,
       "check":"この製品を使用しているか、該当バージョン・機能に合致するかを確認し、提供元の修正版と回避策を確認。",
       "tag":name,
    }

def scored(row):
    epss=row.get("epss")
    try:e=min(1,max(0,float(epss))) if epss is not None else 0
    except (TypeError,ValueError):e=0
    sev=SEVERITY.get(row.get("severity","UNKNOWN"),0)
    kev=int(bool(row.get("known_exploited")))
    return (kev,sev,e,int(category(row)!="セキュリティ上の問題"),str(row.get("published_date","")),str(row.get("id","")))

def picks(rows,n=8):
    # Public feeds can report the same advisory ID through GitHub and OSV.
    # Keep source records for provenance, but avoid repeating one headline.
    ordered=sorted(rows,key=scored,reverse=True)
    result=[];groups=collections.Counter();seen=set()
    for row in ordered:
        advisory_id=str(row["id"])
        vendor=label(row).lower()
        if advisory_id in seen or groups[vendor]>=2:continue
        result.append(row);groups[vendor]+=1;seen.add(advisory_id)
        if len(result)>=n:break
    if len(result)<min(n,len({str(x["id"]) for x in rows})):
        for row in ordered:
            advisory_id=str(row["id"])
            if advisory_id not in seen:
                result.append(row);seen.add(advisory_id)
                if len(result)>=n:break
    return result[:n]

def data_hash(data):
    return hashlib.sha256(json.dumps({"items":data["items"],"technologies":data["technologies"]},
                    ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()

def coverage(meta):
    return "前日付の注目情報" if int(meta.get("carryover_count",0)) else "本日掲載の情報"

def big_story(rows,meta):
    if not rows:
        return ('''<div class="eyebrow">TODAY / ZERO ADVISORIES</div>
<div class="lead-grid"><article class="lead-story">
<h2 class="lead-title">本日の追加掲載は、<br>ありませんでした。</h2>
<p class="deck">情報源の確認が正常に終了し、今回の掲載対象は0件でした。
ただし、新たな脆弱性や悪用が世界中で存在しないという意味ではありません。</p>
<p>昨日までの掲載情報やお使いの製品に関する情報は、通常版のSWWWから検索できます。</p>
</article><aside class="metabox"><h2>本日の掲載情報</h2><div class="metric"><span>新たな掲載</span><strong>0</strong></div></aside></div>''')
    prior=int(meta.get("carryover_count",0))>0
    lead_notice=(f"本日付の新着掲載は0件です。前日付の公開情報{meta.get('carryover_total',len(rows))}件から"
                 f"注目情報{len(rows)}件を選んでいます。前日の情報を今日の新着とは扱いません。") if prior else ""
    ordered=picks(rows,8)
    main=ordered[0];f=story(main)
    crit=sum(x.get("severity")=="CRITICAL" for x in rows)
    high=sum(x.get("severity")=="HIGH" for x in rows)
    cards=[]
    for row in ordered[1:4]:
        detail=story(row,True)
        cards.append(f'''<article class="teaser">
<span class="story-kicker">編集部の注目</span>
<h3>{paper.e(detail["head"])}</h3>
<p>{paper.e(detail["blurb"])}</p>{paper.tag(detail["tag"])}{paper.anchor(row,"原文を確認 ↗")}
</article>''')
    return f'''<div class="eyebrow">TOP STORY / {coverage(meta)}</div>
<div class="lead-grid"><article class="lead-story">
<div class="story-kicker">SWWW注目記事・{paper.e(main.get("severity","未評価"))}</div>
<h2 class="lead-title">{paper.e(f["head"])}</h2>
<p class="deck">{paper.e(f["blurb"])}</p>
<p>まずは、ご自身の環境でこの製品を使っているか、影響対象の版や機能を使っているかを確認してください。
実際の悪用やResoArcへの影響を確認したという意味ではありません。</p>
<div class="byline">出典：{paper.e(main.get("source","公開情報"))} / {paper.anchor(main)}</div>
</article>
<aside class="metabox"><h2>朝刊を数字で読む</h2>
<div class="metric"><span>{coverage(meta)}</span><strong>{len(rows)}</strong></div>
<p class="note">{paper.e(lead_notice)}</p>
<div class="metric"><span>SWWW CRITICAL</span><strong>{crit}</strong></div>
<div class="metric"><span>SWWW HIGH</span><strong>{high}</strong></div>
<div class="metric"><span>品質</span><strong>OK</strong></div>
<p class="note">掲載日と発見日・対策日・被害件数は異なります。</p></aside></div>
<div class="visual"><div><strong>警報は、<br>読む順番で変わる。</strong><small>THE SECURITY MORNING PAPER</small></div>
<span class="orb" aria-hidden="true"></span></div>
<hr class="break"><h2 class="sectitle">注目記事 <small>EDITOR'S PICK</small></h2>
<div class="story-columns">{''.join(cards) if cards else '<p>本日追加の注目記事はありません。</p>'}</div>
<div class="ed-note"><strong>編集部から：重大度だけで判断しない。</strong>
<p>SWWWの集計は重要度の目安です。実際の危険度は製品の導入状況、バージョン、公開状態、悪用確認などで変わります。
原文と自分の環境を照合しましょう。</p></div>
<div class="bottomrail"><div class="quote">31件でも、300件でも。<br>まず自分に関係する情報から。</div>
<div class="small"><b>読むコツ</b><br>2面のランキングは編集部の閲覧優先順位。
3面は技術名から探し、4面で確認手順をまとめています。</div></div>
'''

def ranking(rows,meta):
    entries=[]
    for i,row in enumerate(picks(rows),1):
        f=story(row)
        epss=row.get("epss")
        epss_info= "" if epss is None else f"<p>EPSS参考値：{paper.e(epss)}</p>"
        entries.append(f'''<article class="rank"><div class="num">{i:02d}</div>
<div><h3>{paper.e(f["head"])}</h3>
<p>{paper.e(f["blurb"])}</p>
{paper.label(row)}{paper.tag(f["tag"])}<br>{paper.anchor(row)}</div>
<aside class="rank-side"><b>確認すること</b>{paper.e(f["check"])}{epss_info}</aside></article>''')
    return f'''<div class="section-head"><h2>注目の{len(entries)}件を読む。</h2><span>2面　注目ランキング</span></div>
<p class="deck">{coverage(meta)}を、重大度・公開元の情報・技術の多様性をもとに並べました。
この順位は攻撃発生数や組織への影響順位ではありません。</p>
<div class="census"><div><strong>{len(entries)}本</strong><small>注目の選抜記事</small></div>
<div><strong>{len(rows)}件</strong><small>{coverage(meta)}</small></div>
<div><strong>{len(rows)}件</strong><small>ResoArc影響は未判定</small></div></div>
<div class="ed-note"><strong>注意：自動編集した紙面です。</strong>
<p>見出しは技術カテゴリのルールによる日本語要約であり、修正版や被害の有無を独自確認したものではありません。
製品名・版・影響条件は必ず一次情報で確認してください。</p></div>
<div class="rank-list">{''.join(entries)}</div>'''

def technologies(rows,tags,meta):
    counts=collections.Counter(tag.get("label") or tag.get("id") for x in rows for tag in x.get("technologies",[]))
    frequent=counts.most_common(8)
    items=[]
    for tech,n in frequent:
        items.append(f'''<article class="tech-feature"><span class="eyebrow">{coverage(meta)}・{n}件</span>
<h3>{paper.e(tech)}</h3><p>同じ技術タグが付いた記事です。使用バージョンや影響の有無は別途確認が必要です。</p></article>''')
    if not items:items.append("<p>本日分の技術タグ付き記事はありません。</p>")
    bars=[]
    tags=sorted(tags,key=lambda x:-int(x.get("count",0)))[:10]
    max_count=max([int(t["count"]) for t in tags] or [1])
    for t in tags:
        w=max(5,min(100,5*round(20*int(t["count"])/max_count)))
        label_=t.get("label") or t.get("id","")
        bars.append(f'''<div class="barrow"><span>{paper.e(label_)}</span>
<div class="bar" aria-hidden="true"><i class="w{w}"></i></div><b>{int(t["count"]):,}</b></div>''')
    return f'''<div class="section-head"><h2>技術名から選んで読む。</h2><span>3面　技術・製品</span></div>
<p class="deck">紙面で扱う情報に多く登場する分野と、収録データ全体の技術を分けて表示します。</p>
<div class="tech-grid"><section><h2 class="sectitle">注目記事の技術別件数 <small>FEATURED</small></h2>{''.join(items)}</section>
<section><h2 class="sectitle">収録データのタグ傾向 <small>ARCHIVE</small></h2>
<div class="barlist">{''.join(bars)}</div>
<p class="data-key">こちらは本日分だけの件数ではありません。多い順は危険な順ではなく、複数のタグを持つ記事もあります。</p>
</section></div>
<hr class="break"><div class="ed-note"><strong>「使っているか」が最初の絞り込み。</strong><p>
Java・Oracle・PHP・Python・OS・CMSなどの情報は<a href="https://resoarc.com/api/v1/swww/technologies">SWWWの技術タグAPI</a>から確認できます。
導入されていない製品のニュースは、自組織の対応優先度を下げられます。</p></div>'''

def action(rows,meta):
    if not rows:
        context='<p>今回新たに掲載されたものはありませんが、未対応の過去記事とソフトウェア資産の確認を続けましょう。</p>'
    else:
        f=story(picks(rows,1)[0])
        context=f'''<h3>{coverage(meta)}：{paper.e(f["head"])}</h3>
<p>{paper.e(f["check"])}</p>{paper.anchor(picks(rows,1)[0])}'''
    return f'''<div class="section-head"><h2>読んだら、次に何をする？</h2><span>4面　行動のガイド</span></div>
<p class="deck">脆弱性情報は、不安を増やすよりも確認作業を簡単にするために使いましょう。</p>
<div class="actiongrid"><section><h2 class="sectitle">確認はこの順番で</h2>
<ol class="checklist">
<li><b>使っている製品を棚卸し</b><p>アプリ、OS、依存ライブラリ、外部サービスを確認。採用していない技術はひとまず後回し。</p></li>
<li><b>対象バージョンと条件を照合</b><p>同じ製品でもすべてのバージョン・設定が影響するとは限りません。</p></li>
<li><b>修正版・回避策を原文で確認</b><p>アドバイザリー発行元の公式情報を優先し、誤った更新を防ぎます。</p></li>
<li><b>テストと切り戻しを準備</b><p>業務停止、設定変更、互換性の問題がないか確認してから更新します。</p></li>
<li><b>根拠と結果を残す</b><p>対応済み・未対応・対象外の判断を、日付やテスト記録とともに管理します。</p></li>
</ol></section>
<aside><article class="article"><span class="eyebrow">TODAY'S FOCUS</span>{context}</article>
<article class="article"><h3>ResoArcへの影響は別途確認</h3>
<p>SWWWは公開情報の集約サービスです。一般公開記事に関連技術が現れても、ResoArc製品やVPSが影響を受けると判定されたわけではありません。</p></article></aside></div>
<hr class="break"><h2 class="sectitle">ニュースを読むための短い辞典</h2>
<div class="story-columns">
<article class="teaser"><h3>CRITICAL / HIGH</h3><p>技術的な重大度の区分。実際に攻撃や被害が確認されたという意味ではありません。</p></article>
<article class="teaser"><h3>EPSS / KEV</h3><p>EPSSは悪用確率の予測指標、KEVはCISAが悪用を確認した脆弱性リストです。空欄は「悪用なし」と同じではありません。</p></article>
<article class="teaser"><h3>掲載日と公開日</h3><p>「今日の掲載」はSWWWが扱う日付。発見・公開・修正の日付とは異なる場合があります。</p></article>
</div>
<div class="ed-note"><strong>今日の結論。</strong><p>全件を読むより、使っている技術と該当バージョンを絞って確認する。知らない製品のニュースで焦る必要はありません。</p></div>'''

def validate(data):
    assert set(data)=={"metadata","items","technologies"}
    m=data["metadata"];rows=data["items"]
    assert m["quality"]=="OK" and 10<=int(m["source_count"])<=30
    date=dt.date.fromisoformat(m["date"])
    ts=dt.datetime.fromisoformat(m["generated_at"])
    assert ts.tzinfo is not None and ts.date()==date
    assert 0<=len(rows)==m["published_date_count"]<=700
    same=int(m.get("same_day_count",len(rows)))
    carry=int(m.get("carryover_count",0))
    assert same>=0 and carry>=0 and same+carry==len(rows)
    assert not (same and carry)
    # Advisory IDs are unique per source, not globally unique across feeds.
    identities=[(str(x["source"]),str(x["id"])) for x in rows]
    if len(set(identities))!=len(rows):
        raise ValueError("duplicate_advisory_within_same_source")
    for row in rows:
        assert row["resoarc_impact"] in ("NOT_CONFIRMED","UNREVIEWED")
        assert row["resoarc_response"]=="UNREVIEWED"
        expected=(date-dt.timedelta(days=1)).isoformat() if carry else m["date"]
        assert row["published_date"]==expected
        assert row["severity"] in SEVERITY
        url=urlsplit(row["url"])
        assert url.scheme=="https" and url.hostname
        assert len(row["title"])<=300 and len(row["summary"])<=400
    return m,rows

def make(data,site):
    meta,rows=validate(data)
    assert meta["date"]>=FIRST_DATE
    out=pathlib.Path(site)/"security/weather/newspaper"
    existing=out/"edition.json"
    if existing.exists():
        old=json.loads(existing.read_text(encoding="utf-8"))
        old_date=old["edition_date"]
        if meta["date"]<old_date:raise ValueError("Refuse to replace newer issue with an older one")
        if meta["date"]>old_date:
            previous=out/"all/index.html"
            if not previous.exists():raise FileNotFoundError("Missing previous print issue; no archive")
            archive=out/"archive"/old_date/"index.html"
            archive.parent.mkdir(parents=True,exist_ok=True)
            archive.write_bytes(previous.read_bytes())
    if meta["date"]==FIRST_DATE and all(x in {r['id'] for r in rows} for x in paper.PRIORITY_IDS+list(paper.ISSUES)):
        # Precisely the previously reviewed launch issue, not reused for future dates.
        bodies=[paper.top_story(rows,meta),paper.ranking(rows),
                paper.tech_page(rows,data["technologies"],meta),paper.action_page(rows,meta)]
    else:
        bodies=[big_story(rows,meta),ranking(rows,meta),
                technologies(rows,data["technologies"],meta),action(rows,meta)]
    pages=[paper.page_shell(i,bodies[i],data) for i in range(4)]
    for i,(rel,_,_) in enumerate(paper.SECTIONS):
        file=out/rel
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(paper.document(i,pages[i],meta),encoding="utf-8",newline="\n")
    combined=out/"all/index.html"
    combined.parent.mkdir(parents=True,exist_ok=True)
    combined.write_text(paper.document(0,"".join(pages),meta),encoding="utf-8",newline="\n")
    # The initial issue has an archive entry too; later issues keep it immutable.
    if meta["date"]==FIRST_DATE:
        archived=out/"archive"/FIRST_DATE/"index.html"
        archived.parent.mkdir(parents=True,exist_ok=True)
        archived.write_bytes(combined.read_bytes())
    issue={"schema_version":"1.0","edition_date":meta["date"],"generated_at":meta["generated_at"],
           "source_count":meta["source_count"],"quality":"OK",
           "published_date_count":len(rows),"same_day_count":int(meta.get("same_day_count",len(rows))),
           "carryover_count":int(meta.get("carryover_count",0)),
           "carryover_total":int(meta.get("carryover_total",0)),
           "content_sha256":data_hash(data),"render_version":"newspaper-daily-2",
           "model":"rules_and_verified_editorial",
           "notice":"公開品質に合格した情報のみ使用。前日付の情報は新着と明確に区別。PARTIALは発行しません。"}
    existing.write_text(json.dumps(issue,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"edition.json.license").write_text("SPDX-FileCopyrightText: 2026 ResoArc contributors\nSPDX-License-Identifier: MIT\n",encoding="utf-8")
    archive_dates=sorted((x.name for x in (out/"archive").iterdir() if x.is_dir()),reverse=True)
    archive_cards="".join(f'<li><a href="/security/weather/newspaper/archive/{paper.e(day)}/">{paper.e(day)}号（4面まとめて読む）</a></li>' for day in archive_dates)
    archive_content=f'''<!doctype html><!--
SPDX-FileCopyrightText: 2026 ResoArc contributors
SPDX-License-Identifier: MIT
--><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SWWW 脆弱性朝刊 過去号 | ResoArc</title><meta name="robots" content="noindex,follow">
<link rel="stylesheet" href="/assets/swww-newspaper.css"></head><body>
<div class="portal"><div class="portal-inner"><a class="logo" href="/">ResoArc</a>
<a href="/os/">ResoArcOS</a><a href="/security/weather/newspaper/">最新号へ</a></div></div>
<main class="paper"><header class="masthead"><h1>脆弱性朝刊</h1></header>
<div class="double-rule"></div><div class="section-head"><h2>バックナンバー</h2><span>ARCHIVE</span></div>
<p>公開品質に合格した紙面のみ保存しています。各号の掲載日は当日発見されたことを意味しません。</p>
<ul class="source-list">{archive_cards}</ul></main></body></html>'''
    archive_index=out/"archive/index.html"
    archive_index.write_text(archive_content,encoding="utf-8",newline="\n")
    print("SWWW_NEWSPAPER_DAILY_READY",meta["date"],len(rows),len(archive_dates),"archived issues")
    return issue

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True);p.add_argument("--site",required=True)
    args=p.parse_args()
    content=json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    make(content,args.site)
if __name__=="__main__":main()
