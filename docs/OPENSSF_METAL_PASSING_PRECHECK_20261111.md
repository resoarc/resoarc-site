<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->

# OpenSSF Metal Passing — evidence-first precheck (2026-11-11)

**Official project:** https://www.bestpractices.dev/projects/15597  
**Source of status:** https://www.bestpractices.dev/projects/15597.json

The issuer's public JSON on 2026-11-11 reports `badge_percentage_baseline_1: 100`, `achieved_baseline_1_at: 2026-11-06T15:59:05.301Z`, **Metal `badge_percentage_0: 0`**, `badge_level: in_progress`, and no `achieved_passing_at`. Most Metal `*_status` fields are **`?` (unanswered)**. This does **not** mean all the underlying controls failed; the formal questionnaire has not been filled out.

The Metal series is separate from the OpenSSF Baseline series. An earned Baseline Level 1 badge is not a Metal Passing badge. The project maintainer must review and submit honest responses through the issuer account; this document is **not** an issuer submission.

## Evidence already available for *candidate* Metal answers

| Issuer field (candidate only) | Public evidence | What to verify before answering |
| --- | --- | --- |
| `description_good_status`, `homepage_url_status` | [README](../README.md), [website](https://resoarc.com) | Wording and current products correspond to what is actually shipped |
| `sites_https_status` | [official site](https://resoarc.com/) | All official download and development entrypoints support HTTPS |
| `interact_status`, `contribution_status` | [Issues](https://github.com/resoarc/resoarc-site/issues), [CONTRIBUTING](../CONTRIBUTING.md) | Feedback links truly work and external participants can report issues |
| `floss_license_status`, `floss_license_osi_status` | [LICENSE](../LICENSE), [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md), [REUSE external report](https://api.reuse.software/info/github.com/resoarc/resoarc-site) | Distinguish first-party MIT from third-party assets; correct actual distribution scope |
| `repo_public_status`, `repo_track_status`, `repo_interim_status` | [public Git commits](https://github.com/resoarc/resoarc-site/commits/main), [pull requests](https://github.com/resoarc/resoarc-site/pulls) | GitHub/Codeberg source authority and real review process |
| `test_status`, `test_invocation_status` | [VERIFICATION](VERIFICATION.md), [GitHub workflow](https://github.com/resoarc/resoarc-site/actions/workflows/verify.yml) | Re-run tests on the exact reviewed source; document how others reproduce |
| `static_analysis_status` | [CodeQL](https://github.com/resoarc/resoarc-site/actions/workflows/codeql.yml) | Scan scope, supported languages and currently passing results |
| `vulnerability_report_process_status`, `vulnerability_report_private_status` | [SECURITY](../SECURITY.md) | Independently test private mailbox receipt; do not promise untested response time |
| `report_tracker_status`, `report_url_status` | [issue tracker](https://github.com/resoarc/resoarc-site/issues) | Visibility, durable history, and response/triage responsibilities |
| `release_notes_status`, `version_tags_status` | [releases](https://github.com/resoarc/resoarc-site/releases) | Verify actual versioning, changelogs, release provenance for each scoped product |

## NOT ready to mark Met without further evidence

- `test_most_status`, `test_continuous_integration_status`, `dynamic_analysis_status` and coverage claims require actual scoped run histories and a measurable definition of tests.
- `warnings_fixed_status`, `vulnerabilities_fixed_60_days_status`, `vulnerabilities_critical_fixed_status` require dated issue/response proof rather than written policy alone.
- `delivery_unsigned_status` and cryptography-specific controls depend on exact distributed products and cannot be inferred from HTTPS or REUSE.
- `build_reproducible_status`, secure release provenance and source-tree correspondence are still constrained by [production drift](LIVE_SITE_RECONCILIATION_20261108.md).
- Questions requiring assigned personnel, separation of duties or actual response operations must not treat AI personas as separate human maintainers.

## Next action by authorized project account

Log in to the **existing** project #15597 under the ResoArc owner identity, review each Metal criterion, submit only evidence-backed `Met` / legitimate `N/A` / `Unmet`. Keep a dated copy of the resulting issuer JSON. **Do not create a duplicate project.**

**Disposition: evidence mapping prepared; issuer Metal questionnaire unsubmitted, 0% shown officially; no Passing badge claim.**
