<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->
# ResoArc 署名付きプラグインの著作権とライセンスの確認方法

公開した署名付きkintoneプラグインZIP（`contents.zip` / `PUBKEY` / `SIGNATURE`）は、署名の有効性を保護するため、ライセンス表記の追記目的では中身を変更しません。

- ソースコードに表示されたSPDXと、各正式リリースの `LICENSE` / `NOTICE` / ソースアーカイブが配布条件の確認資料です。
- リポジトリのMITライセンスはResoArcが権利を保有しMIT提供した部分を対象とし、第三者の著作物や商標への許諾を意味しません。
- 各ZIPのSHA-256および内部ライセンス／SPDX有無の台帳は、`/recognition/reuse-signed-archives.json` に公開します。
- 署名ZIP内部にライセンスファイルがないことは、それだけで著作権違反を意味しません。一方、外部のNOTICEやソースのMIT表記のみで配布物の全内容の権利が証明されるわけでもありません。
- 原本にライセンス文書がない4件（Date Calculator / Grid Editor / Kanban / List Search の signed-qa ZIP）は、それぞれの *v0.1.0-alpha source ZIP* にMITライセンス文書が含まれることを確認しました。ただし、source ZIPと署名QA ZIPの内容が完全に一致するかは未照合であり、権利監査は引き続き必要です。
- 新たな署名ZIPまたは既存ZIPのバイナリ変更は、公開前のハッシュ監査で停止します。正式公開前に配布物の権利とNOTICEの個別確認が必要です。

**これは説明資料であり、元のZIPへの変更やデジタル署名の再生成ではありません。**

確認先： [ライセンス情報](/license/) ／ [公開ソース](/source/) ／ [REUSEの検査状況](/recognition/)
