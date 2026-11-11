<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->

# ResoArc 公開Web HTML文法検査（2026-11-11 JST）

W3C Nu HTML Checker（外部サービス）に対して、ResoArcの本番公開URLをそのまま `doc` として渡し、JSONレスポンス内の `messages[].type == "error"` を集計した。検査時点の結果であり、過去・将来のHTMLや個別JavaScript実行状態を保証しない。

| 公開URL | W3C HTML error | その他メッセージ | 公開検証URL |
|---|---:|---:|---|
| https://resoarc.com/ | **0** | 53 | https://validator.w3.org/nu/?doc=https%3A%2F%2Fresoarc.com%2F&out=json |
| https://resoarc.com/recognition/ | **0** | 30 | https://validator.w3.org/nu/?doc=https%3A%2F%2Fresoarc.com%2Frecognition%2F&out=json |
| https://resoarc.com/tools/hash/ | **0** | 7 | https://validator.w3.org/nu/?doc=https%3A%2F%2Fresoarc.com%2Ftools%2Fhash%2F&out=json |
| https://resoarc.com/tools/csv/ | **0** | 7 | https://validator.w3.org/nu/?doc=https%3A%2F%2Fresoarc.com%2Ftools%2Fcsv%2F&out=json |
| https://resoarc.com/products/ | **0** | 8 | https://validator.w3.org/nu/?doc=https%3A%2F%2Fresoarc.com%2Fproducts%2F&out=json |

`https://resoarc.com/trust/` の検査はサービス側の `HTTP 429 Too Many Requests` で判定不能だった。**0エラーには含めない。**

- その他メッセージは Nu Checker の `info` / `warning` 等を含み、「すべての警告がない」ことを意味しない。
- エラー0件は対象HTMLの文法チェックに限る。WCAGアクセシビリティ適合、セキュリティ、SEO、応答速度の認証ではない。
- 5ページ以外の製品ページ、配布ファイル、βページは検査範囲外。
- この文書は検査証跡の公開用スナップショット。公式バッジの発行やW3Cによる推奨・後援を意味しない。
