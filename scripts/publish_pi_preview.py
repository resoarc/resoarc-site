#!/usr/bin/env python3
"""Publish a source-only Raspberry Pi first-boot developer snapshot.

No IMG or signed installation artifact is created. Do not publish dirty/untracked files.
"""
from __future__ import annotations
import hashlib
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OS=Path.home()/"Documents"/"GitHub"/"resoarc-os"
ZIP_NAME="resoarcos-pi-firstboot-v0.2.1-alpha-source.zip"
ZIP=ROOT/"site"/"downloads"/ZIP_NAME
SHA=ROOT/"site"/"downloads"/(ZIP_NAME+".sha256")
TARGET=ROOT/"site"/"os"/"pi"/"index.html"

def git(*args):
    return subprocess.check_output(["git","-C",str(OS),*args],text=True,encoding="utf-8").strip()

def publish():
    revision=git("rev-parse","--short=8","HEAD")
    if not git("status","--porcelain","--untracked-files=no").strip() in ("","M docs/STATUS.md"):
        # local docs/STATUS.md is a separate in-progress operation; git archive HEAD never includes its changes.
        raise ValueError("OS repository has unexpected pending tracked modifications")
    tracked=set(git("ls-files").splitlines())
    required={"LICENSE","README.md","src/resoarcos/firstboot.py","images/pi/build.sh","images/pi/getty-firstboot.sh","images/pi/resoarc-firstboot.yaml","tests/test_firstboot.py"}
    assert required <= tracked, required-tracked
    ZIP.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(["git","-C",str(OS),"archive","--format=zip","--output="+str(ZIP),"HEAD"],check=True)
    with zipfile.ZipFile(ZIP) as z:
        files={x.filename for x in z.infolist() if not x.is_dir()}
        assert files==tracked,(files-tracked,tracked-files)
        assert len(files)<=500 and all(not name.startswith("/") and ".." not in Path(name).parts for name in files)
        assert b"def validate_public_key" in z.read("src/resoarcos/firstboot.py")
        assert b"test_console_reprompts_invalid_wifi_key_and_mode_without_writes" in z.read("tests/test_firstboot.py")
    digest=hashlib.sha256(ZIP.read_bytes()).hexdigest()
    SHA.write_text(digest+"  "+ZIP_NAME+"\n",encoding="ascii",newline="\n")
    original=(ROOT/"site"/"os"/"index.html").read_text(encoding="utf-8")
    start='<main id="main" class="os-page">'
    header, remaining=original.split(start,1)
    _,footer=remaining.split('</main>',1)
    header=header.replace("ResoArcOS PC 開発プレビュー | ResoArc","ResoArcOS Raspberry Pi 開発プレビュー | ResoArc")
    body=f'''<main id="main" class="os-page">
<section class="inside-hero"><div class="container inside-hero-inner"><div class="kicker"><span class="kicker-no">OS</span><span class="kicker-en">RESOARC OS</span><span class="kicker-jp">RASPBERRY PI</span></div><h1>SDカードから始まる、<br>自分専用のLinux。</h1><p>ResoArcOS Raspberry Pi版は、普段はCLI、必要時だけ軽量GUIを使う実験的OSです。初回起動ではローカルコンソールのセットアップ画面から、端末名・管理者パスワード・Wi-Fi・SSHの設定を行います。</p></div><span class="inside-watermark" aria-hidden="true">ResoArcOS.</span></section>
<section class="section inner-section"><div class="container"><div class="kicker"><span class="kicker-no">01</span><span class="kicker-en">DEVELOPER SNAPSHOT</span><span class="kicker-jp">公開状態</span></div><h2>Pi 4 / Pi 5 初回設定ソース：α版</h2><p class="catalog-lede">この配布物はソースコードとビルド・検証スクリプトです。完成したSDカード用IMGではありません。実機Raspberry Piでの起動、初回設定、ストレージ拡張はまだ最終検証を終えていません。</p>
<div class="article-strip"><div><strong>実機インストール向けの安定版ではありません</strong><p>初期設定はHDMIモニターとキーボードを使用する設計です。パスワードを固定して配布しません。重要なデータを保存したSDカードや運用中の機器では試さず、検証用の予備メディアを使用してください。</p></div><a class="inline-link" href="/principles/">品質方針を見る <span aria-hidden="true">↗</span></a></div>
<div class="product-grid"><article class="product-card"><div class="product-meta"><span>Raspberry Pi 4 / 5</span><span>v0.2.1 α source</span></div><h3>初回設定・ビルドソース</h3><p>Pythonの初回設定画面、SSH鍵の形式検査、入力エラー再試行、CLI主体の動作、Web管理UI、Piイメージ構築・検証スクリプトを含みます。</p><div class="product-tags"><span>ソース公開</span><span>MIT</span><span>実機未検証</span></div><a class="product-cta" href="/downloads/{ZIP_NAME}">ソースZIPを取得 <span aria-hidden="true">↘</span></a></article>
<article class="product-card"><div class="product-meta"><span>SD / IMG</span><span>動作検証中</span></div><h3>SDカード用イメージ</h3><p>Pi 5用の候補IMGはローカルで生成し、ファイル構造と署名・ハッシュを検査しています。今回のSSH鍵検査の改善は新しいIMGにはまだ反映されていません。実機起動を確認するまで、このページでは更新版IMGを配布しません。</p><div class="product-tags"><span>IMG未配布</span><span>実機試験待ち</span></div><a class="product-cta" href="#validation">検証状況を見る <span aria-hidden="true">↓</span></a></article></div>
</div></section>
<section class="section inner-section muted-band" id="validation"><div class="container"><div class="kicker"><span class="kicker-no">02</span><span class="kicker-en">VALIDATION</span><span class="kicker-jp">検証内容</span></div><h2>できたことと、これから確認すること</h2><div class="product-grid"><article class="product-card"><h3>ローカル検証済み</h3><p>初回設定画面の入力再試行、公開鍵のバイナリ構造検査、無効な値の拒否、機密情報が画面へ出ないことを含む全36件のPythonテストを実施。3件はOS・依存ライブラリ条件によりスキップしました。</p></article><article class="product-card"><h3>残る実機検証</h3><p>実物のPi 4 / Pi 5での起動、USBキーボード操作、無線LANへの接続、SSH鍵ログイン、拡張したSD領域の確認、電源断からの復帰。</p></article></div><p>検証対象ソースコミット：<code>{revision}</code></p><p>ソースZIP SHA-256：<code>{digest}</code></p><p><a class="inline-link" href="/downloads/{ZIP_NAME}.sha256">チェックサムファイル <span aria-hidden="true">↘</span></a></p><p><a class="inline-link" href="/os/">PC向けResoArcOSページへ戻る <span aria-hidden="true">↗</span></a></p></div></section>
</main>'''
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    TARGET.write_text(header+body+footer,encoding="utf-8",newline="\n")
    pi_link='<section class="section inner-section"><div class="container"><div class="kicker"><span class="kicker-no">PI</span><span class="kicker-en">RASPBERRY PI</span><span class="kicker-jp">SDカード版</span></div><h2>Raspberry Pi向け初回設定も開発中</h2><p>Pi 4 / 5向けに、SDカードから起動後、ローカルコンソールで初回セットアップを行う版を開発しています。SSH公開鍵検査と入力ミスの再試行を強化したソースα版を公開しました。実機未検証のため更新IMGは未配布です。</p><a class="inline-link" href="/os/pi/">Raspberry Pi版の開発状況を見る <span aria-hidden="true">↗</span></a></div></section>\n'
    marker='<section id="verification"'
    if '/os/pi/' not in original:
        original=original.replace(marker,pi_link+marker,1)
        (ROOT/"site"/"os"/"index.html").write_text(original,encoding="utf-8",newline="\n")
    sitemap=ROOT/"site"/"sitemap.xml"
    xml=sitemap.read_text(encoding="utf-8")
    if 'https://resoarc.com/os/pi/' not in xml:
        xml=xml.replace('</urlset>','<url><loc>https://resoarc.com/os/pi/</loc></url>\n</urlset>',1)
        sitemap.write_text(xml,encoding="utf-8",newline="\n")
    print("ZIP",str(ZIP),"SHA256",digest,"FILES",len(files),"REVISION",revision)

if __name__=="__main__":
    publish()
