# TrapNet v0.58: 二段階ゲートの運用契約

## なぜ数字が減らなかったのか

A2の「壊れた実Cowrieログを識別し署名付き欠測へ変換する」機能試験は
45/45通過していた。しかし、それと異なるD3「外部Witnessによる
過去の履歴保証」、E3「第三者独立監査」をA2の機能未了として
重複計上し、PARTIALから出られなかった。

この文書は**安全要件を削除しない**。技術的な完了と
外部承認を2つの列へ分離し、承認の根拠も明示する。

## 対象の厳密な意味

- `technical_status=PASS`：
  **試験によって実際に裏付けられた個別機能の限定範囲**だけの合格。
  A2は、現存する実Cowrieのログファイル欠落・途中破損・完全重複・
  内容が同じJSON重複からの署名付き欠測通知とHUB記録に限る。
  有効な行の過去削除、長期履歴の完全性、独立のオペレータは含めない。
- `release_status=PASS`：
  元のリリース受入台帳で定められた範囲・承認を含む合格。
  **技術PASSを理由に自動変更しない。** 当面のA1は旧台帳の
  `PASS（隔離）`判定を保持するが、それは一般配布承認ではない。
- `release_authorization=HOLD`：
  D3、D4、E3および他の個別ゲートが未完了なら維持する。
  トップレベルの許可は個別技術状態から自動推論しない。

## v0.58で実際に変わったこと

| 項目 | 従来 | 今回 |
|---|---|---|
| A2 機能上の技術受入 | PARTIALと一括管理 | PASS（実Cowrie 45/45・範囲限定） |
| A2 正式リリースゲート | PARTIAL | PARTIAL（独立承認未達） |
| B2 の隔離実Cowrie境界 | PARTIAL | 技術PASS（27/27、実配備は未証明） |
| 個別技術 PASS / PARTIAL / TODO | 区別なし | **3 / 15 / 2** |
| 正式 PASS / PARTIAL / TODO | 1 / 17 / 2 | **1 / 17 / 2** |
| 一般公開 | HOLD | **HOLD** |

この変更は「17件を偽装して減らす」ものではなく、
**技術検証の完了を公式なリリース承認と混同せず可視化するもの**。

**依存関係の二重計上を解消**：A2に必要な範囲限定の独立レビューが
実際に届けば、D3の長期履歴保管やE3のシステム全体監査が
まだ完了していなくても、**A2だけの正式ゲートをPASSにできる**。
ただし、そのときも全体の一般公開はD3・D4・E3などが未達なら
必ずHOLDとする。これはゲート固有の判定とシステム全体の
配布許可を分離するもので、安全要件の削除ではない。

## 次に正式PARTIALを減らす順序

1. **A2：独立確認の範囲を明確化。**
   [レビューIssue #47](https://github.com/resoarc/resoarc-site/issues/47)で、
   元コミット・実Cowrie証跡・改ざん拒否・範囲限定を第三者に確認してもらう。
   過去ログの外部固定までA2機能試験を延々と増やさず、
   その横断要件はD3で完了させる。
2. **B2：隔離Cowrie実験の技術受入が完了。**
   PR #56では読み取り専用rootfs、非root、無権限、CPU/メモリ/PID、
   別ext4のinode ENOSPC・削除後の復帰を実測し27/27成功。
   **実VPSの独立専用ストレージ、ローテーション、承認付き切戻しは未証明**。
   正式B2はPARTIALであり、無承認で本番設定に適用しない。
3. **E1：保持・削除・アクセス制御。**
   個人情報の実保存経路を文書化して隔離環境で削除まで検証し、
   人間のプライバシー受入に渡す。
   
D3／D4／E3の独立した人間・組織が必要な内容は、
AIテストの数を増やしても代替できない。

## 実行と検査

GitHub CIではオフラインで構造・状態不正・証跡のハッシュ形式を検証する：

```sh
python3 -m unittest discover -s experiments/trapnet-zero-trust/release -p 'test_scorecard.py' -v
python3 experiments/trapnet-zero-trust/release/scorecard.py
```

オペレータPC上の非公開A1原本は、指定された証拠ディレクトリだけで
SHA-256を再計算できる（実際のパスを公開リポジトリへ書かない）。

```sh
python3 experiments/trapnet-zero-trust/release/scorecard.py \
  --verify-local --evidence-dir /path/to/private/evidence \
  --output /path/to/private/report.md
```

A2のGitHub artifact `real-cowrie-a2-matrix-evidence.json`
のSHA-256と対象コミットは、JSON registerに固定する。
ただしGitHub Actionsワークフローは**証跡を再ダウンロードして
自動承認するものではない**。第三者の実在／署名の真偽も認証しない。

## 運用ルール

- 毎回、`technical_status`と`release_status`両方の件数を報告。
- PARTIALで新しい試験を行う前に、具体的に何が足りず、
  その試験でどちらの状態を更新できるか明記する。
- 結果が既に揃っている項目は、同じCIを目的なく再実行しない。
- 外部レビュアー、実ネットワークや本番変更が必要なら
  その依存条件と担当を明示し、代替不可能な事実は保持。
- `review_approval`へ文章だけを書いても独立承認とはならない。
  署名決裁原本、本人の管理権限、対象SHAを別途実確認する。
