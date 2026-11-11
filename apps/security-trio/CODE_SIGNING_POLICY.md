# Code signing policy | ResoArc Security Trio

**状態（2026-11-11）: [未署名RC4 GitHubプレリリース公開済み](https://github.com/resoarc/resoarc-site/releases/tag/security-trio-v0.3.0-rc4-unsigned)。SignPath Foundationへの正式申請・承認・署名発行はいずれも未完了です。**

公開中の **v0.3.0-rc4 Windows EXEは未署名** です。SignPath FoundationまたはResoArcが発行した署名が付いていると表明しません。署名を取得できた場合に限り、以下の仕組みを有効化します。

## 既存の未署名リリースと証拠

- 公開ソース：[ResoArc Security Trio](https://github.com/resoarc/resoarc-site/tree/main/apps/security-trio/)（[PR #91 マージ済み](https://github.com/resoarc/resoarc-site/pull/91)、mainマージコミット `49515e094537e72728615960686df287d45ae3e1`）
- 既存配布物：[v0.3.0-rc4-Windows-x64-UNSIGNED プレリリース](https://github.com/resoarc/resoarc-site/releases/tag/security-trio-v0.3.0-rc4-unsigned)、ダウンロードした実ZIPを再照合済み、SHA-256 `347da414b41157d4b181a8009e6e57ae34dee9ab38bcb88af6317fd74e2fecf8`
- ビルド・公開記録：[GitHub Actions run 42884793392](https://github.com/resoarc/resoarc-site/actions/runs/42884793392)。同一の信頼済みmainソースから3 EXEビルド、署名がないこと、メタデータ、ハッシュ、第三者ライセンスを検証して未署名ZIPを公開。
- SignPathとのやり取り：2026-11-09の担当者回答は「機能面では原則対象となり得るが正式評価が必要」。2026-11-10に既存リリース・独立評判・Tcl/Tk / Microsoft CRTについて質問済み。2026-11-11時点で追加回答を確認できず、正式応募もまだ。
- 外部実利用・プロジェクト固有の信頼性証拠：[利用者フィードバック募集Issue #104](https://github.com/resoarc/resoarc-site/issues/104)。現時点で自作投稿を除く第三者の独立利用報告・レビューは確認できていない。**AIレビューやCIはSignPathの第三者評判の代替としません。**
- 署名準備用CI：[`security-trio-signpath.yml`](https://github.com/resoarc/resoarc-site/blob/main/.github/workflows/security-trio-signpath.yml) はSignPath認可前のテンプレートであり、サービスアカウント・秘密鍵・承認者・保護環境の準備や実際の署名は未実施です。

**次の判断ゲート：** SignPathからの返答を確認し、許容される外部評判の実証方法・第三者ライセンスの適否・実在する署名承認者とMFAを確定してから、必要な審査申請を行います。申請前にSignPath署名の有効化や既存ダウンロードの上書きを行いません。

## 署名対象

- `ResoArcSecretScout.exe`（Windows x64）
- `ResoArcLogLantern.exe`（Windows x64）
- `ResoArcFileInspector.exe`（Windows x64）

署名するのはResoArc自身が保守するSecurity Trioの公開ソースから、GitHub上の承認されたビルドで生成した実行ファイルだけです。ローカルPCのEXE、第三者の実行形式、別製品の実行形式を署名要求に紛れ込ませません。

## 署名方法と公開

対象制度: **Free code signing provided by SignPath.io, certificate by SignPath Foundation**（*承認後にのみ適用*）。

- 署名要求は、ResoArcの公開GitHubリポジトリ内のGitHub Actionsが生成した成果物に限定します。
- SignPathのGitHub Origin Verificationを有効にし、署名用の承認済みブランチ・コミット・ビルド実行を検証します。
- **すべての署名要求を人が手動承認**します。テストが通っただけでは署名しません。
- 完成した署名付きEXEについて、Authenticodeの署名状態、証明書、タイムスタンプ、PEメタデータ、SHA-256を検証します。
- 署名済みリリースを公開するときは、署名後のチェックサム、ソースコミット、ビルドログ、署名状態を掲載します。未署名版と同じURLを無言で上書きしません。
- 未署名であることを隠したり、SmartScreen / Defenderの無効化を促したりしません。

## 役割

- **Authors / コミッター**: GitHubの `resoarc` アカウントが管理する保守担当者。
- **Reviewers / レビュアー**: `resoarc` リポジトリでレビュー権限を持つ保守担当者。**現在、独立レビュー実施の証跡は未取得です。**
- **Approvers / 署名承認者**: 承認後にSignPath組織で承認権限を与えられる実際の担当者。未設定・未確認。

自動化アカウントやAIエージェントは署名の人手承認者として扱いません。SignPathとGitHubのMFA、保護ブランチ、レビュー、必要なポリシーは運用上の前提条件であり、確認前には完了と宣言しません。

## プライバシーと安全性

3アプリはユーザーが選んだローカルファイルを静的に一次点検する設計で、検査対象ファイルをネットワーク上に送信する処理は実装していません。ソース/依存関係のインストールやCIはネットワークを使用します。ログ・検出結果・ファイル名に機密情報が残る可能性があり、共有前に利用者自身の再確認が必要です。

各アプリはマルウェア検知の完全性、脆弱性診断の網羅、侵入の証明、SmartScreen警告の解消を保証しません。

## 問題の報告

機密情報や実際のトークンは公開Issueに投稿しないでください。脆弱性の連絡方法は [SECURITY.md](./SECURITY.md) を参照してください。

## 承認前に残る条件

1. 公開ソース・未署名GitHub Release・ビルド履歴は整備済み。第三者ライセンスのSignPath制度への適合性は最終判断待ち。
2. SignPath Foundationの**セキュリティツール除外条項**に本ツールが抵触しないかの公式判断。
3. 署名用リリースブランチ保護、実在する人間のレビュー・承認、MFA、署名者権限の設定。プロジェクトのAIレビューは署名申請に必要な独立評判を代替しません。
4. Windows PEのファイル名・製品名・バージョンメタデータを署名ポリシーに固定すること。
5. SignPath組織ID、プロジェクトslug、署名ポリシーslug、APIトークン取得後のGitHub Actionsへの安全な設定。

公式ポリシー: https://signpath.org/terms

SignPath GitHub連携: https://docs.signpath.io/trusted-build-systems/github
