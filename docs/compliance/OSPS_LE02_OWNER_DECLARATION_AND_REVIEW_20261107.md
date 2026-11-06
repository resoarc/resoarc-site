# OSPS-LE-02.02 owner statement and release-license review

**Recorded:** 2026-11-07 (JST).  
**Project:** ResoArc (anonymous open-source project).  
**Scope:** Exactly 35 release ZIPs and their SHA-256 fingerprints, as published in [the frozen 35-asset evidence](OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json).  
**Purpose:** Evidence for a **voluntary OpenSSF Baseline Level 1 self-assessment**, not a third-party security or legal certification.

## 1. Operator's direct declaration

On 2026-11-07 JST, the person responsible for ResoArc stated in the project discussion:

> The project's original software was created as a personal project by the operator, using AI assistance. No code from the operator's employer or clients was reused.

This describes the **original ResoArc-authored portions**, not the separately documented third-party dependencies. The operator also accepted primary responsibility for the project's releases. The operator has not represented that an AI is a human co-author, that every AI-generated expression necessarily attracts copyright, or that the declaration alone constitutes an independent copyright audit. The operator's legal name, employer details, and private project chat are intentionally **not** published.

## 2. Verified released software licenses (LE-02.02)

[Exact public license selection matrix for all 35 releases](OSPS_LE02_35_SOFTWARE_LICENSE_EVIDENCE_20261106.json), verified by [mandatory CI](../../scripts/check_osps_le02_35_osi_licenses.py):

| Release class | Count | Observed software license and delivery |
| --- | ---: | --- |
| ResoArc source/other ZIPs | 13 | Full primary **MIT** license text embedded in each ZIP |
| Signed kintone plugin ZIPs | 22 | Released ZIP bytes and signature unchanged; primary **MIT** license provided beside each artifact at `/downloads/LICENSE`, with direct links in the 35-asset catalog |
| QR Code plugin external library | 1 dependency, included in the above | Kazuhiko Arase upstream **MIT and Apache-2.0** copyright/license texts retained in `contents.zip/js/qr-lib.js` |
| Backup & Migration external library | 1 dependency, included in the above | `fflate 0.8.3` **MIT** and author notice retained in `LICENSES/fflate-MIT.txt` and original source |
| esbuild build system | build-time only | esbuild **MIT**; not an additional bundled runtime file |

The original **fflate MIT text** was compared directly against `101arrowz/fflate` upstream `LICENSE` (Git blob `bd36874f34b9ae537f2bbc383fdf6e320dfafe98`) and matched in full after whitespace normalization. The QR plugin's full **upstream MIT text** matched `kazuhikoarase/qrcode-generator` upstream `LICENSE` (Git blob `150770c0fc2994865ccdbef6662735cc083e780d`) after whitespace normalization. The QR release also visibly contains Apache License 2.0 terms; this is a record of software-license evidence, not a claim that independent upstream authorization was obtained.

A scan over **645 readable code/text members** across all 35 ZIPs looked for third-party copyright names, SPDX declarations, imports and common external CDN URLs. The known third-party copyright cases were recognized. No conflicting explicit proprietary software-license statement was discovered in the reviewed readable members. This is a **bounded static scan**; it cannot rule out every uncredited code fragment, nor establish training-data provenance of AI models.

The source-recovered website ZIP also contains **Noto Serif JP font** under **OFL-1.1** (OSI-approved font license, distributed with notices) and an **Unsplash** photograph under the separate Unsplash media license. The photograph is **not falsely described as OSI-licensed software**. These media do not replace or restrict the MIT grant for the original software code. The usual third-party distribution conditions remain applicable.

The [OSI list](https://opensource.org/licenses) recognizes MIT and Apache-2.0 as open-source licenses, and [OFL-1.1](https://opensource.org/license/OFL-1.1) is an approved open-font license. [Unsplash's license](https://unsplash.com/license) separately permits ordinary use and redistribution but has restrictions, so it is not treated as an MIT software component.

## 3. Public release distribution and reproducibility (LE-03.02)

The repeatable `python scripts/verify_osps_35_license_delivery.py --live` check passed **105/105** public ZIP SHA-256/size checks (35 ZIPs x 3 official hostnames) and **6/6** LICENSE/NOTICE integrity checks. [The public directory](https://resoarc.com/downloads/) links each exact archive to its corresponding legal documents. No signed installer was silently rebuilt, re-signed or replaced.

The mandatory repository CI separately checks all 35 license classifications, the presence of companion license links, and the source-to-signed-payload inventory. Verify/REUSE/CodeQL have been run on previous license-audit PRs and must pass again before this statement reaches main.

## 4. AI collaboration and contributions

The operator directed the project's development using AI. Human direction, review, selection, integration and release decisions are documented by the project work and Git history. AI assistance **does not prove originality** or itself establish copyright ownership over any given generated fragment. The published licenses and above third-party notices are based on the existing project declaration and inspected released materials. A historical source snapshot may be a reconstructed artifact rather than the original authoring history; such a snapshot must not be misrepresented as original git provenance.

Two non-brand author metadata entries in the Codeberg repository were reviewed and affected site documentation; the presence of an author string does not prove a third-party contribution or copyright assignment. Identity linking is kept private for ResoArc's anonymity. No additional human code contributor has been represented by the operator.

## 5. Decision and limits

- **Verified:** The *named licenses applied to all 35 released software assets* are MIT, with QR's MIT/Apache-2.0 and fflate's MIT disclosures, satisfying the **license-selection condition** in [OSPS Baseline v2026.08.28 LE-02.02](https://baseline.openssf.org/versions/2026-08-28).
- **Operator statement recorded:** The project-original code was made personally with AI help, without copying employer or client code.
- **Not claimed:** A lawyer's opinion, independent certification of every author's copyright, a universal scan of outside repositories for all possible uncredited similarity, exclusive ownership of all AI output, or a historical Git reconstruction for the 10 mobile signed releases lacking a public exact-match source ZIP.
- **Continuing process:** Keep [Issue #79](https://github.com/resoarc/resoarc-site/issues/79) open for improving source/build provenance, third-party rights checks, and any new upstream notices. Any concrete discovered rights defect triggers release correction or withdrawal and reassessment.
- **Assessment:** This package supports the project's honest **self-assessment of the license-choice control LE-02.02**. Passing it does **not** transform the voluntary self-assessment into an independent audit.

**Control boundary:** LE-02.02 asks whether *the licenses of released software assets* meet the OSI or FSF definition. It does not require a legal opinion or a perfect copyright chain as an express independent criterion. This distinction must not be used to ignore an actual infringement claim or a missing obligatory third-party notice.
