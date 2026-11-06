# OSPS-LE-02.02: released software licenses, evidence for 35 ZIP assets

**Date:** 2026-11-06 (JST).  
**Scope:** The 35 public ZIP releases listed at [https://resoarc.com/downloads/](https://resoarc.com/downloads/) and pinned in [the release manifest](OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json).

## Exact requirement

In [OpenSSF OSPS Baseline v2026.08.28](https://baseline.openssf.org/versions/2026-08-28), **LE-02.02** requires that the licenses for released **software** assets meet the OSI Open Source Definition or FSF Free Software Definition. This is a **license selection and license identity requirement**. It does not say that a professional legal opinion or independent copyright audit must be obtained as a separate mandatory criterion. Of course, the license can be validly granted only by an authorized copyright holder, and unsupported legal claims must not be made.

## License classification by public release

- **Primary license for released ResoArc software:** **MIT**, a recognized OSI open-source software license. This is the *existing published license assertion*, not a newly invented grant or a claim of third-party approval.
- **13/13 source and other ZIP archives** contain the complete MIT software license in a root or nested LICENSE file. The embedded path and SHA-256 are recorded for each archive.
- **22/22 signed kintone plugin ZIPs** are distributed *unchanged*. Their chosen ResoArc MIT license is supplied as a versioned, byte-verified companion at `/downloads/LICENSE`; the corresponding per-asset catalog provides the link. The signatures were not modified.
- **QR Code mobile plugin:** `contents.zip/js/qr-lib.js` includes the Kazuhiko Arase copyright and full MIT and Apache 2.0 texts. These are both accepted open-source software licenses. The upstream author text has not been erased.
- **Backup & Migration:** the shipped fflate 0.8.3 runtime library retains its MIT license file and notice. esbuild, also MIT, is a source-build tool rather than an additional runtime in that ZIP.
- **Noto Serif JP (OFL-1.1)** and **Unsplash media** in a recovered site source snapshot are **font/image materials**, not a competing or restrictive software license applied to ResoArc's code. They are disclosed separately. The Unsplash License is **not** characterized as OSI-approved software licensing; independent asset use and redistribution rights still warrant review.

[The machine-verifiable 35-row license matrix](OSPS_LE02_35_SOFTWARE_LICENSE_EVIDENCE_20261106.json) records each release hash, the full MIT document's location (embedded vs separate companion), hashes of the MIT license documents, applicable third-party software licenses and exceptions. A committed [CI validation script](../../scripts/check_osps_le02_35_osi_licenses.py) checks that every release has a documented approved software license and that unverified legal signoff flags remain explicitly false.

### Public distribution

- [ResoArc public 35-asset download and license catalog](https://resoarc.com/downloads/)
- [MIT license text](https://resoarc.com/downloads/LICENSE)
- [Release NOTICE](https://resoarc.com/downloads/NOTICE.md)
- [Third-party legal notices](https://resoarc.com/downloads/THIRD_PARTY_LICENSES.md)

The 35 ZIPs were checked on all three public domains for **105/105 SHA-256 and byte-count matches**, and the associated LICENSE/NOTICE paths were previously checked **6/6**. These observations support LE-03.02 as well as the reliable identity of the assets assessed here.

### Separate rights/provenance questions (not falsely presented as satisfied)

The [source-to-signed-payload technical review](OSPS_LE02_LICENSE_CLEARANCE_REPORT_20261106.md) confirms public Git, historic QA and published-source-archive matches for some signed payloads. The historical chain of the remaining signed variants and the copyright holder's authority to grant MIT have **not been independently adjudicated**. The formal approval record for eight releases is an approval *to publish*, not a legal ruling. A previous QA-only manifest had `rightsApproved: false`. These factual caveats remain visible in [issue #79](https://github.com/resoarc/resoarc-site/issues/79) and [the unsigned owner rights template](OSPS_LE02_OWNER_RIGHTS_APPROVAL_TEMPLATE.md).

**Scope boundary:** demonstrating that the *named software licenses* meet OSI/FSF definitions is distinct from proving undisputed title to every line of software; neither this report nor OpenSSF self-evaluation is an independent legal certification. If the operator identifies an unlicensed component or lacks the right to distribute it, the release must be corrected or withheld and LE-02.02 re-evaluated.

**Self-assessment interpretation:** the objective part of the LE-02.02 license-choice requirement is supported by the public MIT and Apache 2.0 evidence for the current 35 software releases. Before reporting a definitive status externally, the project's accountable operator must ensure its existing copyright/license declaration is authorized and not contradicted by any outstanding actual rights claim. A request to improve compliance is not, by itself, such an attestation.
