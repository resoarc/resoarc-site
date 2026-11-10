# Offline synthetic reviewer self-check: local acceptance

**Recorded:** late 2026-11-10 through early 2026-11-11 JST. **Scope:** internal Windows source-level verification only. Not an independent external review, actual EXE validation, SignPath application, signature or production release.

## Changes introduced

- Added `review-kit/verify_samples.py`: checks that all nine synthetic sample files, exact file names, SHA-256 hashes and canonical generated manifest are unchanged before exercising the three scanner source engines.
- Reports only fixed case IDs, PASS/FAIL and aggregate counts. No arbitrary source lines, sample data, scan paths, real credentials, network requests or actual user files are captured. Optional JSON report can be created only at a new path outside the sample set.
- Made the ZIP fixture deterministic by fixing synthetic member timestamps; this removes time-dependent hashes.
- Added eight integration tests covering valid results, restricted reporting, byte-for-byte reproducibility, tampered sample/forged manifest rejection, unexpected files, overwrite refusal and invalid report location.
- Added Japanese quick-start instructions. Corrected incorrectly escaped Markdown code snippets in the original reviewer README and the earlier acceptance record.
- Omitted a local Windows account path from the public acceptance document at the branch tip. Previous commit history can retain old content; no force push or history rewrite was attempted.

## Test evidence observed on a dedicated isolated Windows checkout

| Test | Result |
| --- | --- |
| Python 3.13 x64, `python -m unittest discover -s tests -p test_*.py -q` | exit 0; **Ran 177 tests; OK (skipped=1)** |
| Python 3.10 x64, same test command | exit 0; **Ran 177 tests; OK (skipped=1)** |
| Python 3.14 x64, same test command | exit 0; **Ran 177 tests; OK (skipped=1)** |
| Windows acceptance with Python 3.13 `tests/windows_acceptance.py` | exit 0; PASS all 3 source/CLI modes |

Tested code change set: `e0176d905753ddf3dcbae07199e197c6178130f1`. The validation clone was also fast-forwarded to the Japanese-documentation HEAD `a95dff05fa35b671b0ddebe51acdc838ca193f52` before the Python 3.10/3.14 and Windows acceptance runs. Later change `b34c09482e4ac9c362a84620bc318af06586ce07` only redacted a public documentation path. The checkout was clean after the runs.

**Test count interpretation:** 177 tests were run, with 1 skipped; the test process succeeded. Eight additional test cases were introduced relative to the prior 169-test collection. This is neither 177 independent users nor a count of 177 live binaries.

## External and certification status

- GitHub [Issue #104](https://github.com/resoarc/resoarc-site/issues/104): only ResoArc's own kit announcement was present at inspection; **zero independently verifiable outside Security Trio reviews**.
- [PR #91](https://github.com/resoarc/resoarc-site/pull/91): open; no distinct human APPROVED review observed. A newer experimental RC5 internal QA summary was posted separately, not merged into this PR.
- No new GitHub Actions CI run for this exact source was established by the connector; these results are **locally observed Windows runs only**.
- Gmail search to check for new SignPath replies returned an access error in this continuation; **new reply status was not verified**. Do not infer either approval or absence of a reply.
- No Windows EXEs were rebuilt, signed, overwritten, re-released or deployed by these changes. No SignPath action was invoked.

## Release decision

**HOLD** merger of PR #91, SignPath formal application, certificate activation and public signed release. Obtain a separate human code/source review, maintain per-request human SignPath approval, and gather real product-specific third-party reports.

Reviewer instructions: [review-kit](../review-kit/README.md). Human/OSS requirements: [review gate](REVIEW_AND_REPUTATION_GATE_20261110.md).
