# CodeQL v0.68: safe mainline rollout and release-frozen source boundaries

Status: mainline source/test maintenance only. No signed package replacement.

## Mainline changes in PR #73
Four *non-release-locked* JavaScript quality changes:
- `scripts/kintone-progress.mjs`: explicit statement terminator.
- `scripts/test_scorecard_live.mjs`: remove unused test local.
- `tests/kintone-progress.test.mjs`: remove unused import.
- `tests/suite.test.cjs`: strengthen positive HTML-escaping test.

These changes do not alter any frozen Web8 GA v1.0.0 files, kintone signed ZIPs, or versioned alpha/beta source packages.

## Why the other 13 changes are NOT blindly merged
The fully tested 17/17 CodeQL fix remains at [Draft PR #71](https://github.com/resoarc/resoarc-site/pull/71), with the four-language scan [run 42188720811](https://github.com/resoarc/resoarc-site/actions/runs/42188720811) reporting JS/TS 0. However, the Web8 GA v1.0.0 source ZIP was frozen at a pinned SHA, and the beta/alpha kintone source trees must match signed QA packages and source archives. Changing those 13 tracked files in place would fail `scripts/verify_web8_v1.py`, `scripts/verify_suite16_readiness.py` and/or `scripts/verify_alpha_archives.py`, misrepresenting historical downloads.

The 13 pending source-only changes are: 3 stable Auto Number, 3 Auto Number beta, 3 Kanban alpha, 3 List Search alpha and 1 Web8 `site/assets/tools/suite-core.js`.

**Next step:** prepare properly versioned successor packages and new hashes/signatures with preserved plugin identity and explicit QA status, then ship separate verified releases. Never replace existing historical ZIP bytes or weaken an immutable hash gate just to make CI green.

## Verification and limits
All 195 Node tests and all 17 original file syntax checks passed in the isolated source branch. The direct-main PR must independently pass public-source CI. Earlier 17→0 results apply to PR #71's proposed source state, not to `main`, until successor packages are shipped.

TrapNet independent reviews and general-public release status remain HOLD.