# ResoArc Backup & Migration: kintone実API検証環境

検証先は**メインPC側の非公開設定で指定する開発者テナント1件**に固定します。**この環境は既存業務アプリへ書き込みません。**

事前に `Documents\MoleRemote\ResoArcKintoneQA-config.json` を作成します。形式は公開用の [QA_CONFIG.example.json](QA_CONFIG.example.json) を参照してください。

```json
{
  "origin": "https://YOUR-QA-TENANT.cybozu.com",
  "probeAppId": 1
}
```

`probeAppId` は権限確認用の既存アプリで、**GETだけを送る対象**です。値は実テナントの読み取り可能なアプリIDを指定してください。専用Edgeを起動しても、この非公開設定ファイルはGitHubにアップロードしません。

## 1. 専用Edgeでログイン

メインPCで以下のCMDファイルをダブルクリックするか、PowerShellから実行します。

```powershell
cd "$env:USERPROFILE\Documents\GitHub\resoarc-backup-alpha\plugins\backup-migration"
npm run qa:start
```

CMD: `scripts\Open-ResoArc-QA-Edge.cmd`

起動した「ログイン」のEdgeウィンドウでkintoneに正規ログインしてください。通常のEdge、Mole RemoteのヘッドレスEdgeとは**完全に別のプロフィール**です。

- プロフィール: `Documents\MoleRemote\ResoArcKintoneQA`
- 接続方式: 一時的なランダムポートで、**127.0.0.1に限定したChrome DevTools Protocol**
- ログインセッション: Edge自身が管理。パスワード、Cookie、APIトークン、CSRFトークンの書き出しは不要
- 再起動: `npm run qa:start`。Edgeを閉じても同じプロフィールを使い回します
- 終了: 専用Edgeのウィンドウを閉じるだけ。作業後は閉じることを推奨します

**注意:** デバッグポートを開いている間、PC上のほかのプロセスから専用ブラウザへアクセスできる可能性があります。共有PCでは使用しないでください。外部ネットワークへポートを公開しません。

## 2. ログイン・API疎通と実行計画（読み取り専用）

```powershell
npm run qa:status
npm run qa:plan
```

`qa:status` はログインセッション・設定した`probeAppId`のGET権限・管理済みQAアプリの有無を確認します。`probeAppId`は**読み取りのみ**に使用し、変更しません。`qa:plan` は作成予定のQAアプリ・フィールド構成と安全ガードを表示します。どちらもレコードを書き込みません。

## 3. 検証専用3アプリの自動構築（明示的承認が必要）

```powershell
npm run qa:provision -- --confirm CREATE_ISOLATED_QA_APPS
```

kintone開発者テナント内に名前が `ResoArc QA <10桁のランダムID>` で始まる3アプリを**新規作成**します。

| QAアプリ | フィールド | 用途 |
| --- | --- | --- |
| source | Title / Amount / QAChoice / Attachment / Notes（MemoとNestedAttachmentを含むテーブル） | 合成データ専用のバックアップ元 |
| destination | 上記に加え一意制約付きResoArcRestoreKey | 追記復元先 |
| management | BackupName / SourceAppId / ArchiveHash / BackupVersion / RecordCount / Archive | ZIP管理 |

新規アプリの動作テスト環境にフォームを追加し、**これら3アプリだけを運用環境へ反映**します。既存アプリのフォーム変更はしません。失敗時は作成途中のアプリIDを保存して中止し、同じアプリを重複作成しません。アプリ作成・管理権限が必要です。

QAアプリのIDと名称は `Documents\MoleRemote\ResoArcKintoneQA-state.json` に記録します。**認証情報は含みません。** この状態ファイルが既にあれば、再作成を拒否します。

## 4. 実kintone APIの往復試験

```powershell
npm run qa:run -- --confirm RUN_ISOLATED_QA_ONLY
```

試験対象は前段で自動作成した3アプリに限定されます。毎回、kintone APIから**アプリIDとアプリ名の完全一致**を検証し、復元先の重複禁止設定も確認します。

1. sourceに3件の合成レコードと2箇所の添付ファイルを用意
2. 実Cursor APIで元データを取得
3. **製品と同じ`makeArchive`でZIP生成**し、SHA-256で整合性確認
4. managementに実ファイルアップロード＋管理レコード登録
5. managementからZIPを実ダウンロードし、ハッシュを再照合
6. **製品と同じ`createMappedRestorePlan`と`runResumableRestore`**でdestinationへ追記
7. 復元済みキーを確認してもう1回実行、**追加0件**を確認
8. 3レコードのフィールド値・サブテーブル値、通常とテーブル内の添付ファイルを**バイト単位で照合**

同じZIPが再現できるよう、ZIP内のファイル日時を固定しています。**同じQAコマンドを繰り返しても新規復元は発生しない**設計です。成功時の出力はテストアプリID・件数・ハッシュ・判定のみで、レコード本文を表示しません。

## 5. 1コマンドで構築と実行

ログイン後、QAアプリが未作成なら作成から実API往復検証まで一度に実施できます。既に作成済みなら再利用します。

```powershell
npm run qa:auto -- --confirm CREATE_AND_TEST_ISOLATED_QA
```

本コマンドは**新規テスト用アプリ3件の作成、本番設定への反映、合成レコード追加**を伴います。ログインしただけでは自動実行されません。

## 誤操作防止・残課題

- API接続先は単一の開発者テナントに固定
- 既存アプリ49は読み取り確認にのみ使用
- アプリ名とIDがQA状態ファイルと一致しない場合、書き込み前に拒否
- レコード更新・削除、アプリ削除、実業務アプリの変更は未実装
- 明示的な `--confirm` 無しのプロビジョニング・復元を禁止
- 生成したデータは**架空のQAデータのみ**。他の業務データは取得・公開しません
- QAアプリは試験後も残ります。自動削除機能は設けていません。管理者が必要に応じて削除してください
- 本番リリースは、**実API試験が成功し、結果を独立確認するまでNO-GO**です

このAPI試験は本来の製品操作パネルを自動クリックするものではありません。製品のバックアップ・ZIP復元・マッピング・重複防止の**共通コード**を実kintone APIで試すもので、操作画面は別途ブラウザCIで検証します。実テナント上の操作画面を通した試験も、最終判定前に行ってください。

API仕様参照： https://cybozu.dev/ja/kintone/docs/rest-api/apps/form/add-form-fields/ および https://cybozu.dev/ja/kintone/docs/rest-api/apps/settings/deploy-app-settings/
