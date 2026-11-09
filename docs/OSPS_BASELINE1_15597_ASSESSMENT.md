# OpenSSF Best Practices #15597 | Baseline Level 1 achieved

**Current verified official status (2026-11-07 JST): 100% / 24 of 24 Level 1 controls Met; Level 1 self-assessment badge awarded.** The official issuer provided `achieved_baseline_1_at=2026-11-06T15:59:05.301Z`. Official confirmation: https://www.bestpractices.dev/projects/15597/baseline-1

The final two criteria were resolved with real evidence: LE-03.02 verified 35 ZIPs x three domains plus LICENSE/NOTICE delivery; LE-02.02 documents MIT and Apache-2.0 licensing of all 35 released software assets, upstream legal text matches and the operator's statement of personal, AI-assisted original development with no employer/client code reuse. Both are marked **Met in the official issuer record**.

**Important distinction:** this is a voluntary **self-assessment badge**, not an independent security audit, legal clearance, or a guaranteed absence of third-party copyright issues. Historic source build provenance for older plugin versions remains under review. Full dated evidence: [Baseline 1 achieved report](compliance/OSPS_BASELINE1_ACHIEVED_20261107.md).

## Historical preparatory notes (2026-10-17 to 2026-11-06, superseded)

The sections below were written before the final 2026-11-07 submission and are kept as change history only. Any prior "no badge", 17%, 50%, 92%, or unfinished controls are **historical**, not the current official status.

### Branch protection: active and validated in GitHub UI

- Official [branches API](https://api.github.com/repos/resoarc/resoarc-site/branches/main) returns `protected=true` after the dedicated `@resoarc` owner completed a GitHub sudo-mode reauthentication. Earlier results of `protected=false` no longer apply.
- Verified persisted classic protection rule matching `main`: **PR required**, status checks `verify` and `reuse` required, **administrator bypass prohibited**, force-push and deletion permissions disabled. A mandatory one-person approval was **not** imposed, as this project has no genuine independent reviewer at this time.
- OSPS-AC-03.01 and OSPS-AC-03.02 were explicitly submitted to BadgeApp as **Met** with dated GitHub UI/API evidence. We did not deliberately attempt a destructive branch push/deletion to test rejection.

### Owner security: 2FA enabled, evidenced

On 2026-11-06 the authenticated @resoarc GitHub account's security page showed a configured Authenticator app and recovery-code management; the project account received a GitHub email explicitly confirming that two-factor authentication had just been enabled. The earlier observation that 2FA was disabled was before enrollment and has been superseded. OSPS-AC-01.01 is now submitted as **Met**. Recovery code content and TOTP secrets were not accessed, copied or published. Maintain safe offline recovery methods and review privileged access when collaborators are added.

### Verified final two Level 1 blockers, and remediated controls

- **OSPS-LE-02.02: Unmet.** First-party code is declared MIT and source ZIPs generally include MIT license texts; signed installer ZIPs have companion source and MIT/NOTICE in the official GitHub Release. A complete package-by-package third-party rights review is not yet signed off. Do not assume rights merely because the software is available for download.
- **OSPS-LE-03.02: Unmet.** All 20 historical ZIPs are in the [GitHub release mirror](https://github.com/resoarc/resoarc-site/releases/tag/resoarc-osps-distribution-mirror-20261106), alongside LICENSE and NOTICE, with SHA-256 verification. However, the Cloudflare production URL for LICENSE/NOTICE was previously observed as HTTP 404, so distribution-site recipient evidence is still outstanding. Publish through the canonical Cloudflare process and verify 200 responses/links and package hashes before closing.
- **AC-02.01, BR-01.01, BR-01.03, BR-07.01, DO-01.01, QA-02.01, QA-04.01, QA-05.01, QA-05.02: Met as of 2026-11-06**, based on [merged PR #69](https://github.com/resoarc/resoarc-site/pull/69) and [merged PR #70](https://github.com/resoarc/resoarc-site/pull/70), both with passing CI. The current tree has **zero tracked distribution ZIPs**; original bytes are preserved externally. The remaining 34 binary assets are reviewable image/font media with pinned SHA-256 metadata, not generated installer executables.
- Project-owned automation and review do not create an independent third-party security assessment. Historical git commits still reference the former ZIP files; this audit concerns the current working source tree and does not silently rewrite history.

This section and the live issuer's machine-readable values supersede the **2026-10-17 proposed answer table below**. In particular, old table entries mentioning unprotected main, 2FA disabled, 20 tracked ZIPs, or a 17/50% badge state are historical and **must not be used as current evidence**.

## Proposed responses and evidence (historical draft; see current status above)

| Criterion | Proposed | English justification or next validation |
| --- | --- | --- |
| **OSPS-AC-01.01** MFA for sensitive resources | **?** | Confirm GitHub `resoarc` has enforced 2FA/MFA, and review every privileged collaborator or application before declaring Met. Personal 2FA settings are not exposed via public APIs. |
| **OSPS-AC-02.01** collaborator privileges | **Met** (based on platform design, verify locally) | "This is a personal-account GitHub repository. The repository owner must explicitly invite each collaborator and the invitation must be accepted. GitHub does not grant write access to newly encountered users automatically. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository" |
| **OSPS-AC-03.01** direct commits prevented | **Unmet** | "The current GitHub API reports `main.protected=false` and no active matching repository rules. Direct pushes are not yet technically blocked. We are preparing enforced branch protection and do not claim compliance." |
| **OSPS-AC-03.02** default branch deletion safeguard | **Met** (platform default branch) | "GitHub does not permit deletion of the repository default branch until an authorized actor explicitly selects a different default branch first. The project's default is main. https://docs.github.com/en/pull-requests/how-tos/commit-changes/managing-branches-within-your-repository" Adding active no-deletion branch protection is still recommended. |
| **OSPS-BR-01.01** untrusted CI metadata sanitation | **?** | Eight GitHub Actions workflow files were searched for direct untrusted event/inputs interpolation into shell scripts; no obvious patterns were found. This scan alone does not prove all externally supplied parameters are validated. |
| **OSPS-BR-01.03** untrusted PR code cannot reach privileged credentials | **Met, subject to review** | "The public workflows use least-privilege GitHub tokens. The Scorecard reports Dangerous-Workflow=10/10 and Token-Permissions=10/10; privileged release jobs are separated from read-only PR tests. See .github/workflows and the Scorecard report." Verify all release/workflow triggers before final submission. |
| **OSPS-BR-03.01** official channels encrypted | **Met** | "Official project homepage and source repository use HTTPS: https://resoarc.com/ and https://github.com/resoarc/resoarc-site." |
| **OSPS-BR-03.02** authenticated distribution channels | **Met** | "Software downloads are distributed over HTTPS on https://resoarc.com/ and/or GitHub Releases, using authenticated TLS transport. SHA-256 manifests are provided for applicable download artifacts." |
| **OSPS-BR-07.01** unencrypted secrets not committed accidentally | **?** | ".gitignore excludes credential file types, and source validation checks selected secret patterns. Confirm repository-wide coverage and pre-commit/push preventive controls before marking Met." |
| **OSPS-DO-01.01** release user guides | **Met** | "Published tools have publicly readable usage and download guides, available from https://resoarc.com/products/ and https://resoarc.com/guide/. Pre-release limitations are stated separately." |
| **OSPS-DO-02.01** defect reporting | **Met** | "Defects can be reported in public GitHub Issues; CONTRIBUTING.md documents how to contribute and report problems: https://github.com/resoarc/resoarc-site/blob/main/CONTRIBUTING.md." |
| **OSPS-GV-02.01** public discussion | **Met** | "The public repository hosts GitHub Issues and Pull Requests for public project discussion: https://github.com/resoarc/resoarc-site/issues." |
| **OSPS-GV-03.01** contribution procedure | **Met** | "The project documents its contribution procedures in https://github.com/resoarc/resoarc-site/blob/main/CONTRIBUTING.md." |
| **OSPS-LE-02.01** OSI/FSF-compliant source license | **Met** | "ResoArc-authored source code is released under MIT, an OSI-approved license. Third-party material retains its own licenses. See LICENSE and THIRD_PARTY_NOTICES.md." |
| **OSPS-LE-02.02** released software licenses free/open | **?** | "Most ResoArc source release ZIPs include MIT LICENSE and third-party notices are separated, but the scope of all 20 distributed archives needs inspection before attesting that every released software asset is under a compliant license." |
| **OSPS-LE-03.01** license file in repo | **Met** | "The repository includes LICENSE and LICENSES/, with a verified machine-readable REUSE 3.3 report: https://api.reuse.software/info/github.com/resoarc/resoarc-site." |
| **OSPS-LE-03.02** license included with released assets | **Unmet / repair needed** | "Several signed kintone plugin ZIP packages currently contain a signed inner contents.zip, PUBKEY and SIGNATURE; neither the outer nor inner archive includes a LICENSE. Ensure a LICENSE is distributed alongside every corresponding release asset or in its released source." Do not edit signed ZIPs without re-signing. |
| **OSPS-QA-01.01** public source repo | **Met** | "The complete project source is publicly readable at the stable URL https://github.com/resoarc/resoarc-site." |
| **OSPS-QA-01.02** public change history | **Met** | "GitHub's publicly visible Git commits and Pull Requests record changes, authors and timestamps: https://github.com/resoarc/resoarc-site/commits/main." |
| **OSPS-QA-02.01** direct dependency list | **?** | "Nine plugin package.json files exist and list no external JS dependencies; their build/test scripts use Node built-ins. Audit other Python, OS and release-build toolchains before claiming all direct package dependencies are accounted for." |
| **OSPS-QA-04.01** multiple-repository documentation | **N/A** | "The scoped project currently consists of one public repository under the `resoarc` GitHub account: https://github.com/resoarc/resoarc-site. The multiple-repository condition does not apply." Reevaluate if new repos are added. |
| **OSPS-QA-05.01** no generated executable artifacts tracked | **Unmet** | "The Git repository currently tracks 20 distribution ZIP files in site/downloads/, including signed installable kintone plugin packages. Migrate generated distributions to a separate artifact delivery path without breaking public download URLs." |
| **OSPS-QA-05.02** no unreviewable binaries | **?** | "Signed plugin archives inspected to date contain reviewable JS/CSS/HTML/JSON plus PNG icons and signature material, but review the full tree and all archives before declaring this condition Met. Automated Scorecard Binary-Artifacts=10/10 is not sufficient evidence alone." |
| **OSPS-VM-02.01** security contact | **Met** | "SECURITY.md documents the private contact github@resoarc.com, scope and coordinated vulnerability disclosure process: https://github.com/resoarc/resoarc-site/blob/main/SECURITY.md." |

## Highest-priority remediation

1. **Protect `main` with an active rule.** The 2026-11-06 configuration attempt specified PR required, `verify` and `reuse` checks, no admin bypass, no force pushes/deletions, and **no mandatory peer approval** until a real reviewer is available. GitHub **Confirm access** password re-authentication stopped final creation; post-attempt public GitHub API still reports `protected=false`. An authorized human must finish sudo confirmation and verify enforcement via API/negative test. Do not claim the branch is protected until that happens. Confirm owner and repository-plan enforcement compatibility instead of assuming a draft rule applies.
2. **Add correct license alongside each released package**, without repacking signed kintone ZIP files. In [the 2026-11-06 20-asset audit](compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.md), 11 signed installer ZIPs lacked embedded `LICENSE`, while 9 source ZIPs had one. The compliance PR adds an exact first-party `site/downloads/LICENSE`, a companion `NOTICE.md`, eight user-facing signed QA per-product links and SHA-256 evidence. **Cloudflare production deployment, user receipt of sidecars, full third-party obligations and three other signed legacy asset delivery flows still need evidence**; OSPS-LE-03.02 remains PARTIAL.
3. **Stop tracking the 20 generated distribution ZIP assets** only after setting up independent, integrity-checked distribution hosting. Keep public links and checksum verification working first.
4. **Review account MFA and collaborator permissions** on the owner-controlled account, and audit actual workflow secret isolation.
5. **Do not re-register or overwrite the existing project metadata**; the public issuer already shows name/description filled with 17% progress as of 2026-11-06. Confirm any existing `Met` claim such as OSPS-LE-02.02 against package-level proof. Submit remaining answers truthfully only after re-authentication and evidence review; no badge until the issuer awards it.

## Honest status

This project **is registered** but **has not earned Baseline Level 1**. Registration and passing the self-assessment are separate events. No independent security certification or organizational endorsement is implied.
