# OSPS Baseline Level 1 workflow controls

**Reviewed:** 2026-11-06. **Scope:** ten tracked GitHub Actions workflows, tracked source and the textual contents of distribution archives.

### BR-01.01: Validate external CI inputs

`scripts/check_workflow_security.py` rejects use of `pull_request_target` or `workflow_run` triggers, direct shell interpolation of common untrusted GitHub event fields, unpinned third-party actions, and broad write tokens. It runs within the protected, required `verify` workflow.

### BR-01.03: Prevent secret access from untrusted PR code

The general PR verification job has `permissions: contents: read` and disables checkout credential persistence. The secret-consuming OpenSSF assessor uses only the trusted schedule/manual triggers. ResoArcOS publication jobs are separately scheduled by manual dispatch and explicitly check the canonical repository identity before granting write permissions. Do not claim these static checks establish protection on uninspected external environments.

### BR-07.01: Stop accidental committed secrets

`scripts/check_repository_secrets.py` checks tracked filenames, text files, and textual entries of known distribution ZIPs for common credential patterns and private-key delimiters. It never prints secret contents. Its initial local execution found **zero findings across 372 tracked paths**. Branch protection requiring `verify` ensures these checks must pass before changes can be merged.

The scanner is defense in depth, not proof that past commit history or all cloud credentials are safe. Enable and separately verify GitHub-native push protection where available; immediately revoke genuine leaked secrets.

### Evidence boundaries

This is a project-controlled automated security control, **not** an independent code audit or a zero-risk guarantee. Each change remains subject to actual GitHub Actions runs, and the owner must not bypass required checks. For external best practices see https://docs.github.com/en/actions/concepts/security/script-injections.
