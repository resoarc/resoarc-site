# SignPath Foundation application readiness | ResoArc Security Trio

Date: 2026-11-09 (JST). **Prepared evidence, not an application submission or acceptance.**

## Contact and eligibility status

On 2026-11-09, the ResoArc project mailbox received a reply titled **"SignPath Foundation"** from Phillip Deng at SignPath OSS support following a three-tool eligibility inquiry. The response stated that, based on the descriptions, the utilities **may be eligible in principle** under the exceptions for scanning software artifacts during development/testing and detecting traces of security incidents. An actual functionality review is still required to decide.

The response also explicitly requires **public source, an existing release, and sufficient independently verifiable reputation**. The supplied contact for follow-up is `oss-support@signpath.org`; the official application URL is https://signpath.org/apply.

Do **not** describe this as preliminary approval: neither application acceptance nor a certificate exists.

## What a reviewer can already inspect independently

| Evidence | Public reference | Status |
| --- | --- | --- |
| Three applications and their described capabilities | https://resoarc-security-trio.pages.dev/ | Public unsigned developer preview |
| Existing form of distributed software: Windows EXEs | `https://resoarc-security-trio.pages.dev/downloads/ResoArcSecretScout.exe`, `.../ResoArcLogLantern.exe`, `.../ResoArcFileInspector.exe` | Three previously released unsigned RC4 EXEs; still unchanged |
| Published code signing policy | https://resoarc-security-trio.pages.dev/code-signing/ | Public; explicitly not SignPath-approved |
| Third-party license and copyright page | https://resoarc-security-trio.pages.dev/licenses/ | Public for **legacy Python 3.10/OpenSSL 1.1** preview |
| Public source with tests/build/release scripts | https://github.com/resoarc/resoarc-site/pull/91 | Public **PR branch** pending review; **not merged into main** |
| Automated Windows CI for new Python 3.12 candidate | https://github.com/resoarc/resoarc-site/actions/runs/42625324389 | 163 source tests and Windows acceptance pass; three unsigned EXEs built |
| Python 3.12 unsigned CI review package | Linked GitHub Actions artifact in the run above | Contains 3 EXEs, 12 license originals, ResoArc MIT license, notices and SHA-256; **not published release** |
| Complete native DLL/notice allowlist | `audit_license_coverage.py` and tests in PR #91 | 61 native components in each EXE mapped to 12 third-party notice originals; unknown components fail CI |
| Static analysis and source provenance | CodeQL, REUSE and Verify public source checks on PR #91 | All green for commit `3656fc73de7f9ad0ea59957835398e9d647c3b4b` |

Original public unsigned legacy RC4 hashes (verified after publishing licenses):

- Secret Scout: `7d73999d45de689fa5644fb835d0ee7fdb185119ca9e995a6bbc4b13022111e0`
- Log Lantern: `4a28200ef3482bb5b08d1845a673ae1118c845e1aefabfdc2d428968973129c5`
- File Inspector: `1d1ad0901ed157f0feee86c567ece0444da11477449930bbc29914fdec1f5e30`

These hashes identify the **old** preview EXEs, not the newer unsigned GitHub Actions artifacts.

## Product-by-product scope

**Secret Scout**: Read-only, offline inspection of user-selected software source, configuration files and ZIP/JAR archives for accidentally embedded credentials. No live network probing.

**Log Lantern**: Offline analysis of existing Apache/Nginx/IIS logs for traces of attempted attacks and suspicious access patterns. No live service probes or exploitation.

**File Inspector**: Static triage of local PDF, Office, LNK, ZIP and other attachments without executing them; warnings about risky structures, not exploit tests or an antivirus replacement.

None of the three applications should claim comprehensive vulnerability assessment, malware absence, user security guarantees or SignPath approval.

## Reputation: evidence must be project-specific and independently verifiable

ResoArc's larger GitHub repository has **other releases**, but those releases are not Security Trio releases. Do not substitute ResoArc's OSS activity, project self-descriptions, CI badges or a mention of different ResoArc products as a proven third-party **Security Trio** reputation.

At the time of this record, no independently verified press review, third-party user adoption report or external security assessment *specifically for Security Trio* was established. The pre-existing unsigned RC4 distribution is newly published and may not meet SignPath's reputation threshold. The Foundation alone decides the threshold.

## Applicant-side preflight checklist

- [x] Confirm hypothetical eligibility under security-scanning exceptions: **positive indication only, not approval**
- [x] Publicly describe what each app does and does not do
- [x] Publicly distribute the existing unsigned form of the three Windows executables
- [x] Publish and preserve current and legacy copyright/license terms
- [x] Prepare a public GitHub source/build/test PR and CI verification
- [x] Keep a code-signing policy with unsigned release status
- [x] Prepare a manually triggered SignPath GitHub artifact, metadata-restricted to own 3 EXEs
- [x] Prohibit unknown native DLLs and missing third-party license texts in unsigned CI
- [x] Prepare post-signature verified candidate package, hashes, provenance and notices
- [ ] Obtain independent, verifiable reputation evidence for these particular three applications, or ask Foundation whether the existing project history suffices
- [ ] Finish human security/source review and merge public source after review
- [ ] Configure real GitHub protected release branches, approval environment, contributor MFA and reviewer/approver roles
- [ ] Confirm whether system libraries / Tcl license meet the Foundation program requirements
- [ ] Submit formal application and obtain explicit SignPath Foundation approval
- [ ] Register the project, signing policy and artifact configuration in SignPath and install/configure its GitHub App
- [ ] Request and approve an actual signature, then verify signed EXEs, code-signing EKU, timestamps, exact certificate thumbprint, and signed hashes
- [ ] Verify a complete signed package with notices and a second human release approval
- [ ] Publish a new signed version explicitly; do **not** overwrite the unsigned RC4

## Important technical distinction

The `.github/workflows/security-trio-signpath.yml` workflow is an **inactive pre-approval template**. Without real SignPath variables, credentials, required protected environment and branch policy, it is not executable as a legitimate signing workflow. Its signed-candidate packaging has only been unit-tested with synthetic hashes; **real SignPath-signed binaries have never been obtained or verified**.

## Reference

- SignPath Foundation terms: https://signpath.org/terms.html
- Application: https://signpath.org/apply
- Signing from GitHub Actions: https://docs.signpath.io/trusted-build-systems/github

**Final status: Signing-code preparation in progress, application NOT SUBMITTED, signed release HOLD.**
