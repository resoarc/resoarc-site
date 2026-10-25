<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->

# ResoArc Security Self-Assessment (Draft for Maintainer Review)

**Status:** Draft, 25 October 2026. Not a third-party audit or a completed OSPS Baseline attestation.

## Scope and ownership

This assessment covers the publicly documented website source, related GitHub Actions CI workflows, distribution of repository-maintained static tools, and source publication procedures in `resoarc/resoarc-site`. ResoArc is an independent open-source technology project, not a corporation, public authority, or Linux Foundation stewarded project. The maintainer account is `resoarc`. It does not assert security properties of users' kintone tenants, VPS systems, external hosting providers, or unfinished ResoArcOS development previews.

## Critical assets and security boundaries

| Asset | Threat | Existing evidence / remaining limitation |
| --- | --- | --- |
| Git repository and main branches | Unauthorized change or upstream-source divergence | GitHub/Codeberg main trees are currently different; GitHub main lacks enforced branch protection. Central synchronization review is HOLD. |
| Public web content | Compromised deployment, malicious script, incorrect content | `scripts/verify_site.py`, `site-manifest.sha256` and [deployment controls](../../DEPLOYMENT.md). Passing checks do not prove security. |
| Software and archives | Unreviewed dependencies, licensing or supply-chain tampering | [third-party notices](../../THIRD_PARTY_NOTICES.md), immutable digests and release verification guidance. Rights attribution still requires product-level review. |
| Build and CI actions | Untrusted PR input and excessive privileges | CodeQL/REUSE/site validation workflows; workflow security reviews and token scoping remain important. |
| Vulnerability reports | Undelivered sensitive reports or mishandled disclosures | [SECURITY.md](../../SECURITY.md) provides a private reporting contact and response objectives. Contact delivery tests are separately required. |
| Releases and provenance | Incorrect signing/verification claims | [Release provenance guide](../release-provenance.md) describes which future artifacts may include attestations and warns historical dev builds were not attested. |

## Governance and contributor controls

- Public change guidelines are in [CONTRIBUTING.md](../../CONTRIBUTING.md); source and asset rights are described in [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
- The documented path for site updates is [DEPLOYMENT.md](../../DEPLOYMENT.md), with prepublication review and validation. A document alone does not establish that all production changes were performed this way.
- Current GitHub main branch protection is **not enforced**. Until Codeberg/GitHub source authority is reconciled, automatic branch protection changes and cross-repo overwrites must be reviewed centrally.
- Releases and private signing credentials require authorization and a separate evidence trail. No claim is made that all components have complete license provenance.

## Threat scenarios and mitigations

1. **Supply-chain substitution.** Attackers or mistakes may insert unexpected code into a trusted dependency or release archive. Mitigate through locked dependencies, manifest and digest comparison, SPDX evidence and human approval of rights/provenance.
2. **CI privilege escalation.** A workflow triggered by an untrusted event may execute attacker-controlled content. Mitigate with pinned actions, least permissions, CodeQL, static review of GitHub Actions and avoiding secret access from untrusted PRs.
3. **Publication drift.** GitHub and Codeberg contain different tracked content. Publishing a stale tree could remove website features or release evidence. Block merge/deployment pending a per-file reconciliation and rollback plan.
4. **Vulnerability disclosure failure.** A security mailbox could be unreachable or a report could be exposed in a public issue. The security policy instructs non-public reports; end-to-end delivery must be tested.
5. **Client-side compromise and unsafe restores.** Third-party assets, external responses or improperly scoped permissions can compromise user workflows. Test only authorized QA systems and do not guarantee user tenant security.

## Incident response, remediation and verification

Potential private reports are directed to [SECURITY.md](../../SECURITY.md). The policy describes acknowledgment targets, investigation, coordination and post-remediation communications but does not promise a guaranteed SLA. Maintainers should triage reproducibility, severity and affected releases privately, plan and test remediation in authorized environments, record decisions, then coordinate public advisories where warranted.

Evidence currently includes public CodeQL, REUSE and site validation CI plus the security metadata review PR. These checks are bounded; no claim of a third-party penetration test, vulnerability-free state or baseline certification is made.

## Remaining work / acceptance criteria

- [ ] Maintainer verifies architecture, threat list, role and incident process; correct any assumptions.
- [ ] Codeberg/GitHub authoritative-source differences and branch protection controls resolved.
- [ ] Full OSPS Baseline assessment at justified maturity level, including human-only controls.
- [ ] Local and CI security tooling evidence linked from valid `security-insights.yml`.
- [ ] Security mailbox delivery and release recovery procedures verified with timestamped evidence.
- [ ] This draft formally reviewed, committed to the authoritative default branch, and externally submitted only with maintainer approval.

**Assessment type:** Open-source maintainer self-assessment draft. The Security Slam Inspector badge requires a completed assessment, published in the repository and linked from Security Insights, then organizer review.
