<!--
SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
SPDX-License-Identifier: MIT
-->

# OpenChain narrowly-scoped production/source delivery comparison — 2026-11-11 JST

**Finding:** 5 of 7 files were byte-for-byte identical between GitHub public `main` source and production `https://resoarc.com/`. The two HTML entrypoints **differ**, so this is **not** a full source-to-live mapping and is **not** ISO/IEC 5230 self-conformance.

This is a bounded **read-only** verification of the SHA-256 and CSV/TSV utilities, not all deployed dependencies or source archives. Production is Cloudflare Pages Direct Upload; a GitHub commit does not deploy automatically. Source URLs are `https://raw.githubusercontent.com/resoarc/resoarc-site/main/site/<path>` and live URLs are `https://resoarc.com/<path>` (HTML entrypoints use the trailing-slash route). An authorized ResoArc workstation fetched exact response bodies to temporary files, compared SHA-256, and deleted the temporary files. The result records the public default-branch bytes **at fetch time**; it does not bind an immutable commit to every source response.

| File / comparison | GitHub source SHA-256 | Production SHA-256 | Equal? |
| --- | --- | --- | --- |
| `site/tools/hash/index.html` vs `/tools/hash/` | `c0b651de86944248266b7383132adb14b655ee9848849eb5dbdcd32096cb9acc` | `fcb3e1930ab37a16f661cd8a2763e2329cc159af6ec7ef30d7978b0d26b12674` | **NO** |
| `site/tools/csv/index.html` vs `/tools/csv/` | `148cd656b5375af2f29c431f5a793cb3ec684caac9b739611a309b946b6f47cb` | `def3d4834f7f52aa58e912d2042c88ab7ae5fe2e72f7d82c9e431b66f52a0f5d` | **NO** |
| `site/assets/tools/hash.js` | `1f7e19217cdfe9817f580b0efe946261511f0964ebab06c489e00a0f6689789a` | same | YES |
| `site/assets/tools/csv.js` | `dfe2dc43016ef84dce26018dadddbb2d6b863d858733ca9eccf18e8b7e90125e` | same | YES |
| `site/assets/site-20261015-v10.css` | `d258b3b68aff6d025ad23cb41d185d1393563231334bd02fe212be73fcfdbb21` | same | YES |
| `site/licenses/RESOARC-MIT.txt` | `4b1d5c0298f3626bb3639997084b30818fa13222be2a216c22bb91aa0c834b89` | same | YES |
| `site/licenses/NOTOSERIFJP-OFL.txt` | `5e0da210fb04058a8c0087985d2d456b931c2579811a49655721d3cf0c36b6` | same | YES |

## Important limitations and decisions

- **Confirmed:** identical public bytes for the two main JS files, shared CSS and two license texts on the specific date/time.
- **Unresolved:** both HTML documents differ from current GitHub public main. Investigate whether differences reflect intended newer production content, changed dependencies or stale mirror state. **Do not overwrite production HTML with GitHub copies just to make hashes equal.**
- **Not examined in this check:** all other referenced CSS/JS, image and font assets, rights provenance, cache variants, browser-served transfer semantics, release source provenance and effective user-facing delivery of license notices.
- The existing provisional CycloneDX snapshot `OPENCHAIN_BROWSER_TOOLS_20261106.cdx.json` has older source hashes for some pages and stylesheets; **refresh it only after selecting a verified canonical release revision**, preserving the original as an historical snapshot.
- The REUSE audit and identical license text show delivery properties, not complete legal clearance or competence of the actual license reviewer.

## Next release evidence gate

1. Identify exact GitHub and Codeberg commits corresponding to the **currently delivered** HTML plus all transitive static assets; compare the diff and preserve all newer production routes.
2. Freeze a designated source tree and an actual published release for the two scoped browser tools, then regenerate and validate a **new** CycloneDX SBOM against that exact tree.
3. Verify every required user-facing rights notice is reachable **from the download/usage flow**; retain the signed-off review record and actual response/hash evidence.
4. Complete policy awareness, assigned human responsibility, competent legal escalation and issue intake; only then consider formal OpenChain ISO/IEC 5230 self-declaration.

**Disposition: PARTIAL / NO CONFORMANCE CLAIM.** See [evidence register](OPENCHAIN_ISO5230_EVIDENCE_REGISTER.md) and [source drift analysis](../LIVE_SITE_RECONCILIATION_20261108.md).
