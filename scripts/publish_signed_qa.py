#!/usr/bin/env python3
"""Prepare signed kintone install-test packages with keys stored OUTSIDE the repo.
Requires locally installed official @kintone/cli. Never publishes private keys.
These builds are for sandbox verification, not approved production releases.
"""
from __future__ import annotations
import hashlib,html,json,os,re,subprocess,zipfile,io
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"site/downloads"
KEYS=Path.home()/"Documents/AI-Work/ResoArc/private-plugin-keys"
DEFAULT=Path.home()/"Documents/AI-Work/ResoArc/kintone-pack-tool/node_modules/.bin/cli-kintone.cmd"
CLI=Path(os.environ.get("RESOARC_CLI",str(DEFAULT)))
V=[
("auto-number","v1.1.0-beta","自動採番"),
("tabs","v0.1.0-beta","タブ表示"),
("conditional","v0.1.0-alpha","条件付き表示・必須制御"),
("conditional-format","v0.1.0-alpha","条件付き書式"),
("date-calculator","v0.1.0-alpha","日付・期間計算"),
("list-search","v0.1.0-alpha","高機能検索・絞り込み"),
("grid-editor","v0.1.0-alpha","Excel風一覧編集"),
("kanban","v0.1.0-alpha","カード・カンバン表示")
]
def cli(*args):
 p=subprocess.run([str(CLI),*args],capture_output=True,text=True,encoding="utf-8",errors="replace")
 if p.returncode:raise RuntimeError("cli-kintone failed: "+" ".join(args[:2])+" "+p.stderr[-250:])
 return p.stdout

def prepare():
 if not CLI.is_file():raise RuntimeError("Install official @kintone/cli outside the repository first")
 if not KEYS.is_dir():raise RuntimeError("Missing local private keys; do not publish fake signed packages")
 OUT.mkdir(parents=True,exist_ok=True)
 entries=[]
 for slug,version,title in V:
  source=ROOT/"plugins"/slug/version/"src"
  key=KEYS/(slug+".ppk")
  if not key.is_file():raise RuntimeError("Missing stable private key for "+slug+"; do not silently change plugin IDs")
  target=OUT/("resoarc-"+slug+"-signed-qa.zip")
  cli("plugin","pack","--input",str(source/"manifest.json"),"--output",str(target),"--private-key",str(key))
  info=json.loads(cli("plugin","info","--input",str(target),"--format","json"))
  with zipfile.ZipFile(target) as outer:
   if set(outer.namelist())!={"contents.zip","PUBKEY","SIGNATURE"}:raise ValueError(slug+": invalid signed wrapper")
   with zipfile.ZipFile(io.BytesIO(outer.read("contents.zip"))) as inside:
    for name in inside.namelist():
     relative=source/name
     if name.startswith("/") or ".." in Path(name).parts or not relative.is_file():raise ValueError(slug+": unexpected packaged resource "+name)
     if inside.read(name)!=relative.read_bytes():raise ValueError(slug+": source/packed mismatch "+name)
    manifest=json.loads(inside.read("manifest.json"))
    if info["version"]!=manifest["version"]:raise ValueError(slug+": version mismatch")
  sha=hashlib.sha256(target.read_bytes()).hexdigest()
  entries.append(dict(slug=slug,name=title,plugin_id=info["id"],version=version,sha256=sha,bytes=target.stat().st_size,filename=target.name))
 qa_manifest=OUT/"resoarc-signed-qa-manifest.json"
 qa_manifest.write_text(json.dumps({"notice":"SIGNED_QA_ONLY_NOT_TENANT_TESTED","plugins":entries},ensure_ascii=False,indent=2)+"\n",encoding="utf8",newline="\n")
 reference=(ROOT/"site"/"os"/"pi"/"index.html").read_text(encoding="utf8")
 first=reference.split("<main",1)[0]
 ending="</main>".join(reference.split("</main>")[1:]) # body footer portion after first main
 first=first.replace("ResoArcOS Raspberry Pi 開発プレビュー | ResoArc","kintoneプラグイン導入検証版 | ResoArc")
 cards=[]
 for item in entries:
  name=html.escape(item["name"]);url="/downloads/"+item["filename"]
  cards.append(f'<article class="product-card"><div class="product-meta"><span>署名ZIP・検証専用</span><span>{item["version"]}</span></div><h3>{name}</h3><p>専用のテストアプリへ新規導入して、動作と権限を確認してください。既存版とプラグインIDが異なる可能性があります。</p><div class="product-tags"><span>実機未検証</span><span>本番環境での利用非推奨</span></div><a class="product-cta" href="{url}" download>署名済みQA版ZIP <span aria-hidden="true">↘</span></a><p>プラグインID: <code>{item["plugin_id"]}</code></p></article>')
 main='<main id="main"><section class="inside-hero"><div class="container inside-hero-inner"><div class="kicker"><span class="kicker-no">QA</span><span class="kicker-en">KINTONE PLUGIN TEST</span><span class="kicker-jp">導入検証版</span></div><h1>8機能の導入検証パッケージ</h1><p>公式cli-kintoneで署名したインストール形式のZIPです。動作保証や本番利用承認を意味しません。</p></div></section><section class="section inner-section"><div class="container"><div class="article-strip"><div><strong>テスト環境専用・本番投入禁止</strong><p>kintone実環境、他プラグインとの競合、ゲストスペース、権限、モバイル、性能、既存版からの更新は未検証です。書き込み機能（自動採番・日付計算・一覧編集など）はデータを変更します。新規の検証用アプリのみで使用してください。</p></div></div><p>各署名鍵は非公開で管理し、GitHubには含めていません。公開したZIPは開発版として固定し、更新には同じ署名鍵を利用します。</p><div class="product-grid">'+''.join(cards)+'</div><p><a href="/downloads/resoarc-signed-qa-manifest.json">各ZIPのSHA-256とIDを検証するJSON</a></p><p><a href="/products/kintone/">kintone一覧へ戻る ↗</a></p></div></section></main>'
 page=ROOT/"site/products/kintone/qa/index.html"
 page.parent.mkdir(parents=True,exist_ok=True)
 page.write_text(first+main+ending,encoding="utf8",newline="\n")
 product=ROOT/"site/products/kintone/index.html"
 ps=product.read_text(encoding="utf8")
 if '/products/kintone/qa/' not in ps:
  insertion='<section class="section inner-section"><div class="container"><h2>8機能の署名付き導入検証版</h2><p>kintoneへインストールできる署名ZIPを、テスト専用として用意しました。実テナントでの受入検証前なので本番環境には導入しないでください。</p><p><a class="inline-link" href="/products/kintone/qa/">検証用署名ZIP一覧を見る ↗</a></p></div></section>'
  ps=ps.replace("</main>",insertion+"</main>",1)
  product.write_text(ps,encoding="utf8",newline="\n")
 sitemap=ROOT/"site/sitemap.xml"
 xml=sitemap.read_text(encoding="utf8")
 if 'https://resoarc.com/products/kintone/qa/' not in xml:
  xml=xml.replace("</urlset>","<url><loc>https://resoarc.com/products/kintone/qa/</loc></url>\n</urlset>")
  sitemap.write_text(xml,encoding="utf8",newline="\n")
 print("SIGNED_QA_PACKED",len(entries),"PRIVATE_KEYS_STAY_LOCAL")
 for e in entries:print(e["slug"],e["version"],e["bytes"],e["sha256"][:12])

if __name__=="__main__":prepare()
