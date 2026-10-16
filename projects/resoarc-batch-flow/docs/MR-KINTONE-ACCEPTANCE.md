# ResoArc Clock × Mole Remote kintone test integration

この手順は、ユーザー所有PCの `C:\\Users\\<WindowsUser>\\mole-remote` にあるMR v0.4系「kintone高速テスト」を利用し、ResoArc Batch Flow / Clockのリリース準備を**読み取り専用**で確認します。

## 使用するMR実装

- `integrations/kintone-plugin-preflight.js`: プラグインのソース・署名付きZIPのファイル構成、JS構文、manifestを検査する。RSA署名の暗号学的検証は含まない。
- `integrations/kintone-fast-test.js`: 専用kintoneテストアプリに対するフォーム取得、レコード検索、API応答時間測定。GETだけを使用する。
- `integrations/kintone-browser-smoke.js`: 専用Edgeプロファイルでログイン・画面表示・JavaScript例外・通信エラーを調べる。既存の個人Edgeは使用しない。
- `integrations/kintone-release-gate.js`: 上記の確認を束ねる。**releaseReadyは未達のまま**であり、E2Eの代替ではない。
- `integrations/kintone-auto-number-e2e.js`: 自動採番テストアプリ**ID 48限定**。Batch Centerの書き込みE2Eには使用しない。

## Batch Center専用の読み取り検査

```powershell
cd C:\\Users\\<WindowsUser>\\Documents\\GitHub\\resoarc-batch-flow
npm test
npm run test:mr-readiness
```

`scripts/mr-batch-center-readiness.cjs` はMRが提供する各種テスト機能を呼び出し、ログイン済みEdgeからアクセス可能なアプリを検索します。Batch Centerという名前の管理アプリが見つかった場合のみ、フォーム構造とプラグイン導入有無を確認します。APIトークン、Cookie、シークレット、業務レコードの値は表示・保存しません。

指定した管理アプリIDを確認する場合は `BATCH_CENTER_APP_ID` 環境変数を設定してください。設定しない場合、該当名の管理アプリが1件だけなら自動選択します。名称が一致しないアプリや他のテストアプリは誤って対象にしません。

状態の意味:

| status | 解釈 |
| --- | --- |
| `center_app_not_ready` + `not_provisioned` | Batch Center管理アプリ未作成。**実環境E2E未着手** |
| `center_app_not_ready` + `center_setup_incomplete` | フィールド不足・プラグイン未導入 |
| `staging_ready_for_control_app_e2e` | 管理アプリの読み取り準備は完了。**書き込みの動作確認はこれから** |
| `mr_preflight_failed` | ソース検査、API疎通、ブラウザ確認のいずれかに失敗 |

実行結果のJSONはMRの専用レポート領域 `Documents\\AI-Work\\MR-kintone-tests\\reports` に保存します。デスクトップは使いません。もし別のMRリポジトリに配置している場合は `MOLE_REMOTE_ROOT` を指定してください。

## 実環境E2Eで必要な追加手順

1. 既存業務アプリや自動採番専用のID 48を使用せず、**Batch Center専用の新しいテスト管理アプリ**を準備する。
2. `control-app/fields.json` に従って項目とテーブルを設定する。`control-app/SETUP.md` の生成補助機能は対象と変更内容を確認した場合のみ利用する。
3. Batch Centerプラグインをインストールし、テスト用の取得・更新・転記対象アプリを別途作る。
4. テストモードがレコードを変更しないこと、正常終了時の状態遷移、revision競合、途中失敗後に「要確認」で停止することを確認する。
5. 新規登録・転記後のIDを控え、**今回作成したテストレコードのみ**を削除して復旧を確認する。他の業務データを削除しない。
6. Cloudflare Cronは `RA_CLOCK_ENABLED=false` / `RA_ALLOW_WRITES=false` から開始し、テスト用権限と処理対象を限定したうえで段階的に有効化する。

**今回の読取検査が成功しても本番対応済みとは判断しません**。実テナントでの更新・転記・削除を伴うE2Eは、新規の専用テストアプリおよび明確な復旧手順が準備できてから実施します。
