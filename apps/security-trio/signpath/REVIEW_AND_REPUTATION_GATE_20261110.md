# Security Trio: independent review and SignPath evidence gate

Date: 2026-11-10 (JST). **Applicant preparation only.** This file is not an application, SignPath acceptance, approval record, security certificate or permission to release.

## Verified project facts

- Source and review: [ResoArc Security Trio PR #91](https://github.com/resoarc/resoarc-site/pull/91), still unmerged and open for review. Keep `site/` and all existing unsigned downloads unchanged.
- Dedicated unsigned preview: https://resoarc-security-trio.pages.dev/ with three Windows x64 v0.3.0-rc4 executables. They **are not Authenticode-signed**.
- Recorded Windows CI on an earlier reviewed PR commit: [run 42625324389](https://github.com/resoarc/resoarc-site/actions/runs/42625324389) reported 163 tests passing, three unsigned Windows builds, failed-as-expected unsigned signature gate, 61 inventoried native components and 12 third-party notice originals. **Re-check the checks on the actual release commit.**
- Source MIT licensing and third-party terms: [THIRD_PARTY.md](../THIRD_PARTY.md). The legacy Python 3.10/OpenSSL 1.1 preview and newer Python 3.12/OpenSSL 3 CI candidates have different notices.
- SignPath OSS support's reply dated 2026-11-09 said the functionality **may be eligible in principle**; actual feature review, released public source, and independently verifiable project reputation are needed. This was **not approval**.
- No Security Trio-specific independent user adoption, independent product review or independently verified external security assessment established as of this record.

## Evidence register (do not inflate)

| Evidence category | Current count/status | Acceptable later proof | Not acceptable alone |
|---|---|---|---|
| Independently published Security Trio review | **0 verified** | URL to review by an identifiable external publisher with date and product identity | Self-authored press release or a review of another ResoArc product |
| Independently described Security Trio use | **0 verified** | Public issue/post from a distinct user with reproducible usage context, consent to cite | Maintainer test, bot comment, star-only count |
| External source/security review | **0 verified** | Review/PR by a human reviewer, scope and findings linked to commit SHA | AI-only analysis or CodeQL pass |
| Project-specific release history | **Unsigned RC4 preview only** | Public release page, hashes, changelog, release date, archive of artifact | Other ResoArc product releases |
| Build provenance and testing | **Available for earlier PR CI** | Passing workflow, exact commit SHA, build artifact hashes | Any CI check treated as proof of external reputation |
| Human code review / signing approval | **NOT ESTABLISHED** | Distinct authorized human identities/roles, recorded review and MFA verification, per-request manual approval | AI persona, alternate account owned by the same person, automated approval |

The Foundation decides how much reputation is sufficient. Do not invent a minimum number of reviews/downloads or imply that an open GitHub issue proves adoption.

## Targeted human/external review protocol

1. Invite testers to choose **one of the three unsigned tools**, using only synthetic or non-confidential inputs. State explicitly that Windows security warnings and organizational policies must not be bypassed.
2. Request Windows version, tool and app version, exact download URL/SHA-256, test type, expected vs. actual behavior, reproducible steps, and whether the report may be cited in SignPath materials.
3. For source review, focus on: untrusted archive/log/document parsing, path traversal/symlinks, file overwrites, PII/secret redaction, formula injection, request-free/offline behavior, failure indicators, CI dependencies, native-library licensing, and signing origin.
4. Record author independence (external person, self-managed account, maintainer, bot), evidence URL, review date, and source/build SHA. Avoid real credentials, sensitive logs, customer documents, private contact details, and binary malware samples in public issues.
5. Investigate and reproduce findings in an isolated test environment. Fix on the existing review branch, test, and request a **real human review**; self-checks and AI audits are engineering aids only.
6. Count an external review/adoption only after verifying independence and public URL. Maintain a transparent negative/zero status until then.

## Human signing and release control, to be configured by owner

- **Author(s)**: human identities actually entrusted with source and CI changes; MFA verified by repository owner.
- **Reviewer(s)**: named authorized humans, review of production code **and** CI/build/release scripts, approval of exact commit. Do not substitute `resoarc` self-approval or bot output for independent review.
- **SignPath Approver(s)**: named entrusted humans assigned in SignPath after actual account acceptance; every signing request reviewed and approved **manually**. Record request ID, exact source commit, artifact digest, reviewer decision, date and rationale.
- **GitHub rules**: protected `release/security-trio-*` branch or exact named release branch (verify policy compatibility); block force-push/bypass where available; required status checks and PR reviews; `signpath-approved` environment restricted to approved branches and human reviewers. Configure only when real approvers and enrollment exist.
- **Origin**: GitHub Actions trusted build and SignPath Origin Verification; exact three own EXEs and consistent PE metadata. No local or uploaded executable may be silently substituted.
- **Post-sign**: require `verify_signed_release.ps1` success, pinned expected signer thumbprint, valid Authenticode/EKU/timestamp, fresh signed SHA-256, complete license notices, distinct human release acceptance, and a new versioned download path.
- **No authorization by this document**: do not submit a signing request, trigger the manual signing workflow, create a signed release, merge PR #91, overwrite old binaries or deploy `site/`.

## Open issues to ask SignPath (avoid premature assumptions)

1. Is the currently public **unsigned developer preview**, with source in an unmerged public PR, enough for the "already released" and "public source" conditions, or must source be merged and a versioned GitHub Release published first?
2. For the *reputation* criterion, what kinds of **Security Trio-specific independently verifiable evidence** would be useful? Would published reviews or third-party issue-based test reports be evaluated?
3. Please review each tool separately against the "No hacking tools" clause: Secret Scout (artifact scanning during development), Log Lantern (incident-trace review), File Inspector (static attachment triage).
4. Are the Tcl/Tk `TCL` license and the proprietary Microsoft CRT **System Library** treatment compatible with the Foundation conditions for these specific bundles? Share [THIRD_PARTY.md](../THIRD_PARTY.md) and native inventory.
5. Are the proposed manual approver quorum, protected release branch rules and artifact metadata restrictions sufficient once the account exists?

Do **not** disclose account IDs, tokens or credentials in the public repository. Send any follow-up from the authorized ResoArc project mailbox, and preserve their response as evidence without treating informal guidance as approval.

## Release decision record

**HOLD** on SignPath application as "ready", signing, publication and PR merge. Continue only non-destructive technical review, independent tester outreach and evidence collection. The current signed-package pipeline is an **inactive** candidate workflow that has not verified an actual SignPath-signed executable.

Official rules: https://signpath.org/terms.html
