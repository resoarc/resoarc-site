# ResoArc レコード再利用制御 v1.0.2 リリースノート

## 修正内容
- 再利用直後にDate・Status等の設定対象フィールドが戻る問題を修正。
- 遅延補正が後続の画面操作で変更された新しい入力値を上書きする競合に対し、画面ごとのgeneration guardを追加。
- 既存のプラグインIDを維持し、旧版v1.0.0から上書き更新が可能。

## QAの実測と制限
- Chromium/Firefox/WebKit × desktop/mobile相当の署名済みJS回帰30/30 PASS。
- 開発用kintoneで署名ZIP v1.0.2 の実インストールを確認。
- 実際にインストールしたブラウザー上の再利用操作4/4 PASS、テストレコード1件の保存で対象項目の初期化を確認。テストレコード削除後の元データ整合PASS。
- 既存アプリの設定・レコード保持9/9 PASS。
- 管理者/閲覧専用/アクセス拒否の複数実アカウント試験、物理スマホ、旧版への実切戻しは未完了。利用前に検証アプリで確認してください。

## 識別情報
- SHA-256: c34bccd3e4ec7b18b232f5c06078a3ecbe19f61b8e9c1801dd276ca5ebe67016
- プラグインID: ijippnanodkplekephlnngfbebiopljj
- MITライセンス / ResoArc独立OSS。
