# Security Trio review-kit local acceptance record

**Date:** 2026-11-10 JST. **Nature:** ResoArc maintainer's Windows source-level tests. **NOT** a third-party assessment, GitHub-hosted CI run, independently verifiable adoption, code-signing approval, product release or general GUI/EXE acceptance.

## Reviewed checkout

- Public source branch: `feat/security-trio-signpath-readiness-20261108`
- Exact source commit tested: `e9ca8443a1f8d14de9783e16b46ca88d5cbef08d`
- Dedicated isolated main-PC checkout: `C:\Users\zin\Documents\ResoArc\security-trio-review-kit-20261110`
- Other ResoArc checkout / production site / existing unsigned RC4 binaries: **not modified**. This test execution did not sign or publish anything.

## Executed, observed results

Working directory for the commands below: `apps/security-trio` in the isolated checkout.

| Platform/runtime | Command | Actual observation |
| --- | --- | --- |
| Windows; Python 3.10 x64 | `py -3.10 -m unittest discover -s tests -p test_*.py -q` | exit 0, `Ran 169 tests`, `OK (skipped=1)` |
| Windows; Python 3.13 x64 | `py -3.13 -m unittest discover -s tests -p test_*.py -q` | exit 0, `Ran 169 tests`, `OK (skipped=1)` |
| Windows; Python 3.14 x64 | `py -3.14 -m unittest discover -s tests -p test_*.py -q` | exit 0, `Ran 169 tests`, `OK (skipped=1)` |
| Windows; Python 3.13 x64 | `py -3.13 tests/windows_acceptance.py` | exit 0, `windows_acceptance: PASS`; modes secret/log/file present |

The Windows acceptance script reported:
- secret mode: `engine_scanned=3`, `findings=2`, `cli_code=1`
- log mode: `engine_scanned=1`, `findings=2`, `cli_code=1`
- file mode: `engine_scanned=4`, `findings=6`, `cli_code=1`

The six new `test_external_review_kit.py` tests exercise only synthetic sample generation, refusal to overwrite existing outputs, file hashes, the three scanner engines and export redaction. Nine synthetic, non-executable files are generated **outside the source directory**. The external tester instructions and safe issue reporting channel are in [review-kit](../review-kit/) and [Issue #104](https://github.com/resoarc/resoarc-site/issues/104).

## Boundary of evidence

- Not tested: a newly compiled Windows EXE, Windows Defender or SmartScreen interaction, independent Windows machine, Explorer drag-and-drop, full GUI workflows, OneDrive/UNC/long-path compatibility, real documents, performance/stress limits, or real signed-candidate validation.
- Not tested: current GitHub Actions status on this exact commit. Historical PR CI passed 163 source-level tests but should **not** be misattributed to this update.
- Not established: distinct human reviewer/source approval, real usage by external parties, SignPath project/certificate enrollment, production release branch protection, approval quorum, or SignPath approval.
- **Observed external reputation count as of this record: 0 independently verified Security Trio-specific reports.**
- On 2026-11-10, SignPath follow-up questions had already been sent from ResoArc, but no new substantive response was observed during this continuation.

**Decision: HOLD PR merge, Foundation formal application, live signing and publication.** Continue collecting independently sourced results in Issue #104 and obtain human source/build review. Do not overwrite the existing unsigned RC4 EXEs.
