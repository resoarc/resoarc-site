# OpenSSF Best Practices Badge registration: ResoArc

> Status (2026-11-11 JST): **Official project #15597 achieved OpenSSF Baseline Level 1 on 2026-11-07 JST (issuer timestamp 2026-11-06T15:59:05Z).** The separate Metal-series **Passing badge is still in progress**. See the [official project](https://www.bestpractices.dev/projects/15597/baseline-1) and [current evidence review](RECOGNITION_EVIDENCE_20261111.md).

## Authoritative project details

| Field | Value |
| --- | --- |
| Public project name | ResoArc |
| Public homepage | https://resoarc.com/ |
| Public source repository | https://github.com/resoarc/resoarc-site |
| Project type | Independent open-source technology project; not a registered corporation or government body |
| Badge series and current result | OpenSSF Baseline Level 1 achieved (self-assessed); Metal Passing remains in progress |
| Software licensing | MIT for ResoArc-authored code, with per-file exceptions documented for external material |
| Registration fee | Free |

**Suggested project description (English):** Independent, free and open-source technology project providing browser-based utilities, kintone tools, and Raspberry Pi/Linux-related software.

**推奨説明文（日本語）:** ResoArcは、ブラウザ上で利用できるWebツール、kintone向けツール、Raspberry Pi/Linux関連ソフトウェアを無料で開発・公開する独立したOSS技術プロジェクトです。

## Status update after registration

The authorized ResoArc account created [issuer project #15597](https://www.bestpractices.dev/projects/15597/baseline-1). The October 17, 2026 record of an incomplete assessment is **historical**, not current. The issuer JSON now records `achieved_baseline_1_at: 2026-11-06T15:59:05.301Z`. No independent audit or Metal Passing achievement is implied. The procedure below is kept only for historical reference. The next action is to collect accurate evidence for the Metal Passing criteria.

## Steps for the project owner (historical signup instructions)

1. Open [the official OpenSSF Best Practices registration](https://www.bestpractices.dev/en/projects/new).
2. Choose **Log in with GitHub** using the dedicated **resoarc** GitHub account. Verify the account shown in the OAuth consent screen before authorizing. The badge site states that the GitHub nickname and supplied public name will be shown publicly.
3. Submit the new project with the homepage/repository above. Choose **Baseline series** to start.
4. Record the numeric project ID and public URL, e.g. `https://www.bestpractices.dev/projects/NUMBER`, in the issue tracking this registration.
5. The official evaluator may read this repository's [`.bestpractices.json`](../.bestpractices.json) and propose answers. **Review each result rather than treating suggestions as certified facts.** Save only justified values.
6. Baseline Level 1 was subsequently achieved: publish its exact issuer-provided badge. Do **not** show the separate Metal Passing/Silver/Gold badges until the issuer confirms them.

## Evidence ready to supply

| Topic | Evidence | Claim boundary |
| --- | --- | --- |
| Public source and revision history | https://github.com/resoarc/resoarc-site | Public Git history; does not prove external audit |
| MIT license and third-party rights | [LICENSE](../LICENSE), [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) | Some assets follow other licenses |
| Machine-readable licensing | [REUSE specification scan](https://api.reuse.software/info/github.com/resoarc/resoarc-site) | REUSE compliance, not security certification |
| Contributions and issue tracking | [CONTRIBUTING.md](../CONTRIBUTING.md), [Issues](https://github.com/resoarc/resoarc-site/issues) | A process is documented; don't claim response SLA without evidence |
| Vulnerability contact | [SECURITY.md](../SECURITY.md) | Policy published; do not claim completed independent audits |
| CI/source tests | [.github/workflows/verify.yml](../.github/workflows/verify.yml), [VERIFICATION.md](VERIFICATION.md) | Test execution does not imply total coverage |
| Current security evaluation | [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/resoarc/resoarc-site) | A point-in-time score, not a badge |

## Items that must not be marked "Met" without further evidence

- Branch protection and an independent code-review policy, until repository rules have actually been enabled and validated.
- A full static application security testing workflow on all relevant commits, until demonstrated.
- Fuzz testing, signed release provenance, dependency assurance and patch response SLAs, unless implemented and evidenced.
- Multiple independent reviewers, additional organizations or a formally constituted foundation.
- Higher-level Baseline or Metal Passing criteria solely because the repository has a MIT license or passing CI.

## Duplicate prevention and identity policy

First check the [official project's lookup API](https://www.bestpractices.dev/en/projects.json?url=https%3A%2F%2Fgithub.com%2Fresoarc%2Fresoarc-site). As of 2026-10-17 JST the official lookup now returns **project #15597**. Do not register a duplicate.

Use the brand's GitHub profile `resoarc` and do not sign in using personal `zin1985` / `zin2000` identities. Avoid publishing non-public personal details or any login material in GitHub, badges or application documents. The registration should truthfully identify the project as an independent initiative rather than a company or endorsed member.

The repository-local `.bestpractices.json` contains **reviewable suggestions only**. It neither registers a project nor confers any badge.
