# 2026-10-18 ResoArc Web 品質改善（再計測）

## 公開済みの改善

対象: https://resoarc.com/ （本番） / Lighthouse CLI 12.8.2、Headless Chrome、モバイル相当のシミュレーション

| 指標 | 本番・改善前 | 本番・改善後 |
| --- | ---: | ---: |
| Performance | 77 | **82** |
| Accessibility | 95 | **100** |
| Best Practices | 89 | **93** |
| SEO | 100 | **100** |
| Largest Contentful Paint (LCP) | 4.1秒 | **2.1秒** |

改善後の測定日時は、個々の Lighthouse JSON の `fetchTime` を正とする。単発測定であり、訪問者実測値・保証値・外部認証ではない。

### 実施
- 39ページのヘッダーロゴを視認できる名称を含むアクセシブル名へ統一。
- TOPと実績カードで補足文字のコントラストと文字サイズを改善。
- TOP・実績・信頼性ページの既存機能・リンクを維持。
- 公式検証バッジの認定条件は変更なし。証明できない認定バッジは追加していない。
- CloudflareのCSPは `script-src 'self'` の厳格な設定を維持。外部Analyticsを許可するためだけに緩めない。

### 見送った案（再採用しないこと）
- TOP用フォントサブセット: 403,704→189,936 bytes、しかしプレビューでPerformance 95→83、CLS 0→0.262。元のサイト用フォントを維持。
- フォントの優先プリロード: プレビューでPerformance 95→71、LCP 1.6→3.6秒、CLS 0.262。元に戻した。

### 残る制約
- 本番LighthouseのBest Practices 93の主な減点: Cloudflareが自動挿入するビーコンが既存の厳格CSPに拒否される（browser consoleとInspector）。設定を緩めるよりCloudflareダッシュボード側でサイトのRUM自動挿入を停止する選択肢がある。APIを読み取り確認したところPagesプロジェクトの `build_config.web_analytics_tag` と `web_analytics_token` は nullで、Cloudflare RUM Sites APIは403。現権限で管理設定を変更できていないので未対応。
- Performanceは測定環境により変動。上記82は本番測定値。プレビュー95は別ホスト名の測定なので、公式本番実績として表示しない。
- DNSSECはドメインのCloudflareゾーン管理権限が必要。Internet.nlの73%評価とOpenSSF Baseline 17%の現状も区別すること。GitHubリポジトリ公開停止のため、OpenSSFのバッジは未取得のまま。

### 検証元データ
個人PC: `Documents/ResoArc/audits/20261018/`
- `lighthouse-home-after2-20261018.json` (改善前)
- `lighthouse-readability-production.json` (改善後)
- `lighthouse-readability-preview.json` (プレビュー)
- `lighthouse-font-preview.json`, `lighthouse-font-preload-preview.json` (見送った試験)

公開スコアは毎回の計測値が変わるため、単発のスコアを永続的な検証済み認定として扱わない。
