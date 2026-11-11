<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->

# OSS Compass registration preparation (2026-11-11)

**Status: PREPARED / NOT SUBMITTED / NO EXTERNAL REPORT.**

Official entrypoint: https://oss-compass.org/submit-your-project  
Official documentation: https://oss-compass.org/docs/quick-start/  
Review queue: https://github.com/oss-compass/compass-projects-information/pulls

Official documentation confirms two registration routes: (1) authenticate with GitHub or Gitee and submit through the website, or (2) fork `oss-compass/compass-projects-information` and open a compliant PR. The project submission creates an external pull request for evaluation. Search of the upstream project-information source did not find a ResoArc-specific report or submitted record on 2026-11-11, so no registration is claimed.

## Minimal factual submission profile

| Field | Content |
| --- | --- |
| Submission type | **Single repository**, not a verified organization/community or ecosystem partnership |
| Repository URL | `https://github.com/resoarc/resoarc-site` |
| Project title | ResoArc |
| Website | `https://resoarc.com/` |
| Description | An independent, free and open-source technology project providing browser utilities, kintone-related tools, and experimental Raspberry Pi/Linux software |
| Public license status | First-party components generally MIT; separately documented third-party license restrictions |
| Public proof | `README.md`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, official REUSE report, OpenSSF Baseline project #15597 |
| Contact/identity | Use ResoArc identity only; do not disclose operator's private credentials or personal identity |

## Registration guardrails

- This GitHub repo is a public mirror; the canonical publication history is also managed through Codeberg and a separate Cloudflare deployment path. OSS Compass statistics on **GitHub** must not be presented as measurements of all ResoArc activity.
- Authenticate using the dedicated ResoArc GitHub account. No machine/session authenticated to OSS Compass was established during this investigation, and the available local `gh` CLI reports **not logged in**. Do not impersonate or reuse personal GitHub accounts.
- After a real submission, save the external PR URL, submission date, decision and any public report URL. Only link a badge if one is actually issued with truthful scope.
- Registration, external acceptance, community membership and independent security certification are different types of evidence.

## Manual completion step still necessary

Visit https://oss-compass.org/submit-your-project, sign in with the dedicated ResoArc GitHub identity, choose **Single repository**, enter `https://github.com/resoarc/resoarc-site`, and submit. Verify the resulting PR appears under the official external queue. If service login is unavailable, arrange a fork + compliant PR with the same ResoArc account.

**Disposition: no submitted application or report as of this record.**
