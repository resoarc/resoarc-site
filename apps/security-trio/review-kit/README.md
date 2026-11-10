# Security Trio reviewer kit (synthetic data only)

This kit helps **independent people** reproduce concrete behavior for [PR #91](https://github.com/resoarc/resoarc-site/pull/91) and [external review Issue #104](https://github.com/resoarc/resoarc-site/issues/104). It is **not a signed release**, an external assessment, or proof of SignPath approval. Existing RC4 Windows EXEs are unsigned.

## 日本語クイックスタート

3アプリを**実データを使わず**試すための合成サンプル9件と、ソース版の自動セルフチェックです。実在の秘密情報、顧客ログ、マルウェアは含みません。未署名EXEを実行するためにWindowsや組織の保護機能を解除しないでください。ソースレビューのみでも歓迎です。

Python 3.10以降を用意し、公開ソースの `apps/security-trio` で以下を実行します。

```powershell
py -3 review-kit/generate_samples.py --output "$env:TEMP\SecurityTrioReviewSamples"
py -3 review-kit/verify_samples.py --samples "$env:TEMP\SecurityTrioReviewSamples"
```

結果を新規のJSONファイルに保存する場合（既存ファイルは上書き不可）：

```powershell
py -3 review-kit/verify_samples.py --samples "$env:TEMP\SecurityTrioReviewSamples" --report "$env:TEMP\SecurityTrioReviewResult-01.json"
```

- 9件のファイル名・容量・内容・SHA-256が、生成器の正本と一致するか確認します。改ざんを検出すると処理を中止します。
- ソース版3アプリの基本検出と模擬秘密・IPの出力抑制を確認します。**EXEやGUIは起動しません**。レポートには固定のテストIDと件数のみを記録し、ローカルのパスやサンプル内容は含めません。
- セルフチェックのPASSは、**合成データに対するソースエンジンの検証成功**です。EXEの安全性、独立レビュー、SignPath承認を意味しません。
- 実際にGUIを使った感想・改善案・外部ソースレビューは [Issue #104](https://github.com/resoarc/resoarc-site/issues/104) にお寄せください。提出前に個人情報が含まれないか再確認してください。

拡張子が `.exe` のサンプルは実行できない**文字列データ**です。実行しないでください。PDF用サンプルも実文書互換性の保証には使えません。

## Quick start

1. Review the [unsigned preview and limitations](https://resoarc-security-trio.pages.dev/). Do **not** disable Windows Defender, SmartScreen, or your organization's security controls. You may instead review the source without running a binary.
2. With Python 3.10+ installed, from `apps/security-trio` run:
   ```powershell
   py -3 review-kit/generate_samples.py --output "$env:TEMP\SecurityTrioReviewSamples"
   ```
   Pick a **new** destination each time. The generator blocks overwriting an existing destination or generating inside the source tree. It has no package dependencies, network requests or malware.
3. Check `manifest.json` for each sample SHA-256 and the *expected* finding. All generated inputs are fabricated, harmless markers or logs from TEST-NET IP ranges. The synthetic PDF markers are **not full valid PDFs**. The `.exe`-named fixture is **plain text, never run it**.
4. Use **Select file** in each Security Trio app to inspect a corresponding sample. Avoid moving generated fixture content into a production directory. Try the app's JSON or CSV export to a separate directory.
5. Write down your **observed** results. Do not simply copy expected values or say “PASS” unless you actually tested. In particular, report false positives, missing warnings and unclear language.

| App | Generated sample | What to check |
| --- | --- | --- |
| Secret Scout | `secret-review.env` | A **synthetic** password-shaped assignment is flagged, but the fabricated value is absent from findings/export |
| Secret Scout | `secret-placeholder.env` | Obvious placeholder has no secret finding |
| Secret Scout | `archive-review.zip` | Warn on mock secret and unsafe ZIP entry; **no actual extraction** |
| Log Lantern | `access-review.log` | 15 synthetic requests, secret-file probe and repeated distinct 404s; original IP and query token absent from exports |
| Log Lantern | `normal-access.log` | One normal 200 request with no suspicious finding |
| File Inspector | `pdf-marker-review.pdf` | Reports a static PDF active-content **marker**; this is not a full document compatibility test |
| File Inspector | `mismatch-review.pdf` | Says a supposed PDF has PNG signature |
| File Inspector | `double-extension.pdf.exe` | Flags double extension; file is plain text, **not executable** |
| File Inspector | `plain-review.txt` | Ordinary text has no warning |

## Technical self-test (not independent evidence)

From `apps/security-trio`:
```powershell
py -3 -m unittest discover -s tests -p "test_*.py" -v
```

The included `tests/test_external_review_kit.py` and `tests/test_external_review_verifier.py` check generator non-overwrite, SHA-256, deterministic fixtures, expected detections, JSON redaction, and fail-closed rejection of altered kits and existing reports. Automated tests and maintainer checks are **internal evidence only**, not external user reputation or a full review of GUI/EXE runtime behavior.

## Report back

Use [Issue #104](https://github.com/resoarc/resoarc-site/issues/104) and state:

- **Tool/version** and **source SHA or EXE SHA-256** (plus whether source, legacy unsigned RC4 EXE, or newer unsigned CI artifact)
- OS build and how you ran the test (GUI, CLI or source inspection)
- Which sample and the **expected vs actually observed** result, including any export-only issue
- Reproduction steps or a safe, redacted screenshot
- Whether we may link your public report in a SignPath Foundation eligibility submission, with attribution

Please **never** attach real access tokens, actual customer logs, private source, personal data, or live malware. A GitHub account alone does not establish reviewer independence. The maintainer will label internal/bot/AI reports separately and include only genuinely verifiable external evidence in eligibility materials.

## Release restrictions

The kit creates input samples only. It does not modify the scanners, invoke SignPath, disable security controls, trigger a release, overwrite unsigned downloads, merge PR #91 or deploy the site. The project still needs human security/source review, independent reputation evidence, SignPath acceptance and per-request human signing approval. See [the evidence gate](../signpath/REVIEW_AND_REPUTATION_GATE_20261110.md).
