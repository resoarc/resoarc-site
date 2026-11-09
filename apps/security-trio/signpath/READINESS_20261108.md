# Security Trio signing readiness record

Date: 2026-11-08 UTC/JST. This document records completed public CI checks, not code signing or certification.

## Current update: 2026-11-09 (latest evidence)

- **SignPath OSS response received**: Phillip Deng wrote that all three utilities **may be eligible in principle** under the development-artifact or security-breach-trace exceptions. A review of actual functionality remains necessary. SignPath specifically requires public source, an existing release and independently verifiable reputation. This is **not** an eligibility approval. Contact: `oss-support@signpath.org`.
- See [application evidence and honest reputation gaps](APPLICATION_EVIDENCE_20261109.md). The source PR is public but **unmerged**. The three Windows RC4 EXEs already distributed on the separate preview website are unsigned and unchanged. No independent Security Trio-specific reputation verification is available yet.
- Latest code under test: Python 3.12 unsigned CI **163 automated tests**, three Windows EXEs, code-signing negative test and 61 native-library license controls.
- [Windows CI](https://github.com/resoarc/resoarc-site/actions/runs/42625324389), CodeQL, REUSE and Verify public source all **success** at source commit `3656fc73de7f9ad0ea59957835398e9d647c3b4b`. Subsequent documentation commits require their own CI completion checks.
- [Maintainer third-party license verification](../THIRD_PARTY.md) completed for identified components; 12 original license files packaged with unsigned CI review ZIP. **Not** a complete independent source security review or legal certification. Existing Python 3.10/OpenSSL 1.1 binaries have a separately published [copyright notice page](https://resoarc-security-trio.pages.dev/licenses/).
- Added `package_signed_candidate.py` and signing workflow steps to re-verify actual signatures before building a signed **candidate** ZIP with SignPath request provenance, signed EXE hashes and 12 upstream license notices. New unit tests validate the offline fail-closed packaging contract. **There is still no real SignPath-signed binary** and no live signature validation success.
- SignPath's own rules require human approval per signing request, source-to-binary provenance and a protected contributor/approver structure. These remain unconfigured and may not be bypassed.

**Decision: Technical readiness continues; formal SignPath application, certificate activation, and signed release remain HOLD until evidence and human approval exist.**

## Historical record

## Verified in GitHub on PR #91

- Review branch: `feat/security-trio-signpath-readiness-20261108`.
- Latest fully green source commit before this documentation-only update: `fb099a991c85736f6379b73e41ea3f52ffa20015`.
- [Windows CI run 42495092937](https://github.com/resoarc/resoarc-site/actions/runs/42495092937): **success**.
  - 139 automated tests executed by Windows Python; exact individual test results remain in logs.
  - Windows acceptance script completed.
  - Three EXEs built from checked-out public sources with PyInstaller 6.22.3.
  - Three EXEs confirmed **NotSigned**, never claimed signed.
  - Three SHA-256 manifest checks passed.
  - PE product name / file version / original file name checks passed.
  - GitHub Actions artifact: `SecurityTrio-Windows-UNSIGNED-review-only`, review artifact produced by run 42495092937 (short retention, not a permanent release).
- [Verify public source run 42495092911](https://github.com/resoarc/resoarc-site/actions/runs/42495092911): **success** (release mirror hydration, source-asset audits, repository secret checks and site checks).
- [CodeQL run 42495092943](https://github.com/resoarc/resoarc-site/actions/runs/42495092943): **success**.
- [REUSE run 42495092918](https://github.com/resoarc/resoarc-site/actions/runs/42495092918): **success**.

The prior failing release archive hydration was addressed separately in [PR #92](https://github.com/resoarc/resoarc-site/pull/92), merged into `main` at `14b9aed61e21c46bb4b2f1e1e099b347476abc52`; the fix preserves exact size and SHA-256 checks.

## Source and dependency packaging audit

- The GitHub source tree now includes the previous rc3 archive preflight (6 tests) and privacy/accuracy regression corpus (15 tests) that were absent from the initial public CI branch. Windows CI exercises **139 tests**, and the unsigned 3-EXE build/PE metadata/hash/signature rejection checks pass.
- Actual `tkinterdnd2==0.4.3` installed-wheel inventory identifies one MIT wrapper license file and seven platform-native libraries (Linux, macOS, Windows x86, Windows x64, Windows ARM64). **This alone does not establish the complete licensing of the included TkDND native code.**
- PyInstaller's previous `--collect-all=tkinterdnd2` caused **67 TkDND archive members per EXE**, including **56 entries from other operating systems or CPU architectures**. Evidence: [Windows CI 42494862870](https://github.com/resoarc/resoarc-site/actions/runs/42494862870).
- A local Windows-x64 PyInstaller hook now collects the target platform's DLL and Tcl files only. Follow-up [Windows CI 42495092937](https://github.com/resoarc/resoarc-site/actions/runs/42495092937) confirms **11 TkDND archive members, zero cross-platform entries** for each of the three executables; total archive entries decreased from 1073 to 1008 per EXE.
- `dist/SUPPLY_CHAIN_REVIEW.json` includes version, license file paths and native wheel SHA-256; `dist/FROZEN_CONTENTS_REVIEW.json` lists actual frozen EXE archive members. These are attached to short-retention unsigned CI review artifacts, not formal signed releases.
- The locally packaged EXEs published in the separate preview site are still the **previous unsigned rc4 builds**, unchanged. The narrower hook's new EXEs are **CI-generated, internal review candidates**. Frozen Windows GUI drag-and-drop runtime acceptance on an independent desktop remains required before a signed release.
- Historical note: license-text distribution audit was still pending at this earlier point. As of the latest update above, the identified component notices are bundled; a complete independent security review and signed-release verification remain **HOLD**.

## External eligibility inquiry

- 2026-11-08: An eligibility inquiry was **sent** from the connected ResoArc project mailbox to the company contact `office@signpath.io`. The question explicitly covers all three applications and the *No hacking tools* exceptions.
- Historical state immediately after the inquiry: it was not a formal program application. A positive, non-binding SignPath response was subsequently received on 2026-11-09 (see current update above).
- The official conditions remain at https://signpath.org/terms.html. SignPath Foundation alone decides whether to accept the project.

## Strengthened signature release validation

- The signed-release gate now rejects any additional files or directories alongside the expected three EXEs before producing the post-signing hash manifest.
- Signed PE metadata (product, company, version and original filename) must match the approved release configuration.
- The unsigned Windows CI also runs the signed-release verifier as a negative test; it must reject the locally built unsigned EXEs.
- This is a test of failure behavior only. Actual SignPath-signed binaries have not yet been tested.

## What was explicitly NOT completed

- No SignPath Foundation application submitted and no eligibility ruling received.
- No actual signed executable, code-signing certificate, certificate serial or signer SHA-1 available.
- No SignPath organization / signing policy / artifact configuration established in the service.
- No SignPath GitHub App enrollment / trusted origin policy completed.
- No actual authorized human signer/approver roster and MFA verification evidence.
- Independent manual security/code review of the scanners remains pending. The identified third-party license texts were checked and bundled in the later 2026-11-09 maintainer audit.
- No Windows cross-machine standard-user/SmartScreen acceptance of a newly signed release.
- The existing downloadable v0.3.0-rc4 binaries on the separate preview website remain **unsigned and unchanged**.
- The main `resoarc.com` Cloudflare deployment was not modified.

## Blocking next actions (human/operator and service)

1. **Completed as a preliminary, non-binding answer:** SignPath indicated possible eligibility in principle but must inspect actual functionality and project reputation. See latest update above.
2. Obtain explicit SignPath Foundation approval, if eligible. No approval may be assumed from passing CI.
3. Assign real project authors/reviewers/approvers, verify MFA, enforce protected signing branch and SignPath project manual approval, and create the protected `signpath-approved` GitHub environment.
4. Configure actual `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_SIGNING_POLICY_SLUG`, `SIGNPATH_ARTIFACT_CONFIGURATION_SLUG`, `SIGNPATH_SIGNER_SHA1_THUMBPRINT`, and `SIGNPATH_API_TOKEN` as scoped GitHub variables/secrets only after formal enrollment. Never commit tokens.
5. Validate the approved artifact configuration using a real SignPath test request, inspect the signed artifact, then require `verify_signed_release.ps1` to pass.
6. Release signed binaries as a new version with signed-binary hashes, provenance and human approval record. Do not silently overwrite the published unsigned rc4.

## Policy references

- https://signpath.org/terms.html
- https://docs.signpath.io/artifact-configuration/reference
- https://docs.signpath.io/trusted-build-systems/github

Status: **Signing preparation CI PASS; Foundation eligibility and signature NOT obtained.**
