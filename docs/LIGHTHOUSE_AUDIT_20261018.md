# ResoArc Lighthouse自己診断の記録（2026-10-18 JST）

これはChrome上で実行した **Lighthouse CLI 12.8.2 の自己診断**。Googleによる外部認証、PageSpeed Insights公式公開結果、製品品質保証ではない。

## 同じ本番URLでの測定

| 状態 | Performance | Accessibility | Best Practices | SEO | LCP | CLS |
|---|---:|---:|---:|---:|---:|---:|
| 変更前 | 67 | 95 | 89 | 100 | 6.1秒 | 0.13 |
| 変更後1回目 | 76 | 95 | 89 | 100 | 4.2秒 | 0 |
| 変更後2回目 | 77 | 95 | 89 | 100 | 4.1秒 | 0 |

テスト環境の preview URL では Performance 90 / LCP 1.7秒となったが、ホスト名が違い、SEO 69となっていた。この値を本番実績として宣言しないこと。測定には変動がある。

## 実装
- `site/index.html` のTOP写真に `srcset` / `sizes` を設定。元写真は維持。
- `hero-architecture-800.webp` 62,184 bytes、`hero-architecture-1600.webp` 175,310 bytes。
- 従来の `hero-architecture.jpg` 456,049 bytesから、モバイル向け画像転送量を86%削減。
- 既存カード6件、PC/タブレット/モバイルの表示をプレビューで確認。
- Lighthouseで検出された `static.cloudflareinsights.com` のビーコンに関するCSP違反は、外部追跡JavaScriptを通さない既存方針の副作用。点数目的でCSPを緩める変更は行わない。
- 色のコントラストとアクセシブルラベルは別途改善の余地あり。

## 再実行方法
PowerShellで `CHROME_PATH` をChromeのexeに設定して実行:

```powershell
$env:CHROME_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
npx --yes lighthouse@12.8.2 https://resoarc.com/ --chrome-flags="--headless --no-sandbox" --output=json --output-path="lighthouse-resoarc.json" --only-categories=performance,accessibility,best-practices,seo --quiet
```

元のJSON監査結果はユーザーPCの `Documents\ResoArc\audits\20261018` に保存する（Gitの配布物には含めない）。

## その他
- W3C Nu HTML Checkerでは、公開後のTOPと実績詳細ページは両方ともエラー0。
- Internet.nlは公式テスト73%（2026-10-17）、100%バッジ未取得。HSTSは段階的に7日へ延長。
- GitHubが外部から404である間、OpenSSF Baselineは未取得のまま。実証準備の詳細は `OPENSSF_BASELINE_READINESS_20261018.md` を参照。
