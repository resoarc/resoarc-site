# OpenSSF Best Practices #15597 | Baseline Level 1 assessment draft

**Status: DRAFT. No baseline badge earned.** Updated 2026-10-17 JST.

Official project: https://www.bestpractices.dev/projects/15597/baseline-1
Repository: https://github.com/resoarc/resoarc-site

The official project exists (ID **15597**, repo and homepage verified), but the badge issuer still reports **Name Unknown / 0%**. Its metadata and criteria have not been completed. Submit only after signing in as the dedicated `resoarc` GitHub account and reviewing the actual evidence. Statuses below are **recommendations**, not submitted self-certification claims. A question mark means evidence is insufficient.

## Proposed responses and evidence

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

1. **Protect `main` with an active rule.** Deny direct pushes, block branch deletion, require the CI checks `verify` and `reuse`, and carefully test developer/admin bypass and release automation. A ruleset saved with **Disabled** enforcement does not satisfy OSPS-AC-03.01. Confirm owner and repository-plan enforcement compatibility instead of assuming a draft rule applies.
2. **Add correct license alongside each released package**, without repacking signed kintone ZIP files. Publish the license and third-party notices next to each download, then verify the public URLs and release metadata.
3. **Stop tracking generated installable plugin archives** after setting up independent, integrity-checked distribution hosting. Keep public links and checksum verification working first.
4. **Review account MFA and collaborator permissions** on the owner-controlled account, and audit actual workflow secret isolation.
5. **Enter the project name and description on #15597** and answer criteria only with validated evidence. Never show an earned badge until the issuer reports it.

## Honest status

This project **is registered** but **has not earned Baseline Level 1**. Registration and passing the self-assessment are separate events. No independent security certification or organizational endorsement is implied.
