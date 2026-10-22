#!/usr/bin/env python3
"""Generate safe, immutable API/RSS/Atom from the reviewed public SWWW snapshot.

Does not read any private assessments or machine inventories.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from swww_public import enrich, export_feeds

def generate(site):
    report_path=site/"security/weather/today.json"
    report=json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("quality") not in ("OK","PARTIAL"):
        raise ValueError("Decline to publish incomplete or invalid snapshot")
    if not isinstance(report.get("items"),list) or not report.get("date"):
        raise ValueError("Missing advisory collection")
    if report.get("resoarc_review",{}).get("scope")!="public_approved_only":
        raise ValueError("Private impact disclosure guard failed")
    private_fields=("affected_asset","internal_owner","investigation_notes",
                    "remediation","verification_ref","difficulty_evidence",
                    "security-weather-operations","weather-assessments")
    text=json.dumps(report,ensure_ascii=False)
    for forbidden in private_fields:
        if ('"'+forbidden+'":') in text or ('"'+forbidden+'": ') in text:
            raise ValueError("Private field in public snapshot: "+forbidden)
    enrich(report)
    catalog=export_feeds(report,site)
    root=site/"api/v1/swww"
    (root/"openapi.json").write_text(json.dumps({
      "openapi":"3.1.0",
      "info":{"title":"ResoArc SWWW Public Security Feed","version":"1.0.0",
        "description":"Read-only, human-reviewed public information. Technology tags do not mean ResoArc exposure."},
      "servers":[{"url":"https://resoarc.com"}],
      "paths":{
        "/api/v1/swww/advisories":{"get":{"summary":"Filtered public advisories (daily snapshot)",
          "parameters":[
            {"name":"q","in":"query","schema":{"type":"string","maxLength":120}},
            {"name":"technology","in":"query","schema":{"type":"string"}},
            {"name":"severity","in":"query","schema":{"type":"string","enum":["CRITICAL","HIGH","MEDIUM","LOW","UNKNOWN"]}},
            {"name":"source","in":"query","schema":{"type":"string"}},
            {"name":"date","in":"query","schema":{"type":"string","format":"date"}},
            {"name":"exploited","in":"query","schema":{"type":"string","enum":["true","false"]}},
            {"name":"page","in":"query","schema":{"type":"integer","minimum":1,"maximum":100}},
            {"name":"limit","in":"query","schema":{"type":"integer","minimum":1,"maximum":100}}
          ],
          "responses":{"200":{"description":"Public advisories and pagination metadata"},"400":{"description":"Invalid query"},"503":{"description":"Snapshot not available"}}}},
        "/api/v1/swww/summary":{"get":{"summary":"Current report metadata and technology categories",
          "responses":{"200":{"description":"Public daily summary"}}}},
        "/api/v1/swww/technologies":{"get":{"summary":"Available technology tags",
          "responses":{"200":{"description":"Tag taxonomy and counts"}}}},
        "/api/v1/swww/advisories.xml":{"get":{"summary":"Complete published catalog in XML","responses":{"200":{"description":"Read-only public XML"}}}},
        "/api/v1/swww/rss.xml":{"get":{"summary":"RSS 2.0 feed of recent public advisories","responses":{"200":{"description":"RSS XML"}}}},
        "/api/v1/swww/atom.xml":{"get":{"summary":"Atom 1.0 feed","responses":{"200":{"description":"Atom XML"}}}},
        "/api/v1/swww/feed.json":{"get":{"summary":"JSON Feed 1.1","responses":{"200":{"description":"JSON Feed"}}}}
      }
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Documentation uses the canonical ResoArc shell and is accessible without JavaScript.
    homepage=(site/"security/index.html").read_text(encoding="utf-8")
    header=homepage[homepage.index('<header class="site-header">'):homepage.index("</header>")+len("</header>")]
    footer=homepage[homepage.index('<footer class="footer">'):homepage.index("</footer>")+len("</footer>")]
    doc="""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,follow">
<title>SWWW 公開API・XML/RSSフィード | ResoArc</title>
<meta name="description" content="SWWW脆弱性天気予報の公開JSON API・XML・RSS・Atom購読。認証不要、読み取り専用。">
<link rel="canonical" href="https://resoarc.com/api/v1/swww/">
<link rel="stylesheet" href="/assets/site-20261015-v10.css?v=20261018-design-v1">
<link rel="stylesheet" href="/assets/navigation.css">
</head><body>
<a class="skip-link" href="#main">本文へ移動</a>
{header}
<main id="main"><div class="container" style="padding-top:32px;padding-bottom:80px">
<p><a href="/security/weather/">SWWW 脆弱性天気予報</a> / 公開API</p>
<h1>SWWW 公開API・データ配信</h1>
<p>一般公開の脆弱性情報を第三者が再利用できるよう、JSON検索APIとXMLフィードを提供しています。認証不要・読み取り専用です。</p>
<p>対象は<strong>公開承認済みの日次スナップショット</strong>です。過去の全CVEを網羅するDBではなく、配信日の情報・集計範囲・取得品質を必ず確認してください。</p>
<section><h2>JSON API</h2>
<ul>
<li><a href="https://resoarc.com/api/v1/swww/advisories?technology=java&amp;limit=20">Javaの脆弱性情報を検索（JSON）</a></li>
<li><a href="https://resoarc.com/api/v1/swww/advisories?technology=oracle&amp;limit=20">Oracleの脆弱性情報を検索（JSON）</a></li>
<li><a href="https://resoarc.com/api/v1/swww/advisories?severity=CRITICAL&amp;limit=20">重大度CRITICALだけを検索</a></li>
<li><a href="https://resoarc.com/api/v1/swww/summary">日次サマリー</a></li>
<li><a href="https://resoarc.com/api/v1/swww/technologies">技術タグと件数</a></li>
<li><a href="/api/v1/swww/openapi.json">OpenAPI 3.1 仕様</a></li>
</ul>
<p>絞り込みは <code>q</code>、<code>technology</code>、<code>severity</code>、<code>source</code>、<code>date</code>、<code>exploited</code>、<code>page</code>、<code>limit</code> を指定できます。1ページの取得上限は100件です。</p></section>
<section><h2>XML・購読用フィード</h2>
<ul>
<li><a href="/api/v1/swww/advisories.xml">XML（公開カタログ全件）</a></li>
<li><a href="/api/v1/swww/rss.xml">RSS 2.0（最新100件）</a></li>
<li><a href="/api/v1/swww/atom.xml">Atom 1.0（最新100件）</a></li>
<li><a href="/api/v1/swww/feed.json">JSON Feed 1.1（最新100件）</a></li>
<li><a href="/api/v1/swww/catalog.json">公開カタログ（JSON一括）</a></li>
</ul></section>
<section><h2>安全性と利用条件</h2>
<p>配信データにResoArc内部のホスト、担当者、調査メモ、非公開の対策手順は含めません。技術タグはアドバイザリー本文に登場した技術を示すもので、ResoArcでの使用・影響を証明しません。</p>
<p>原文の著作権・ライセンスは各提供元に帰属します。詳細な修正情報はリンク元で確認してください。ResoArcの統合集計に第三者の権利まで含む再配布許諾が与えられているわけではありません。</p>
<p>毎日の公開更新は現状手動審査制です。RSS等の更新日時が古い場合、現在の安全状態を示しません。CORS対応のJSON APIは非認証・読み取り専用で提供しています。</p>
</section>
</div></main>
{footer}
<script defer src="/assets/navigation.js"></script>
</body></html>"""
    doc=doc.replace('style="padding-top:32px;padding-bottom:80px"','')
    (root/"index.html").write_text(doc.format(header=header,footer=footer),encoding="utf-8",newline="\n")
    assert catalog["available_records"]==len(report["items"])
    assert catalog["source_count"]==report["source_count"]
    assert catalog["report_date"]==report["date"]
    print("API_GENERATED",root,"items",len(catalog["advisories"]),
          "tags",len(report["technology_summary"]),"feed",len(catalog["advisories"][:100]))
    return catalog

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--site",required=True,type=Path)
    args=parser.parse_args()
    generate(args.site)
