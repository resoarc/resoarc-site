# CodeQL v0.65: metadata-only finding inventory

## Purpose
The expanded CodeQL workflow passed on PR #63, but the owner could not retrieve the alert list from its restricted connector. The workflow now reads each completed CodeQL SARIF file locally and emits a **metadata-only** JSON artifact for each language. This provides real rule/level/location accounting without leaking raw SARIF, code snippets, alert message text or honeypot evidence.

## Safeguards
- Four independent jobs (JS/TS, Python, Go, Actions) each retain a matching scan category.
- SARIF reducer fails closed when there is no SARIF, missing run data or an unexpected schema. Self-tests exercise redaction and negative inputs.
- Public repository-relative paths, bounded line numbers, rule IDs, level and counts are the only finding content emitted.
- Source snippets, finding descriptions, raw SARIF, taint data and attacker-provided strings are never persisted in the evidence artifact.
- Summary artifact is retained for 14 days and is uploaded using a SHA-pinned action with read-only repository permissions and the CodeQL job's existing `security-events:write` requirement.
- The figures are **SARIF result rows, not unique repository code-scanning alerts**. Do not treat findings as vulnerabilities until individually triaged.
- No automatic dismissal, code rewriting, mitigation, git merge, general release approval, or independent human audit is performed by this pipeline.

## Operator triage
After a run, download `codeql-findings-<language>` artifacts from the CodeQL workflow run. Identify highest-severity rules and repeated affected public-source file paths, open corresponding alerts in GitHub Security → Code scanning, and confirm each item's relevant code path and safe reproduction.

Map to issue numbers with fixed commit, rule ID, severity, source path, source line, reviewer identity and disposition. Never use the number of warnings as a standalone release gate.

PR #63 is still a Draft, and deployment/release remains HOLD until actual independent human review and the remaining formal acceptance gates.
