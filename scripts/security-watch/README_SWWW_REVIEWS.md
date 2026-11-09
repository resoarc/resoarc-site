# SWWW: ResoArc影響評価・対応状況（非公開台帳）

SWWWは一般的な脆弱性速報と、ResoArc固有の資産影響評価を明確に分けます。

## 公開側（誰でも閲覧可能）
- `/security/weather/` の「ResoArcへの影響・対応状況」は、公表承認された件数だけを表示
- 既定は `影響未判定` / `未審査`。重大度が高くても自動で「影響あり」としない
- `影響あり` / `影響なし` / `対応済み` は、根拠記録＋担当者レビュー＋公表承認がある場合のみ
- 「対応難易度」は一般的なCVSSやEPSSと別指標。ベンダーがパッチを配布しているだけでは簡単とは限らない
- 未審査時は `unknown`（要調査）。0件の分類は「軽微」も「難しい」も0ということであり、全件安全ではない

## 非公開側（VPS内、Web配信禁止）
- 入力台帳：`/var/lib/resoarc-security-watch/output/weather-assessments.json`
- 基盤対策の時系列：`/var/lib/resoarc-security-watch/output/security-weather-operations.json`
- 生成された内部レポート：`/var/lib/resoarc-security-watch/output/security-weather-private/index.html`
- 同JSON：`/var/lib/resoarc-security-watch/output/security-weather-private/assessment-register.json`
- レポートのディレクトリ権限 0700、ファイル 0600。**Cloudflare Pagesのsiteディレクトリへコピーしない**
- 初期レポートは未審査件数を正直に表示。作業履歴はCVEの影響確定と混同しない

## 評価ファイルの記録例
実際には対象CVE/GHSAのキーを指定します（`id` 単独でも可）。下記は架空IDです。

```json
{
  "CVE-2099-99999": {
    "resoarc_impact": "NOT_CONFIRMED",
    "response_status": "INVESTIGATING",
    "difficulty": "unknown",
    "affected_asset": "",
    "internal_owner": "担当コード（公開禁止）",
    "investigation_notes": "利用状況・依存バージョンを確認中",
    "remediation": "",
    "evidence_ref": "内部証跡ID",
    "difficulty_evidence": "",
    "verification_ref": "",
    "reviewed_by": "担当者",
    "reviewed_at": "2026-10-22T15:00:00+09:00",
    "public_approved": false
  }
}
```

状態コード:
- 影響: `NOT_CONFIRMED` / `AFFECTED` / `NOT_AFFECTED`
- 対応: `UNREVIEWED` / `INVESTIGATING` / `PLANNED` / `MITIGATING` / `REMEDIATED` / `MONITORING` / `NOT_APPLICABLE` / `BLOCKED`
- 難易度: `unknown` / `easy` / `moderate` / `hard`

公表には `public_approved: true` に加え、`reviewed_by`、`reviewed_at`、`evidence_ref` が必須。
難易度を公表する場合は `difficulty_evidence` も必須。
対応済みを公表する場合は `verification_ref` を必須とし、存在しなければ「調査中」に格下げします。

## 難易度の判断基準（ベンダー情報だけでは判断しない）
- 軽微: 正規パッチあり、使用状況確定、停止不要で自動テストとロールバックが確立
- 中程度: 依存関係や一部設定を変更し、回帰テスト・短時間停止が必要
- 難しい: 大規模更新／設計変更／互換性検証／長時間停止／代替策の整備が必要
- 要調査: 対象構成が不明、根拠不足、対策工数が判定できない

自動判定は最終承認に使わず、まず使用有無と影響範囲を照合してください。
CVE/アドバイザリー単位の判定証跡には修正情報、バージョン、適用試験結果、復旧手順、レビュアーを紐づけます。

## 公開前の安全性チェック
- `python scripts/security-watch/test_swww_private_review.py`
- 厳格CSPの実ブラウザテスト
- 埋め込み公開JSONに内部メモ・社内ホスト・担当者名等が含まれないこと
- 公開承認フリーズは別のルールとして維持。日次自動公開は有効化しない
