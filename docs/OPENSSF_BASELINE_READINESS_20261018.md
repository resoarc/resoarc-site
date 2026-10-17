# ResoArc / OpenSSF Baseline Level 1 実証資料（2026-10-18）

公式基準: https://baseline.openssf.org/versions/2026-08-28
登録案件: https://www.bestpractices.dev/en/projects/15597
公開ステータス: `in_progress`、Baseline Level 1 **17%**（2026-10-18確認）。取得済みの認定ではない。

## 証拠と未達の切り分け

「要申請」はBadgeApp管理者のログイン・確認が必要な項目、「未確認」は実態確認前にMetと答えてはいけない項目。「公開停止」はGitHub制限によって現時点では達成できない項目。

| レベル1項目 | 状態 | 既存証拠 / 次の作業 |
|---|---|---|
| OSPS-AC-01.01 MFA | 未確認 | 復旧後のGitHubアカウント・リポジトリ権限確認が必要 |
| OSPS-AC-02.01 最小権限 | 未確認 | Collaborators権限と招待時の動作を確認 |
| OSPS-AC-03.01 main直push禁止 | 未確認 | Branch protection / ruleset の有効性を確認 |
| OSPS-AC-03.02 main削除確認 | 未確認 | Gitホスト側の設定・挙動を確認 |
| OSPS-BR-01.01 CI入力検証 | 点検中 | `.github/workflows`に第三者入力を使用する部分がないか監査 |
| OSPS-BR-01.03 CI特権分離 | 点検中 | `permissions: contents: read` の既存ワークフローあり。他の全ワークフローにも同等の確認が必要 |
| OSPS-BR-03.01 公式URI HTTPS | 実証資料あり | `https://resoarc.com/` と公式の各ページがTLS配信 |
| OSPS-BR-03.02 配布経路の暗号化 | 実証資料あり | `https://resoarc.com/source/` と公開ZIPがHTTPSで取得できる |
| OSPS-BR-07.01 秘密情報の混入防止 | 未確認 | secret scanningの導入・全履歴点検を要する |
| OSPS-DO-01.01 基本ユーザーガイド | 実証資料あり | `https://resoarc.com/guide/`, `/products/` |
| OSPS-DO-02.01 不具合報告ガイド | 点検中 | GitHub Issues停止中の代替窓口の確実な受信と案内 |
| OSPS-GV-02.01 公開議論機構 | **公開停止の影響** | GitHub Discussions/Issuesが404。代替の公開議論チャネルが必要 |
| OSPS-GV-03.01 貢献方針 | 実証資料あり | `CONTRIBUTING.md`（公開配布のソースZIPに含まれる） |
| OSPS-LE-02.01 ソースOSSライセンス | 実証資料あり | `LICENSE` MIT と `THIRD_PARTY_NOTICES.md` |
| OSPS-LE-02.02 配布資産のOSSライセンス | 個別監査 | 独自成果物と第三者素材、ResoArcOSの各配布物を区別 |
| OSPS-LE-03.01 ソース内ライセンス | 実証資料あり | ルート `LICENSE`, `site/licenses/` |
| OSPS-LE-03.02 配布物のライセンス | 個別監査 | 配布ZIP・OSイメージ単位で同梱の確認 |
| OSPS-QA-01.01 公開ソースGit URL | **未達** | `https://github.com/resoarc/resoarc-site` が外部から404 |
| OSPS-QA-01.02 公開Git変更履歴 | **未達** | ZIPのみではGitの時系列履歴・コミット作者を確認できない |
| OSPS-QA-02.01 直接依存一覧 | 点検中 | ツール・プラグイン単位の package / requirements の監査 |
| OSPS-QA-04.01 複数リポジトリ一覧 | 点検中 | 管理対象の公式リポジトリを公開リスト化する |
| OSPS-QA-05.01 生成実行物をVCSに置かない | 点検中 | ソース配布ZIPのGit追跡と配布アセット扱いを再検討 |
| OSPS-QA-05.02 不透明バイナリの回避 | 点検中 | フォント・画像など合理的な第三者素材例外の説明 |
| OSPS-VM-02.01 セキュリティ連絡先 | 実証資料あり | `SECURITY.md`, `/.well-known/security.txt`。メール受信確認は別途必要 |

## 次の行動（優先度順）
1. GitHub復旧を待たず、公式Git履歴を保った公開ミラー（例：Codeberg）を確保し、サイトの primary repo 明記と関係を整理する。ただし未公開の運営者情報・秘密情報を公開しない。
2. 独立ミラーの公開後、Issue／変更議論窓口を用意して QA01.01, QA01.02, GV02.01 を再検証する。
3. 分岐保護・MFA・権限・CI権限を監査し、スクリーンショットではなく設定根拠または公開ワークフローの内容を証拠化する。
4. 配布物ごとのライセンス・依存一覧・SBOMを整備する。全ファイルを網羅しない自己適合宣言はしない。
5. BadgeAppの認可済みアカウントで、各設問へ「Met / Unmet / N/A」と具体的根拠を入力して保存する。現在17%であり、Passing / Baselineの取得済み表現は禁止。

「実証資料あり」は基準全体への適合を保証せず、実装証拠を列挙しただけです。
