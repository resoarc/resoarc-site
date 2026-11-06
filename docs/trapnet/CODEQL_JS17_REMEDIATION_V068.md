# ResoArc CodeQL JS/TS v0.68: 17 warning-row remediation

**State:** proposed as a Draft PR. No publication, production deployment or formal release approval.

## Proven baseline

- Exact parent: `4f1d0efd1a1a19baaba606401b9024ff19e6548b`.
- CodeQL original JS/TS scan: [run 42149202966](https://github.com/resoarc/resoarc-site/actions/runs/42149202966), `security-and-quality`.
- The machine-readable SARIF summary reported **17 warning rows** (not a verified number of distinct GitHub Code Scanning alerts).

## Changes and assessment

| Rule | Baseline | Change | Safety / behavior rationale |
| --- | ---: | --- | --- |
| `js/whitespace-contradicts-precedence` | 9 | Parenthesize existing `&&` and `||` retry error handling (Auto Number beta desktop/mobile/runtime), `in` membership (Kanban 3), `?:` and `in` membership (List Search 3) | Existing JavaScript precedence is explicitly preserved. No widening of retry conditions or record access. |
| `js/unused-local-variable` | 5 | Remove unused mobile detection in stable Auto Number 3, unused local in scorecard test, and unused `cpSync` import in progress test | Unreferenced symbols only; Kintone registration remains for desktop and mobile events. |
| `js/bad-tag-filter` | 1 | Replace a narrow negative regex for literal `<script>` with a positive assertion that the malicious image/attribute payload is HTML-escaped | No runtime sanitization logic is weakened; test checks actual escaped user-controlled content. |
| `js/trivial-conditional` | 1 | Remove redundant `!quoted` in the CSV parser's already-unquoted `else` branch | Branch semantics unchanged, all CSV negative tests retained. |
| `js/automatic-semicolon-insertion` | 1 | Add the missing explicit statement terminator to the progress CLI error path | No change in CLI exit code or arguments. |

These code changes do **not** change signed plugin release archives or published downloads. The beta/alpha plugin sources are modified deliberately because the CodeQL results specifically target them.

## Evidence

- All relevant 97 targeted Node tests passed (Auto Number stable/beta, Kanban, List Search, suite, progress).
- All 195 repository `*.test.cjs` / `*.test.mjs` Node tests passed.
- All 17 modified JavaScript/MJS/CJS files passed `node --check`.
- `node scripts/test_scorecard_live.mjs`: PASS.
- `node scripts/kintone-progress.mjs --check`: PASS.
- `git diff --check`: PASS.
- **A fresh CodeQL scan of the updated commit is required before claiming warning closure.** The existing 17-row summary remains historical evidence, not proof that all warnings have disappeared.

## Gate impact

These are automatic CodeQL review findings, not an independent human security review. This change cannot satisfy TrapNet E3 or change the network-wide public release **HOLD**. Keep the linked tracking issue #67 open for independent disposition and any new findings.
