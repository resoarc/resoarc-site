# TrapNet 二段階リリースゲート（自動検証）

基準日：2026-11-04。判定：**HOLD**。

## 実測された進捗

| 判定軸 | PASS | PARTIAL | TODO |
|---|---:|---:|---:|
| ゲート固有の技術受入 | 3 | 15 | 2 |
| 従来の正式リリースゲート | 1 | 17 | 2 |

**重要：技術PASSは正式リリース承認ではありません。** 自動化は第三者の実在や署名の真偽まで認証しません。

## 技術受入PASSの範囲
- **A1 実CowrieのENOSPC再現**：v0.27 実Cowrie ENOSPC実測。技術範囲：lab。正式：PASS。
- **A2 ログ欠落・部分破損・重複**：PR #46 45/45; #54 同一隔離CI通過。技術範囲：lab。正式：PARTIAL。
- **B2 コンテナ権限・資源上限**：PR #56: real-Cowrie containment, actual in-container root write denial, private ext4 size and independent inode exhaustion/recovery 27/27 checks (production proof excluded)。技術範囲：isolated real Cowrie nonroot/read-only rootfs/cap-drop/resource ceilings; 16MiB persistent ext4 + separate low-inode ENOSPC/recovery only, NOT production storage。正式：PARTIAL。

## 当面の優先3件
- **1. A2 ログ欠落・部分破損・重複**：技術的な未実施なし。独立確認待ち。実施経路：external。関連ゲート：D3, E3。
- **2. E1 個人情報・ログ保持削除**：本番生ログの保持・アクセス・削除のE2E、プライバシー影響評価とレビュー。実施経路：internal。関連ゲート：E3。
- **3. B3 大量イベント・異常入力**：連続高負荷中のCPU/キュー飽和、イベント欠測HOLDと正常復帰。実施経路：internal。関連ゲート：E3。

## 判定の責任境界
- **A2**：現存する実Cowrieログの欠落・途中破損・完全重複・意味的重複と、署名付き欠測通知のHUB記録までは技術的に完了。過去の観測行が自然に削除された場合の検知は含めない。
- **D3**：独立保管された履歴の完全性、別管理主体のWitness鍵、実停電・断線からの復旧は未達。
- **E3**：実在する第三者の監査と重大指摘の解消は未達。自動CI成功で代用しない。
- **D4**：複数独立運用者の参加・撤退・失効訓練は未達。
- **公開判定**：D3・D4・E3を含むすべての個別正式受入が揃うまでHOLD。

## 全ゲートの進捗

| ID | ゲート | 技術 | 正式 | 次の決定を妨げる項目 |
|---|---|---|---|---|
| A1 | 実CowrieのENOSPC再現 | PASS | PASS | なし |
| A2 | ログ欠落・部分破損・重複 | PASS | PARTIAL | 依存：D3、E3 |
| A3 | ログ転送停止・復帰 | PARTIAL | PARTIAL | 10分超の未受領期間の照合、多件の永続キュー |
| A4 | 強制終了・停電・バックアップ復元 | PARTIAL | PARTIAL | 本番相当の突然の電源断、別筐体バックアップからの完全復元 |
| B1 | 保護LAN到達不能 | PARTIAL | PARTIAL | 実ルータ・VLANを使ったPC/NAS/管理LAN到達不能確認 |
| B2 | コンテナ権限・資源上限 | PASS | PARTIAL | 稼働中のVPSを含む実配備で専用容量・inode quotaを保護できる構成の採用と検証、本番ログの保管期限/削除・ローテーション、バックアップ保護と本番相当のリストア、独立した承認者による変更計画とロールバック手順の受入 |
| B3 | 大量イベント・異常入力 | PARTIAL | PARTIAL | 連続高負荷中のCPU/キュー飽和、イベント欠測HOLDと正常復帰 |
| B4 | 実行コードと公開ソース一致 | PARTIAL | PARTIAL | 全Docker/依存/配布バイナリの再現ビルド、独立再現ハッシュ |
| C1 | 署名済みGuardian配布/来歴 | PARTIAL | PARTIAL | 別管理Rootによる本物の配布署名、ソース/署名/配布物の来歴証明 |
| C2 | OS別インストール・アンインストール | PARTIAL | PARTIAL | 実Raspberry Piで電源断・破損状態から完全削除/再導入 |
| C3 | Root鍵更新・失効・状態消失 | PARTIAL | PARTIAL | 独立鍵保管と実配布経路での失効・状態消失復旧 |
| C4 | Guardian非侵襲性 | PARTIAL | PARTIAL | Windows ETW/ファイアウォール通信監査、Pi実機・全分岐・配布版の非侵襲性 |
| D1 | 偽Sensor・リプレイ・Sybil耐性 | PARTIAL | PARTIAL | 異なる運用者による虚偽報告・複数HUB対抗試験 |
| D2 | 悪意あるHUB・フィード改ざん | PARTIAL | PARTIAL | 実ネットワーク内の悪意HUBからの偽フィード拒否、独立Root/Witness証拠 |
| D3 | Witness外部保管と履歴改ざん | PARTIAL | PARTIAL | 別管理主体のWitness秘密鍵・履歴保管、不変オフサイトtipと実停電/断線復旧、鍵失効・独立承認 |
| D4 | 複数独立運用者 | TODO | TODO | 別の運用者2組織による登録・所有確認・失効・退出 |
| E1 | 個人情報・ログ保持削除 | PARTIAL | PARTIAL | 本番生ログの保持・アクセス・削除のE2E、プライバシー影響評価とレビュー |
| E2 | AIプロンプト注入耐性 | PARTIAL | PARTIAL | 正式Root署名ポリシーでの受入、実LLM→Sonar→HUB→Guardian全経路と独立監査 |
| E3 | 独立外部レビュー | TODO | TODO | 実在の独立レビュアーによるCritical/High監査と解消確認 |
| E4 | 緊急停止・更新・巻き戻し | PARTIAL | PARTIAL | 全サービス系統での停止・キー失効、本番相当の更新巻き戻し・複数人訓練 |
