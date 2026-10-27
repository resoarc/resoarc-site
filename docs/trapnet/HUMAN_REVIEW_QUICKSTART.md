# TrapNet: volunteer human security-review quickstart / 人間によるセキュリティレビュー協力のお願い

**Status (2026-10-28): Seeking independent volunteer feedback. Not audited. Not approved for deployment or public beta.**

ResoArc is developing **TrapNet**, an experimental open-source, zero-trust attack-observation and advisory network. We welcome **independent human** design and source-code reviews. AI-generated feedback and CI results do **not** count as completed independent human review.

## Start here (no setup required)

- **Open review discussion / 募集窓口:** [Issue #31](https://github.com/resoarc/resoarc-site/issues/31)
- **Experimental code / 実験コード:** [Draft PR #32](https://github.com/resoarc/resoarc-site/pull/32/files) (look under `experiments/trapnet-zero-trust/`)
- **Review scope, threat assumptions and current gaps / レビュー基準:** [independent-security-review-v1.md](https://github.com/resoarc/resoarc-site/blob/feat/trapnet-zero-trust-protocol-20261027/experiments/trapnet-zero-trust/docs/independent-security-review-v1.md)
- **Protocol / 仕様:** [TZTP v0.1](https://github.com/resoarc/resoarc-site/blob/feat/trapnet-zero-trust-protocol-20261027/docs/trapnet/TZTP-v0.1.md)
- **Private vulnerability disclosure / 非公開報告:** [SECURITY.md](https://github.com/resoarc/resoarc-site/blob/main/SECURITY.md)

**Review request:** Even **one focused 20–40 minute desk review** would help. Please select a track below. No installation, network access, VPS access, credentials, personal data, or live exploitation are requested.

## Architecture and trust boundaries

```text
Sensor (isolated, may be malicious) -> HUB (untrusted observations, verification)
Guardian (read-only local client) <- signed informational warning feed
```

- Sensor reports observations; a valid signature does not prove an observation is true.
- HUB must not gain a remote-control path to Guardian.
- Guardian should display verified informational warnings only by default, with no automatic blocking or arbitrary code execution.
- Current code is a **pre-alpha experiment** in a Draft PR. Experimental Docker/loopback checks do not establish independent physical-node or operational isolation.
- A separately deployed Sonar/VPS and its private configuration **are not within this public code-review scope**.

## Pick just one review track / 一つだけ選んでください

| Track | 20–40 minute question | Related risk |
| --- | --- | --- |
| **A. Guardian & releases** | If HUB or a signing key is compromised, can a client be tricked into executing a command, changing a firewall, accepting rollback, or accepting forged updates? | Client safety / root trust |
| **B. Sensor, HUB & authenticity** | Can validly signed lies, Sybil identities, replay, revocation failures, or resource exhaustion cause unsafe trust decisions? | Poisoning / availability |
| **C. Witness & recovery** | Can a compromised HUB rewrite or hide history while producing apparently valid witness/recovery evidence? Which trust anchor must be kept external? | Evidence integrity |
| **D. Privacy, operations & AI** | Are data minimization, operator separation, safe lab boundaries, and attacker-controlled log / prompt-injection protections adequately specified? | Consent / containment |

For a 20-minute review, **one concrete concern plus a suggested test** is a useful result. We welcome architectural objections, competing prior art, and suggestions to simplify unsafe complexity.

## How to report / 報告方法

For non-sensitive feedback, comment on [Issue #31](https://github.com/resoarc/resoarc-site/issues/31) or [Draft PR #32](https://github.com/resoarc/resoarc-site/pull/32).

Suggested short format:

```text
Track:
Reviewed revision / commit SHA:
Files or design sections:
Observation / possible failure mode:
Preconditions & impact:
Evidence or safe, non-destructive test suggestion:
Recommendation:
Confidence (high / medium / low):
```

**Do not disclose an exploitable unfixed Critical/High vulnerability, working exploit, private address, secret, or captured user data in a public thread.** Coordinate disclosure using [SECURITY.md](https://github.com/resoarc/resoarc-site/blob/main/SECURITY.md) (github@resoarc.com) first. Please do not probe any public infrastructure or third-party system. A source-only or deliberately isolated toy test is preferred.

Attribution in a public acknowledgements note is **opt-in**. No fee, formal audit certificate, endorsement, or guaranteed response is implied by volunteering. We will identify verified fixes and unresolved issues separately; a positive comment does not grant release approval.

---

## 日本語でのご案内

ResoArcでは、分散型の攻撃観測・警戒ネットワーク **TrapNet** を開発しています。安全な一般公開に先立ち、**開発関係者・開発AIから独立した人間の視点**による確認を求めています。

全コードの監査をお願いするものではありません。**20〜40分程度で、上のA〜Dのいずれか1分野について「設計上の懸念1件＋検証案」だけでも歓迎します。** レビューは公開済みの設計書やDraft PRのソースを読むだけで参加できます。

1. [募集Issue #31](https://github.com/resoarc/resoarc-site/issues/31) または [実装Draft PR #32](https://github.com/resoarc/resoarc-site/pull/32) を開く。
2. Guardianの安全性、偽報告、証跡・復旧、プライバシー・AIなど一つを選ぶ。
3. 対象コミット、懸念、成立条件、非破壊の検証案をコメントする。
4. 未修正の深刻な脆弱性は公開せず、[SECURITY.md](https://github.com/resoarc/resoarc-site/blob/main/SECURITY.md) の連絡先へ報告する。

**ご自宅のポート開放、実運用HUBへの接続、実機への侵入試験はお願いしません。** 現在の隔離試験の成功は第三者監査の完了を意味せず、一般参加・本番配布・自動遮断は承認されていません。

レビュー参加者の氏名やハンドルの公表は本人希望を確認してから行います。ご協力いただいたご意見には、修正結果と残存リスクを区別して対応します。
