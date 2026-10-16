# ResoArc Mini v0.1.2 → v1.0 安全性改修オーバーレイ

**状態：開発版・未署名・正式リリース不可。** このディレクトリ単体では18機能の完全なソースではありません。正本ZIPを展開した上で適用する差分です。

## 正本と適用方法

正本：`resoarc-mini-plugins-v0.1.2-source.zip`、SHA-256 `22f22159407063a90fc354cf0ee1af1283f402f25fe554d5f7c49026a4da0edb`、152ファイル。

Windows側の正本: `Documents/GitHub/resoarc-mini-plugins` に展開済み。**ここは書き換えません。** QAコピーに下記3ファイルを同じ相対パスで適用してください。

- `scaffold.py`：18機能共通のフィールド更新検証、設定の許可リスト、値の安全な表示変換、外部リンクのデフォルト拒否。
- `package.py`：全18個の元の秘密鍵と公開鍵指紋を全件検証してから署名。欠落や相違の場合はZIP生成前に失敗し、新規の秘密鍵を作らない。
- `runtimes/related-links.js`：外部HTTPSリンクは管理者設定 `allowExternal: "true"` の場合だけ有効。既存設定との互換性に注意。
- `tests/v1-security.cjs`：型検証、プロトタイプ汚染、数値・日付・時刻・HTML、オフサイト遷移などの8試験。
- `tests/mobile-text-normalizer.cjs`：入力文字自動整形のモバイル保存イベント4試験。
- `scripts/build_source.py`：18機能のソースを再生成し、参照アセットとJavaScript構文を検査して未署名ソースZIPを作成。

構築は署名付き `build.sh` を不用意に実行せず、QAコピーの中で `python scaffold.py` と `python bundle_qr.py` を使用してください。署名秘密鍵はGitHubへコミットせず、`package.py` については元鍵がない状態での失敗を負の試験として確認するだけです。

## 2026-10-17 Windowsでの検証実績

- 元の152ファイルの内容ハッシュ一致、正本無変更。
- 18機能のイベント登録31件、Edgeモックブラウザー17件、追加安全性8件：全合格。
- 追加したモバイル用ソースを含め、JavaScript 38ファイルの構文・manifest 18件の参照アセット：全合格。
- 元秘密鍵がない場合の署名生成拒否：合格。秘密鍵・配布ZIPは作成されていません。
- **モバイル用manifestは18件中1件**（入力文字自動整形）。4件のモバイルイベント模擬テストは合格。他17機能のモバイル実装と、実機モバイル受入は未達。
- すべてテスト環境の模擬kintoneであり、実テナントへの導入・共存・権限テストは未実施。

証拠：[Windows候補版QA](../../docs/kintone-progress/evidence/mini-v1-local-qa-20261017.json)、[モバイル試作と未署名ソースZIP](../../docs/kintone-progress/evidence/mini-v1-text-mobile-20261017.json)。

ローカルの未署名ソースZIP：`resoarc-mini-v1-candidate-source-only-20261017.zip`（157ファイル、SHA-256 `8d153f2dfda3969d53bcb4a5e069d72ef5fa0a94a30e8f784a16408ec626dff3`）。これはkintoneへ直接導入できる形式ではありません。

正式版にするには、元鍵の所有確認、機能別テストアプリでのPC・モバイル受入、異常系と共存試験、リリース台帳の承認が必要です。
