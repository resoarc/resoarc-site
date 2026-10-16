#!/usr/bin/env python3
"""Only enable the ISO download link after a verified GitHub prerelease exists.

Never use this for production-ready claims: the ISO is an experimental Live image.
After --apply, use scripts/deploy_canonical.ps1 and rerun the live-browser QA.
"""
import argparse
import hashlib
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "os" / "index.html"
TAG = "resoarcos-pc-v0.1.0-dev-20261016"
ASSET = "resoarcos-pc-v0.1.0-dev-amd64.iso"
REPO = "resoarc/resoarc-site"
EXPECTED_SOURCE = "72b427a8ef08ab388dc70ad2f1b14bcb2a7517b8f5edd0ebe67c8d934a93bb20"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ResoArcOS-release-verifier", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Update local HTML only; deployment is separate")
    args = parser.parse_args()
    release = json.loads(get(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}"))
    assert release["tag_name"] == TAG and release["prerelease"] is True and not release["draft"]
    assets = {x["name"]: x for x in release["assets"]}
    assert ASSET in assets and "SHA256SUMS" in assets and "source.zip" in assets
    iso = assets[ASSET]
    assert iso["size"] > 500_000_000, "Unexpectedly small ISO"
    sums = get(assets["SHA256SUMS"]["browser_download_url"]).decode("utf-8")
    matching = [line for line in sums.splitlines() if line.strip().endswith(ASSET)]
    assert len(matching) == 1, "Missing/ambiguous ISO SHA-256"
    sha = matching[0].split()[0].lower()
    assert re.fullmatch(r"[0-9a-f]{64}", sha)
    if iso.get("digest"):
        assert iso["digest"] == "sha256:" + sha, "Uploaded ISO digest disagrees with SHA256SUMS"
    src = ROOT / "site" / "downloads" / "resoarcos-pc-v0.1.0-dev-source.zip"
    assert hashlib.sha256(src.read_bytes()).hexdigest() == EXPECTED_SOURCE
    assert assets["source.zip"]["size"] == src.stat().st_size
    url = iso["browser_download_url"]
    assert url.startswith(f"https://github.com/{REPO}/releases/download/{TAG}/")
    print(json.dumps({"status":"verified-prerelease","iso_bytes":iso["size"],"sha256":sha,"url":url}, ensure_ascii=False))
    if not args.apply:
        print("DRY RUN: HTML unchanged. Use --apply after reviewing verification.")
        return
    page = PAGE.read_text(encoding="utf-8")
    old = "現在公開できるのはソースコードと検証記録です。ISOイメージは生成・検証済みですが、ファイル配布先の整備が必要なため、このサイトからのISOダウンロードはまだ提供していません。"
    new = "開発プレビューのLive ISOとソースコードを公開しています。ISOは仮想環境で検証した実験版です。インストーラーや本番運用の安全性は未検証のため、実機への導入は推奨しません。"
    assert page.count(old) == 1, "Unexpected page content: refusing edit"
    page = page.replace(old,new)
    oldtags = '<span>配布準備中</span><span>本番非推奨</span>'
    assert page.count(oldtags) == 1
    page = page.replace(oldtags, '<span>ISO公開中</span><span>本番非推奨</span>')
    oldcta = '<a class="product-cta" href="#verification">検証状況を見る <span aria-hidden="true">↓</span></a>'
    assert page.count(oldcta) == 1
    page = page.replace(oldcta, f'<a class="product-cta" href="{url}" rel="noopener noreferrer">開発版ISOをダウンロード <span aria-hidden="true">↗</span></a>')
    oldsum = re.search(r"ローカル検証でのISO SHA-256：<code>([0-9a-f]{64})</code>", page)
    assert oldsum, "Cannot find ISO checksum in page"
    page = page.replace(oldsum.group(0), f"公開ISO SHA-256：<code>{sha}</code>")
    assert page.count(url) == 1
    PAGE.write_text(page,encoding="utf-8")
    print("CANONICAL_SITE_UPDATED: run update_manifest.py, verify_site.py, commit via ResoArc GitHub, then deploy_canonical.ps1")

if __name__ == "__main__":
    main()