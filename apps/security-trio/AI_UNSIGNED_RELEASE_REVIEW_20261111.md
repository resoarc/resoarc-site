# Security Trio unsigned release AI review decision (2026-11-11)

## Decision and authority

The maintainer has instructed that **an AI-performed project security/release review may replace the project's optional third-party reviewer requirement for an explicitly UNSIGNED public release**. This is an **internal ResoArc release policy**, not an assertion that a human external reviewer, legal counsel, antivirus vendor, Microsoft or SignPath approved anything.

**Release scope authorized if final CI passes:** ResoArc Security Trio **v0.3.0-rc4 Windows x64 unsigned public prerelease**. Keep the `rc4` version because the application and Windows PE metadata still identify this build as `0.3.0-rc4` / `0.3.0.4`. Do **not** label it a signed or fully certified stable release.

## Actual AI review and observed source-evidence

- Read the actual public PR #91 source/release packaging scripts and its CI workflow, and compared the historical public CI evidence with the present source branch. Confirmed code paths for read-only offline static scan, explicit file selection, no archive extraction, bounded file sizes and counts, cancellation/incomplete-scan indicators, output path overwrite protection, URL/IP/token redaction and CSV formula escaping. This is a focused review, **not a proof that no vulnerability exists**.
- Windows source tests in a distinct checkout: `177 tests run, OK (skipped=1)` on Python **3.10, 3.13 and 3.14**. Windows non-GUI acceptance: all three engines PASS. These apply to source code, not to frozen EXE GUI operations.
- Historic [Windows CI 42625324389](https://github.com/resoarc/resoarc-site/actions/runs/42625324389), commit `3656fc73de7f9ad0ea59957835398e9d647c3b4b`: 163 tests, Win x64 PyInstaller EXE build, negative Authenticode check, native library inventories and a notice-complete **UNSIGNED** 18-entry review ZIP. That CI does **not** cover the later review-kit changes. Use only a **new** green release CI before the release is published.
- Fetched GitHub Actions artifact `13677393414`. Independently inspected the 18-entry inner distribution ZIP: exactly three EXEs, ResoArc MIT notice, SHA-256 manifest, third-party notice summary and **12 upstream license originals**. SHA-256 checks on all three EXEs **match both the inner ZIP and outer CI artifact**:
  - Secret Scout: `c80032baf1b5d763b8ab952d47bd961934864af0bc24be25249a5d3894af0fa0`
  - Log Lantern: `d8e31308dd0b509f6c8bdf7fea117697ab00e6c20f7f790c841630230600b124`
  - File Inspector: `1d6523f7cf8a796da568ce5f0645b3009d21126bf7c63e3a7a846591c1285690`
- Third-party components and notices for this *CI-built Python 3.12/OpenSSL 3* artifact are recorded in [THIRD_PARTY.md](../THIRD_PARTY.md). These notices are NOT the same set as the older Python 3.10/OpenSSL 1.1 preview EXEs.
- **Practical limitations:** no independent human security assessment; no proof of full binary reproducibility; no SmartScreen reputation or Microsoft Defender approval; no comprehensive adversarial fuzzing or broad clean-install/drag-and-drop/UNC/OneDrive/long-path/permissions acceptance for these exact frozen binaries; heuristic detection may miss threats. Don't describe a Defender test of an experimental RC5 on another host as a clean bill of health for these RC4 binaries.
- The separately tested **experimental RC5** Python 3.14/Tk9 migration is not part of this release. Do not silently substitute its EXEs or dependency license set.

## Release gate implemented in CI

- Explicit unsigned labeling in tag, title, asset filename and release notes; release itself must be clearly a **prerelease**.
- Public GitHub Actions build from exact checked-out `main` commit, `actions/checkout` credentials not persisted, Python 3.12 exact major/minor, pinned build-tool version, source unit tests and CLI acceptance.
- Enforce exactly three EXEs, Authenticode `NotSigned`, PE metadata `0.3.0.4`, exact SHA-256, 12 license originals, license coverage and frozen archive inventory, signed-release negative gate.
- Verify the full bundled ZIP and hashes again before publishing; use a unique immutable release tag, no overwrites of existing GitHub Release assets and no replacement of legacy RC4 preview files.
- Publish GitHub Release *only after* all gates pass. No release automation may touch SignPath, Cloudflare, existing website downloads or unrelated ResoArc artifacts.

## SignPath remains separately governed

**AI approval is NOT SignPath Foundation approval and does not meet any required independently verifiable reputation, genuine human signer/approver, project eligibility or GitHub origin-verification requirement.** Do not enable `security-trio-signpath.yml`, set signing credentials, describe the EXEs as signed, or submit a Foundation application based solely on this AI review.

## Status at time of writing

**Project's AI review: ACCEPTED with explicit unsigned prerelease scope and disclosures.**
**Actual public release: pending new CI success and GitHub Release URL verification.**
**SignPath: HOLD, no certificate, no signature.**