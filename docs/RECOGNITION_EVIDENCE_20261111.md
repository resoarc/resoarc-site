# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT

# ResoArc 外部確認可能な技術実績と次の自己診断（2026-11-11 JST）

本記録は、公開された外部検証結果を正確に区別するためのスナップショットです。自己申告、機械判定、独立した第三者監査を混同しません。2026年10月時点の記録は履歴として残します。

## 2026-11-11に確認できた実績

| 項目 | 結果 | 公式の証跡 | 意味と限界 |
| --- | --- | --- | --- |
| OpenSSF Best Practices Baseline | **Level 1 取得**。発行元JSONでは達成日時 2026-11-06T15:59:05.301Z（日本時間11月7日） | [#15597](https://www.bestpractices.dev/projects/15597/baseline-1) / [JSON](https://www.bestpractices.dev/projects/15597.json) | プロジェクトによる自己評価。Metal Passingは `in_progress`、第三者監査ではない |
| FSFE REUSE Specification 3.3 | **compliant**。2026-11-11 06:01:28 UTC の対象コミット `052dc416979db92938da7ed8f7615fb74ab2f830`、著作権・ライセンス情報 844/844 ファイル、欠落0 | [FSFE REUSE API](https://api.reuse.software/info/github.com/resoarc/resoarc-site) / [GitHub CI](https://github.com/resoarc/resoarc-site/actions/runs/42939422831) | ライセンス表記の仕様準拠。製品安全性の認証ではない |
| Green Web Foundation | **green: true**、登録ホスト Cloudflare（2026-11-11照会） | [公式API](https://app.greenweb.org/api/v3/greencheck/resoarc.com) | 事業者の環境データに基づく。サイト固有の排出量ゼロという意味ではない |
| CodeQL | GitHub Actionsの2026-11-11の解析実行が **success** | [Actions run](https://github.com/resoarc/resoarc-site/actions/runs/42939422794) | 対象ワークフローの成功。すべての脆弱性がないことの証明ではない |
| Software Heritage | 2026-10-17 の保存成功記録あり | [既存保存記録](https://archive.softwareheritage.org/api/1/origin/save/2560719/) | 当時のソース保存を示す。最新コミットの保存完了は別途確認が必要 |

## 2026-11-11 追加で確認した進捗（申請・外部検査）

- **OSS Compass 正式申請:** 専用 `@resoarc` アカウントから [登録PR #11638](https://github.com/oss-compass/compass-projects-information/pull/11638) を 2026-11-11 23:36 JST に提出。公式Botは形式検証 `status: true` / `message: ok` を返した。現時点は **PR OPEN / 未マージ / 分析結果未発行**であり、取得済み評価や認証ではない。
- **W3C HTML Checker:** 本番5ページについて外部 Nu Validator のHTML文法エラー0件。対象URL・その他メッセージ数・判定不能のHTTP 429は [実測記録](W3C_HTML_VALIDATION_20261111.md) を参照。アクセシビリティ全面適合ではない。
- **RFC 9116 `security.txt`:** 公開 `/.well-known/security.txt` に対し外部検証 `valid: true` / 警告・エラー0件。証跡は [検証記録](SECURITY_TXT_VALIDATION_20261111.md)。窓口メールの配送試験や安全認証ではない。
- **OpenChain証跡:** 2つのWebツールでソースと本番7ファイルのSHA-256比較を実施し5件一致、2件のHTML不一致。 [詳細記録](compliance/OPENCHAIN_LIVE_SOURCE_VERIFICATION_20261111.md)。適合宣言は保留。
- **CI改善:** [PR #109](https://github.com/resoarc/resoarc-site/pull/109) を全チェック合格後に統合。Chrome/Chromiumの実起動を必須とし、不要なAPT依存インストールを回避する。テスト省略なし。
- 検証証跡の整理は [PR #108](https://github.com/resoarc/resoarc-site/pull/108) にて統合済み。

## 次の実績獲得候補

1. **OpenSSF Metal Passing（無料・自己評価）:** プロジェクト #15597 をそのまま使い、MUST / SHOULD / SUGGESTED の各設問について証跡を照合してから入力する。別バッジの達成を先取りしない。
2. **OpenChain ISO/IEC 5230:2020（無料の自己適合確認）:** 全項目について実際のライセンス管理プロセス、担当者、教育、台帳、是正の証拠を確認した後にのみ自己適合宣言する。REUSE準拠だけでOpenChain適合とはならない。
3. **OpenChain ISO/IEC 18974（無料の自己適合確認）:** 製品セキュリティ保証の実運用手順と記録が揃った場合に検討。第三者認証とは区別する。
4. **OSS Compass（外部のOSSコミュニティ健全性評価）:** 登録申請は[公式PR #11638](https://github.com/oss-compass/compass-projects-information/pull/11638)として提出済み。マージ・索引作成・実際の外部分析ページの発行を確認してから掲載する。[公式登録手順](https://oss-compass.org/docs/quick-start/)
5. **アクセシビリティ評価:** W3C文書検証、Lighthouse / axe等の自動検査に加え、キーボード操作、フォーカス、読み上げの手動検査結果を残す。自動検査合格のみで WCAG AA に適合したと宣言しない。
6. **Software Heritageの継続保存:** 新しい公開コミットの再保存を申請し、受付IDだけでなく完了ステータスとSWHIDを確認する。

## リリース上の注意

- GitHub の `main` は公開ミラーであり、公開正本Codebergと Cloudflare Pages Direct Upload の差異照合が別途必要。GitHubのPR作成やマージだけでは本番サイトの更新完了を意味しない。
- `site/recognition/index.html` の2026-10-17時点の旧「Baseline 17%、未取得」は、2026-11-11の公式発行情報と矛盾する。更新後も本番ページと再照合する。
- コミュニティ購読・自己評価・外部自動検査を「公式パートナー認定」「独立監査済み」「製品安全保証」と表現しない。
