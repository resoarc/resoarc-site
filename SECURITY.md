# Security Policy / セキュリティポリシー

## Reporting a vulnerability / 脆弱性の非公開報告

ResoArc welcomes responsible vulnerability disclosures. Do not publish access tokens, private data, exploit instructions, or unresolved vulnerabilities in public GitHub Issues, Discussions, or Pull Requests.

脆弱性の疑い、認証情報の漏えい、意図しないデータ公開などを発見した場合、公開Issueには書かず、**github@resoarc.com** までメールでご連絡ください（転送メール窓口）。

Please email **github@resoarc.com** with the affected product/version, reproduction conditions, expected and actual behavior, and possible impact. Share sensitive reproduction details only through this private contact.

## Scope / 対象

This policy covers publicly maintained code and downloads in this repository, including the ResoArc website and ResoArc tools. Development previews, alpha/beta components and ResoArcOS pre-releases are not production-ready; they are handled on a best-effort basis. See the individual release notes for support limitations.

このリポジトリで保守中の公開ソースおよび配布ファイルを対象とします。開発版・α版・β版・ResoArcOSプレビュー版のサポートはベストエフォートです。公開済みの開発プレビューを本番用途の安全なOSだと保証するものではありません。

## Response and disclosure timeline / 対応目安

- We aim to acknowledge reports within **7 calendar days**. This is a goal, not a guaranteed service-level agreement.
- We privately assess reproducibility, affected versions and severity, then coordinate remediation and an appropriate disclosure date with the reporter.
- An estimated fix timeline will be shared when sufficient information is available; critical issues may need a faster response, while complex reports may take longer.
- We do not promise a universal fixed deadline or a vulnerability-free codebase.
- Once mitigation is ready, we will publish an advisory, release notes or other appropriately scoped notice without disclosing unnecessary personal information.

- 受信後**7暦日以内の一次返信を目標**とします（対応期限の保証ではありません）。
- 再現性・影響範囲・重大度を非公開で確認し、修正方針および公開時期を報告者と調整します。
- 修正予定が見積もれる段階で目安を伝え、重大な問題は優先して扱います。
- 必要な対策ができた時点で、適切な範囲で注意喚起や変更履歴を公開します。

## Safe handling / 取扱い

Avoid accessing other people's data, persistence, disruption or broad automated scanning. Test only systems and accounts you control or are authorized to assess. Do not send secrets or personal data with a public issue.

第三者のデータやシステムへの無断アクセス、サービス妨害、無差別なスキャンを行わないでください。報告メールに秘密情報を含める必要がある場合は、まず共有方法をご相談ください。

The ability to inspect public source code is not proof that software contains no vulnerabilities.
