# ResoArc downloadable software: license and attribution index

**Status:** licensing information companion for public download assets, not proof of all release obligations.

Every ResoArc-authored source file in the corresponding published source tree is generally offered under the [MIT License](LICENSE) (copyright 2026 ResoArc Open Technology Project), subject to the terms and notices actually included with the corresponding product. **Third-party material is not re-licensed by ResoArc.**

- [Full first-party MIT license](LICENSE)
- [Public source repository and exact change history](https://github.com/resoarc/resoarc-site)
- [Third-party material and applicable licenses](https://github.com/resoarc/resoarc-site/blob/main/THIRD_PARTY_NOTICES.md)
- [REUSE/ machine-readable license metadata](https://github.com/resoarc/resoarc-site/blob/main/REUSE.toml)
- [Security and vulnerability reporting](https://github.com/resoarc/resoarc-site/blob/main/SECURITY.md)

## Signed kintone installer packages

Some `*.zip` files in this folder are already **signed installation packages**, containing `contents.zip`, `PUBKEY` and `SIGNATURE`, but **not embedded license text**. Their bytes must not be changed without an authorized re-build and re-sign. Keep this license and the relevant source/release notices alongside any redistributed package, and check the corresponding product-specific source and license before reuse.

**A standalone download of a signed ZIP does not automatically include this notice.** This companion file is an interim remediation only. Individual product download links must clearly provide the same license/notice material, or verified distribution bundles must be provided before claiming that every user has received the required documents. Do not assert OpenSSF OSPS-LE-03.02 is complete based on this file alone.

## Rights and packaging cautions

The main website uses separate Noto Serif JP / OFL 1.1 font material and an Unsplash image with distinct licensing conditions. Product-specific third-party libraries, notices and source-offer obligations, if any, require additional examination. Release-by-release review is required, including nested ZIPs, upstream authorship, fonts, images, scripts and binary metadata. This document is not a warranty or independent certification.

**Audit reference:** `docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.md` (snapshot date and gaps).
