# 初回公開・更新チェックリスト

## アカウント分離

- ResoArc専用のGitHubアカウントと専用メールアドレスを用意し、本人確認を完了する。
- 公開コミットの作者メール、Git設定、GitHubプロフィールに個人用の情報を含めない。
- 管理者・共同開発者のパブリックな活動から個人名が推測されうることを理解する。
- 個人用アカウントからのフォーク、個人リポジトリへの移動、個人の認証トークンでのpushを避ける。

## 配布アーカイブの安全な復元（2026-11-06以降）

- 公開用チェックアウトには生成済みZIPをGitで保持しません。まず `python scripts/verify_external_archive_mirror.py --hydrate` を実行し、GitHub Release に保管した20件のZIPが監査JSONのSHA-256・サイズと一致することを検証してください。
- 旧版インストール済みkintoneプラグインの署名は変更しません。ダウンロードURL `/downloads/<filename>.zip` を維持するため、Cloudflare Pagesへアップロードする実体はZIPを復元した `site/` ディレクトリとしてください。
- `python scripts/verify_site.py` と `python scripts/audit_release_license_evidence.py` が成功することを確かめ、LICENSE/NOTICEの公開URLが200になり実体が正しいことを確認してください。
- 復元失敗・SHA不一致・署名不一致・元URLへのアクセス不可なら **公開を中止**。GitHub Releasesへ勝手に差し替えたり、未検証ファイルを強制的に配布しないこと。
- **注意**: これは配布復元手順の整備であり、現在のCloudflare本番反映成功を意味しません。実際に本番を操作した後、HTTP応答とZIP SHA-256を照合して証跡化してください。

## 公開前

- `python scripts/verify_site.py` が成功する。
- Git差分を確認し、API鍵、個人情報、クラウド設定、ログ、バックアップを含めない。
- `THIRD_PARTY_NOTICES.md` の権利表示を確認する。
- 公開サイトとライセンスページの表記を一致させる。
- コミットしたファイルと本番配信ファイルのSHA-256照合結果を記録する。

## 初回公開後

- パブリックリポジトリを公式サイトにリンクする。
- コード変更時にCIを通し、更新内容・制約・テスト結果を明示する。
- 必要ならGitHub Releasesを付け、公開版を固定する。
- DNS、Cloudflare PagesおよびGitHubの管理権限は分けて保護する。

この作業フォルダーには個人アカウントをremoteとして設定しません。
