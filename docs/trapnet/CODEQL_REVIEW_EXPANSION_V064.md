# TrapNet / ResoArc CodeQL coverage expansion v0.64

Status: proposed via Draft PR. No changes to `main`, no public release authorization.

## Gap found in the previous workflow

The original GitHub CodeQL workflow scans JavaScript/TypeScript and Python with `security-extended` against PRs targeting `main` only. It does not currently analyze TrapNet's Go implementation, the repository's GitHub Actions YAML, or stacked Draft PRs targeting another development branch.

## Changes proposed

| Check | Before | Proposed |
| --- | --- | --- |
| Languages | JavaScript/TypeScript, Python | + Go, GitHub Actions (4 independent jobs) |
| Query coverage | `security-extended` | `security-and-quality` for each language, superset of current rules |
| PR targets | Only `main` | All target branches, including chained Draft PRs |
| Scheduled scan | Monday | Monday and Thursday, 03:27 UTC |
| Operator-triggered run | No | `workflow_dispatch` (available from default branch after merge) |
| Go extraction | Not analyzed | Pinned Go toolchain, manual `go build ./...` in `experiments/trapnet-zero-trust` |

The workflow retains minimum job permissions (only `security-events: write` where required) and pinned checkout / CodeQL Action SHAs. Go setup uses a pinned third-party action commit. No forked PR is granted secrets or privileged execution.

## Verification before accepting

1. All **four** language-specific CodeQL jobs must finish successfully on the exact PR commit SHA. Confirm each language reports a completed scan, not just successful workflow setup.
2. Triage alert **rule ID, affected path, severity, reproducible evidence**. Assign status `real`, `false-positive` or `needs-investigation`; never count a reported finding as independently validated solely because CodeQL emitted it.
3. For Go, confirm that the manually built nested Go module covered the actual TrapNet files. Check the extraction log and analysis diagnostics for partial coverage.
4. For Actions, examine permission elevation, untrusted workflow inputs, pinned actions, artifact and cache poisoning, not simply YAML validity.
5. Preserve the three historical automated CodeQL file-mode warnings on PR #32 for comparison; they were not proof of human approval or proof the same issue still exists in the current branch.
6. Keep new findings and CI logs free of private Sensor/HUB signing keys, honeypot raw logs or network access credentials.

GitHub `CodeQL` automated analysis is valuable, but **it does not fulfill the independent human security review E3**, nor change A2/D3 or any general release HOLD gate. The number of findings may increase because `security-and-quality` intentionally contains more lower-confidence and code-quality rules.

Resources: GitHub official CodeQL query-suite reference and advanced setup documentation.
