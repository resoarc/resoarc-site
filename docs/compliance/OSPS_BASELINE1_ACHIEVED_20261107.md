# ResoArc OpenSSF Baseline Level 1: 100% self-assessed and badge awarded

**Official issuer record:** [OpenSSF project #15597, Baseline Level 1](https://www.bestpractices.dev/projects/15597/baseline-1).  
**Recorded achievement:** `2026-11-06T15:59:05.301Z` (2026-11-07 00:59:05 JST).  
**Official issuer API after submission:** `badge_percentage_baseline_1 = 100`, `OSPS-LE-02.02_status = Met`, `OSPS-LE-03.02_status = Met`, and non-empty `achieved_baseline_1_at`.  
**Result:** 24 of 24 Level 1 controls assessed Met.

**Important meaning:** this is a **voluntary, evidence-backed self-assessment badge** for the requirements of the [OSPS Baseline current v2026.08.28](https://baseline.openssf.org/versions/2026-08-28). It is not an externally performed security audit, a legal opinion, an OpenSSF corporate partnership or a guarantee that every component is vulnerability-free.

## Closure of the final license selection and delivery controls

**OSPS-LE-02.02 — released software assets have OSI/FSF-compatible licenses**

1. ResoArc's 35 public software distribution ZIPs use the project-declared **MIT** software license. **13 source/other archives** embed the complete MIT text; **22 signed plugin ZIPs** preserve existing signatures and offer the same primary MIT text as the companion `/downloads/LICENSE` alongside the released files.
2. **Third-party software:** QR Code Generator retains original Kazuhiko Arase's MIT and Apache-2.0 text; Backup & Migration includes fflate 0.8.3 MIT and its upstream notice; esbuild is an MIT build-time dependency only. Upstream fflate and QR MIT texts were compared with their respective published GitHub LICENSE files, and the complete license text matched after whitespace normalization.
3. **Not software-license substitutions:** Noto Serif JP font has OFL-1.1 and the site photograph has Unsplash media conditions, each disclosed separately without claiming these images are ResoArc MIT code.
4. On 2026-11-07, the responsible ResoArc operator explicitly confirmed that the project-original code was developed personally with AI and **without copying code from an employer or clients**. This statement is scoped to operator-owned development; it is not an independent copyright opinion or an assertion of exclusive rights to every automatically generated code fragment.
5. A reproducible [public release content scanner](../../scripts/audit_osps_35_release_license_content.py) verified **35 ZIPs, 22 signed payloads, full MIT texts in 13 source archives, 681 readable code/text members, and zero explicit restrictive software-license phrase matches**. A static scan cannot prove that no uncredited third-party expression has ever been included. Future rights claims or newly discovered dependencies must be reviewed and remediated.

**OSPS-LE-03.02 — licensed release distribution**

- [35-asset catalog](https://resoarc.com/downloads/) offers every release with legal-document links.
- Public HTTP verification confirmed **105/105** exact ZIP hashes and sizes (35 products x 3 official domains), plus **6/6** matching LICENSE/NOTICE companions.
- The 22 signed plugin ZIP bytes and signatures were preserved; code and license contents were not silently replaced.

## Auditable project records

- [35-asset release inventory](OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json)
- [OSI software-license evidence for each ZIP](OSPS_LE02_35_SOFTWARE_LICENSE_EVIDENCE_20261106.json)
- [Dated operator declaration, AI limitations and upstream checks](OSPS_LE02_OWNER_DECLARATION_AND_REVIEW_20261107.md)
- [Source and signed-release provenance analysis](OSPS_LE02_LICENSE_CLEARANCE_REPORT_20261106.md)
- [Published software license catalog](../../site/downloads/index.html)
- [PR #81 implementing the checks and documentation](https://github.com/resoarc/resoarc-site/pull/81), merged after Verify, REUSE and CodeQL passed
- [Technical source/release provenance follow-up #79](https://github.com/resoarc/resoarc-site/issues/79)

## Continuing obligations

This badge represents compliance **as self-assessed at that point in time**, not permanent immunity from flaws or an independent audit. If any actual permission issue, source attribution defect or new release license incompatibility is found, the project must correct or withdraw the affected release, preserve evidence, and re-evaluate the self-assessment. The owner should continue working on the older signed plugin provenance tracked in #79 without falsely treating reconstructed source archives as historical Git commits.

**Responsible disclosure principle:** do not publish personal account identities, signing keys, unrelated development files, or client information in support of the badge. Reviewers can inspect published hashes, MIT and third-party notices, upstream terms and the official issuer record.
