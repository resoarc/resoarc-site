<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->

# Production route and SWWW snapshot preservation audit — 2026-11-12 JST

**Scope:** public GitHub main commit `4738b2b7ed4b318f69168e6b04f54d5df9d5eec0` and publicly served `https://resoarc.com/`. Read-only verification on 2026-11-12 around 00:21–00:27 JST. Production was **not** deployed or modified by this check.

## Public sitemap / HTML parity

- Production `https://resoarc.com/sitemap.xml`: **66** absolute URL entries.
- GitHub main `site/sitemap.xml`: **66** entries.
- Set differences (both ways): **0**.
- Every production sitemap route has a corresponding tracked `site/<route>/index.html` in main: **66 of 66**, missing **0**.
- These are route and file-presence results, **not** evidence that every page's HTML is byte-for-byte identical or that all assets/worker behavior agree.

## Separately updated public SWWW artifacts

Compare the raw GitHub file at the exact commit above against its live public URL using HTTP GET response bytes and SHA-256 (not parsed data):

| Relative URL beneath site/ | Source SHA-256 | Live SHA-256 | Result |
| --- | --- | --- | --- |
| `api/v1/swww/catalog.json` | `a1793070d234ea1ef09a6b461753b9ab8e7f66c8050b6434006a5c7e8a1e6d6b` | same | MATCH |
| `api/v1/swww/advisories.xml` | `92d55149ac92172826e3952bfd34aa10cbf0f5e40ec63b53492ee41dacb3547f` | same | MATCH |
| `security/weather/today.json` | `81ce750759d84b72824bc86309afffefe681db6784a1534a502fd166fbbe8980` | same | MATCH |

These files are also updated by a separate workflow. A full-site Direct Upload can overwrite newer snapshots unless it compares **the actual candidate bytes immediately before deployment** with live bytes.

## Production publishing safety improvement

Port the narrowly scoped `verify_live_data_preservation.py` idea from the older, conflicting [PR #93](https://github.com/resoarc/resoarc-site/pull/93) into current main as a separate, testable change:

1. Check precisely these three public artifacts before deployment; fail closed on missing files, changed hashes, over-size responses, network errors or non-200 responses.
2. Integrate the guard into `scripts/deploy_canonical.ps1` **after** route preservation but **before** `wrangler pages deploy`. The guard never writes files or attempts to publish.
3. Run offline acceptance tests from the GitHub verification workflow.
4. If one of the independent publishers has newer content, synchronize it through an approved, sourced pipeline first. Do not bypass the check by replacing live data with older candidate data.

## Why PR #93 cannot simply merge now

- It was drafted when production contained 54 routes and the older GitHub main had 37. The current public sites have already converged to **66 routes each**.
- At the current GitHub main, a read-only Git three-way merge reports **58 conflicting paths**, including Worker, shared site HTML, downloads, CI and notice files.
- Of its 590 tracked files, only 12 are absent from the current 890-file main snapshot; most of its contents already overlap or have changed further.
- Several of the 12 unique files are historical inventories, one old `_routes.json`, a deleted `downloads/index.html`, and optional extra checks. Carry them over **only after individual review** rather than overwriting newer Worker and releases.
- The real production `/recognition/` page still has older October text and did not show the just-submitted OSS Compass PR #11638 at the check time, so site content synchronization remains unfinished.

## Unverified deployment gates

- Whether all 66 live HTML documents and every linked asset are still equivalent to current main.
- Whether the current Cloudflare Pages Worker routes, bindings, download integrity and provenance match the candidate, including immutable ZIP files and independent service endpoints.
- Whether current main is the intended publishing source relative to Codeberg and other deploy worktrees.
- Whether authentic deployment credentials and a complete guarded dry-run are available.

**Decision: route parity achieved, 3/3 SWWW snapshot byte matches, but NO full-site deployment authorized by this audit alone.**
