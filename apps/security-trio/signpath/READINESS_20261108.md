# Security Trio signing readiness record

Date: 2026-11-08 UTC/JST. This document records completed public CI checks, not code signing or certification.

## Verified in GitHub on PR #91

- Review branch: `feat/security-trio-signpath-readiness-20261108`.
- Latest verified source commit: `a37a7c484035a4b09fc03c9a9e2ba62f12997c43`.
- [Windows CI run 42481405906](https://github.com/resoarc/resoarc-site/actions/runs/42481405906): **success**.
  - 118 automated tests executed by Windows Python; exact individual test results remain in logs.
  - Windows acceptance script completed.
  - Three EXEs built from checked-out public sources with PyInstaller 6.22.3.
  - Three EXEs confirmed **NotSigned**, never claimed signed.
  - Three SHA-256 manifest checks passed.
  - PE product name / file version / original file name checks passed.
  - GitHub Actions artifact: `SecurityTrio-Windows-UNSIGNED-review-only`, artifact ID `13617438107` (short retention, not a permanent release).
- [Verify public source run 42481405894](https://github.com/resoarc/resoarc-site/actions/runs/42481405894): **success** (release mirror hydration, source-asset audits, repository secret checks and site checks).
- [CodeQL run 42481405940](https://github.com/resoarc/resoarc-site/actions/runs/42481405940): **success**.
- [REUSE run 42481405896](https://github.com/resoarc/resoarc-site/actions/runs/42481405896): **success**.

The prior failing release archive hydration was addressed separately in [PR #92](https://github.com/resoarc/resoarc-site/pull/92), merged into `main` at `14b9aed61e21c46bb4b2f1e1e099b347476abc52`; the fix preserves exact size and SHA-256 checks.

## External eligibility inquiry

- 2026-11-08: An eligibility inquiry was **sent** from the connected ResoArc project mailbox to the company contact `office@signpath.io`. The question explicitly covers all three applications and the *No hacking tools* exceptions.
- This is a preliminary email inquiry, **not the formal program application**. Delivery acceptance by the recipient and Foundation feedback have not yet been verified; no eligibility decision may be inferred.
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
- No independent manual review of the scanners and PyInstaller bundled third-party licenses.
- No Windows cross-machine standard-user/SmartScreen acceptance of a newly signed release.
- The existing downloadable v0.3.0-rc4 binaries on the separate preview website remain **unsigned and unchanged**.
- The main `resoarc.com` Cloudflare deployment was not modified.

## Blocking next actions (human/operator and service)

1. Ask SignPath whether each tool falls under the artifact-development or breach-trace exceptions to its *No hacking tools* condition. A draft is in `signpath/ELIGIBILITY_AND_APPLICATION.md`.
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
