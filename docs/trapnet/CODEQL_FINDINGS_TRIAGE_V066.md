# TrapNet CodeQL v0.66: first evidence-based findings triage

Status: Draft PR only. No authorized general release. Static analysis by GitHub CodeQL is **not** independent human E3 review.

## Exact baseline
- CodeQL workflow: https://github.com/resoarc/resoarc-site/actions/runs/42147439044
- Baseline source SHA: `1777cb0d04b31a57e8e2dc80f042e53ae15122b6`
- Four metadata-only workflow artifacts: `codeql-findings-python`, `codeql-findings-javascript-typescript`, `codeql-findings-go`, `codeql-findings-actions`. Retention 14 days.
- Baseline **64 SARIF result rows** (not necessarily unique repository alerts): Python 47; JavaScript/TypeScript 17; Go 0; GitHub Actions 0. All 4 analysis jobs succeeded.
- All Python findings have SARIF `warning` level: `py/unused-import` 32, `py/empty-except` 5, `py/file-not-closed` 4, `py/overly-permissive-file` 3, `py/uninitialized-local-variable` 1, `py/multiple-definition` 1, `py/mixed-returns` 1.
- JS/TS: `js/whitespace-contradicts-precedence` 9, `js/unused-local-variable` 5, `js/automatic-semicolon-insertion` 1, `js/bad-tag-filter` 1, `js/trivial-conditional` 1. All level `warning`.

## Highest-priority remediation submitted
Three persistent CodeQL warnings from original PR #32 are linked to chmod 0755 on temporary Cowrie image-default **configuration** directories. The files and lines on baseline are:

- `experiments/trapnet-zero-trust/sonar/cowrie_log_pressure.py:80`
- `experiments/trapnet-zero-trust/sonar/cowrie_offline_integration.py:119`
- `experiments/trapnet-zero-trust/sonar/cowrie_recreate_recovery.py:101`

Change each temporary directory after `docker cp` to service UID/GID 999:999 and mode `0700` instead of allowing other users to enumerate it with `0755`. This is a laboratory-only ownership change, not production VPS configuration. The Docker container already runs as UID/GID 999:999, so access to the bind-mounted configuration is preserved while host file enumeration is restricted.

**Accept only after** immutable Cowrie image integration tests and CodeQL report verify real SSH startup, logging, isolation and cleanup; no premature "fixed" label. The code still contains world-readable inherited default files inside private 0700 directories, so the end-to-end access boundary, not the individual file's mode in isolation, matters.

## Triage without noise
- Investigate `py/file-not-closed` at `sonar/cowrie_log_health.py`; that function uses `ExitStack` plus `stack.callback(os.close, fd)` to close pinned descriptors. Treat as *potentially analyzer-limited*, never suppress without testing failure paths.
- Review `py/empty-except` including production-mode repair logging carefully. Suppressing a best-effort logging exception may hide operational evidence.
- Inspect `js/whitespace-contradicts-precedence` after identifying the exact expressions; changing grouping can change plugin behavior. Do not batch edit without focused JS tests.
- Unused imports (32) are a lower priority and can be removed in small tested batches after security and availability controls.
- GitHub Actions and Go 0 results mean no matches under this CodeQL ruleset on the exact commit, not comprehensive safety, nor a formal Gate PASS.

## Gate accounting
A2, D3 and E3 remain their previous formal statuses. No independent human reviewer approved this triage, no production attack evidence was changed, and whole-network public release remains **HOLD**.
