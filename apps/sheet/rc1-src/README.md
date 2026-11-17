# ResoArc Sheet v1.0.0-rc.1

無料の日本語ローカル表計算ツールです。Excelのすべての機能との互換性は保証しません。Microsoft Excel製品ではありません。

## 使い方
[公式サイト](https://resoarc.com/products/sheet/)からZIPを取得して展開し、`ResoArc-Sheet.html`をEdge・Chrome・Firefoxで開いてください。XLSX/CSVをブラウザ内で処理し、編集したものは原本と別のファイルに保存します。インストール、ログイン、ネットワークへのワークブック送信は不要です。

## 主な機能
XLSX入出力、CSV入出力、JSONバックアップ、数式バー、書式・列幅・行高変更、検索・文字列置換、値だけコピー・貼り付け、1行目を見出しとして残す並べ替え、文字列による簡易フィルター、オートフィル、XLSX保存前の互換性比較。

「ファイル → 形式を選んで保存」（または Ctrl+S）から、①Excel機能保持XLSX、②標準XLSX、③CSV、④ResoArcバックアップ（JSON）の4種類を選べます。複雑なExcelブックでは**Excel機能保持XLSX（安全保存）**を最初におすすめします。既存セルの値・数式だけを元XLSXへ反映し、元のグラフ・画像・書式を保持します。書式や行・列構造を変更した場合は利用できません。

## 注意事項
- XLSM、XLSB、旧XLS、マクロは非対応です。
- 標準XLSXでは元のグラフ・画像・条件付き書式などが失われる場合があります。既存のXLSXで標準形式を選んだ場合は利用者の明示了承を求め、実際の欠落要素がある場合は項目を表示して再確認します。了承時は **.simplified.xlsx** に別名保存します。原本は変更しません。機能保持が必要なら「Excel機能保持XLSX」を選んでください。
- 保護されたシートは編集・並べ替えを拒否します。簡易フィルター中は行・列挿入を禁止します。
- XLSX取込直後は安全保存用の初期状態を記録するまで編集できません。準備が終わると自動的に編集可能になります。
- クリップボード動作はブラウザ依存です。Excelデスクトップでの貼り付け解釈は未検証です。
- Microsoft Excel 16.0で、改訂②のExcel再保存ファイル、ResoArc Sheetの新規作成・通常保存・安全保存ファイルを実際に開く試験を実施しました。一般的なExcel互換性を保証するものではありません。重要なブックはExcelで再確認してください。
- そのほかの制限は`KNOWN_LIMITATIONS.md`を参照してください。

## QA（2026-11-16）
Nodeユニットテスト56件すべて合格、Viteビルド成功、Edge/Chrome/Firefoxの各ブラウザで検索・並べ替え・フィルター・保護シート・XLSX入出力・オフライン起動を確認。グラフ・画像・結合セル・条件付き書式・別シートのあるブックは、安全保存で画像・グラフ等のOOXML部品が元ファイルとバイト一致しました。2026-11-17追加検証：Microsoft Excel 16.0で通常保存の破損問題を再現し、ExcelJSによる再シリアライズを追加。修正後のResoArc Sheet画面から保存した2種類のXLSXがExcelで開けることを確認しました。2026-11-17保存形式選択QA：Edge/Chrome/Firefoxで4形式を検証。保持XLSXと簡易版XLSXはMicrosoft Excel 16.0でも再計算を確認。Excel完全互換を保証する結果ではありません。

## 開発
Node.js 22以上で`npm ci`、`npm test`、`npm run build`、`npm run dev`。

## OSS
ResoArcの自作部分はMIT。FortuneSheet、FortuneExcel、Reactなど第三者の部分はそれぞれの原典ライセンスです。再配布する場合は`LICENSE`、`THIRD_PARTY_NOTICES.md`、`licenses/`を保持してください。68ベンダー中9件の元ソース版は未証明ですが、候補npmのMIT/ISC原文と配布文は照合済み。詳細は`THIRD_PARTY_ORIGIN_AUDIT.md`を参照。

変更履歴は`CHANGELOG.md`をご覧ください。

## 正式版候補

この成果物は **v1.0.0-rc.1**、一般公開用正式版ではなく受入試験のための候補です。詳細な受入条件は `RC_ACCEPTANCE.md`、制限は `KNOWN_LIMITATIONS.md` を参照してください。従来版・旧タグは上書きしません。
