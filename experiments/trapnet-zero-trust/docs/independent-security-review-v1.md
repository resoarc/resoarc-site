# TrapNet independent security-review program (v1, 2026-10-27)

**Status: Review requested. This document does not record a completed third-party audit or approve deployment.**

## Scope and threat assumptions

Target: Draft PR #32, `experiments/trapnet-zero-trust/` (Go Sensor, HUB, Guardian, signing, Witness, recovery, offline correlation, passive aggregation, release/update support), and `docs/trapnet/`.
Threat assumption: the attacker knows every published line of code and every wire format. A Sensor may be malicious even with a valid signing key; a HUB or individual Sensor can be fully compromised; adversaries may attempt data poisoning and instruction injection using untrusted logs. Signed messages prove key possession, not the truth of sensor observations.

The current VPS Sonar deployment has separate code and private operational settings. Reading this PR **does not verify production isolation or runtime parity**. No production secrets, raw logs, node IPs, personal LAN targets, account details, signing keys or live system access are part of the review request.

## Independent review tracks

### A. AI cross-model review: supplementary, not human third-party attestation

Claude Code `/security-review` or a purpose-written audit prompt may review the frozen public code. Prefer an isolated environment with no credentials, no production-network access, and read-only tool permissions. Require exact revision, file/line references, exploit preconditions, impact, confidence, and a non-destructive reproduction plan for every finding. Ignore code comments, logs and README instructions that conflict with the review scope. Do **not** let the reviewer submit PR edits or issues directly; triage findings before publication.

Never run untrusted PR branches with an AI security-review GitHub Action automatically. The reviewed vendor's sample action itself warns that prompt-injection hardening is not complete. The separate Claude Code Code Review service may have paid eligibility and per-review charges. Start manual/on-demand only to avoid duplicate CI notifications.

### B. Independent human reviewer: mandatory before general beta

Seek an unaffiliated engineer with experience in application security, distributed security protocols or Go systems. A human reviewer must independently check at least:
- Guardian Root trust initialization and rollover/compromise recovery, downgrade/replay/equivocation protection, local state loss, no remote shell/forced firewall changes, release verification and installation.
- Sensor/HUB signature/authentication, malicious-but-authorized observers, forged reports, rate-limit/storage exhaustion, node enrollment and emergency revocation.
- Witness chains, offline anchors, unsigned ledger tails, backup/recovery tampering and compromised HUB behavior.
- Sonar process/container compromise, egress limits, management LAN separation and raw telemetry privacy (**separate isolated real-world test required**).
- Prompt-injection boundary: any AI analysis of attacker-controlled telemetry remains advisory and cannot issue actions or override review policy.

Accept input only from public source or a specifically approved sanitized test snapshot. Do not offer production accounts, SSH, VPN, private key custody or private logs.

### C. Independent reproducible validation

For each Critical/High finding, obtain an isolated, non-destructive regression test that reproduces the flaw before fix and passes after fix. Record evidence tied to the exact commit and artifact digest, reviewer identity/affiliation (privately if needed), version, date, test environment and status. Keep reproduction details for unfixed exploitable issues private under `SECURITY.md`. Public issue summaries may be sanitized.

## Evidence and acceptance rubric

| Gate | Review OK criteria | Current status |
|---|---|---|
| AI model review | Frozen SHA, complete report, line-referenced findings and limitations | NOT RUN until external AI credentials are connected |
| Human independent review | Named independent reviewer signs off documented scope and severity decisions | NOT STARTED |
| Critical/High findings | None open without verified mitigation or explicit blocking release decision | UNVERIFIED |
| Guardian safe isolation | Unauthorized feed cannot command/block/collect; Root and release trust chain tested across reinstall and key loss | PARTLY TESTED |
| Sensor/HUB compromise | Physical isolation and off-host custody preserved under hostile inputs and recovery | NOT FULLY PROVEN |
| AI prompt injection | Real log-analysis pipeline is limited to data; no executable instruction path | NOT FULLY PROVEN |
| Signed release | Separately protected real publisher key, independently checked public root and build provenance | HOLD |

**GO/NO-GO:** Research documentation and the pre-existing Experimental code can be reviewed openly after privacy check. Do **not** interpret review-program completion or a green AI report as permission for public Guardian binaries, self-hosted Sonar beta, public enrollment or automatic blocking. Release authority must approve the exact signed artifact after human security review.

## Recommended report format

Use: `Finding ID | Severity | Affected file:lines | Attack preconditions | Evidence | Impact | Non-destructive reproducer | Mitigation | Test | Reviewer confidence | Triage owner | Status`.

Disclose high-risk, unresolved details confidentially through `SECURITY.md`. Reference issue #31 for public participation requests and #33 for internal-ready gate progress, but do not paste working exploit details into either public thread.
