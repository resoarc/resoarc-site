<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->
# REUSE Specification 3.3 / current ResoArc policy

Canonical standard: https://reuse.software/spec/
Pinned tool: `reuse[charset-normalizer]==6.2.0`.
Sources: repository `LICENSES/`, `REUSE.toml`, individual SPDX headers.
The 2026-10-18 local report covered **363/363** files; it is *historical*, not a statement about current HEAD.

## New file handling

1. Identify the creator(s), provenance, and permission for EACH added binary or file.
2. Add a precise `[[annotations]]` declaration to `REUSE.toml` or embed SPDX headers. Never blindly mark new third-party art MIT.
3. Add the complete license text to `LICENSES/<SPDX-ID>.txt` for every actual license and remove unused texts.
4. Run `python -m reuse lint` and `python scripts/reuse_release_gate.py --report <outside-repo-path>`.
5. Inspect release archives independently: their outer metadata does **not** prove all internal files are redistributable. Check `docs/reuse-archive-inventory.json` and `docs/REUSE_LEGAL_REVIEW.json`.

## CI, release gate, failure transparency

- `.github/workflows/reuse-compliance.yml` runs on every push to main, on pull requests, and manually.
- A non-zero REUSE result fails the workflow; generated audit JSON is retained in workflow artifacts; a job summary provides the cause.
- For site or product deployment run `scripts/reuse_release_gate.py` **before** any build or deployment. Never publish a newly added product when this gate fails.
- `/recognition/` shows the latest GitHub workflow state when available: success, failure, pending; date and SHA; links to details.
- `/recognition/reuse-status.json` is a conservative historical fallback, NOT an assurance for the latest commit.
- Branch protection requiring the REUSE check should be enabled on hosting platforms; changing organization-level protection settings is an independent administrative step.

## Rights caveat

REUSE is metadata-completeness verification, not a legal determination. Unsplash photographs, third-party marks, captured third-party UIs, special brand artwork and bundled ZIP licenses require separate review.

## Hosting reality (2026-10-23)
GitHub main and Codeberg main currently diverge; never force-push GitHub merely to activate CI. Codeberg Actions must be enabled in repository Settings > Units > Actions with an available runner. Until verified, the site status reports local test PASS but hosted CI pending. The local release gate fails closed even when hosted CI is unavailable.

## Signed archive release gate (2026-10-23)
All 22 existing signed kintone ZIP wrappers are SHA-256 pinned in docs/reuse-signed-archive-register.json. The scanner inspects outer PUBKEY/SIGNATURE/contents.zip and nested license/SPDX evidence. The gate rejects an unregistered new signed ZIP, a deleted archive, or a changed outer/payload hash. This is not cryptographic signature validation or a legal audit. Existing absent internal notices remain recorded as pending. A separate notice is served at site/downloads/RESOARC_SIGNED_PLUGIN_LICENSE_NOTICE_20261023.md. Actual release approval still requires legal/rights review of new archives.

Codeberg API on 2026-10-23 reports has_actions=false. Repositories need authenticated owner to enable Settings > Units > Overview > Actions, and an available trusted runner, before hosted CI can be reported as operational. Do not enable an unisolated runner on the production VPS, because action jobs can execute arbitrary code.
