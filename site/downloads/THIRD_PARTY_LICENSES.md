# ResoArc: public-download third-party license notes

This release directory offers a first-party MIT LICENSE and NOTICE alongside all 35 downloadable ZIPs. This is documentary evidence of the distribution mechanism, not independent legal sign-off.

* ResoArc-authored implementation: MIT, copyright 2026 ResoArc Open Technology Project, full text at /downloads/LICENSE.
* QR-code mobile plugin: the signed contents.zip/js/qr-lib.js includes Kazuhiko Arase's 2009 MIT copyright notice, the full MIT terms, and a full Apache License 2.0 notice. Keep both original texts; upstream QR implementation: https://github.com/kazuhikoarase/qrcode-generator/blob/master/LICENSE.
* Backup & Migration 1.0.0: includes fflate 0.8.3 (Arjun Barrett, MIT) at LICENSES/fflate-MIT.txt, with additional notices in bundled JavaScript. esbuild 0.25.12 (Evan Wallace, MIT) is a build-only tool and is not the shipped runtime. Upstream: https://github.com/101arrowz/fflate/blob/master/LICENSE and https://github.com/evanw/esbuild.
* Recovered site source archive: Noto Serif JP font (SIL OFL 1.1) and an Unsplash-licensed photograph are separately licensed media, not re-licensed under ResoArc's MIT declaration. See the embedded THIRD_PARTY_NOTICES.md.

The signed plugin ZIP bytes have not been rewritten and have no separate LICENSE entry inside the signed container: anyone redistributing one must also include the corresponding LICENSE and NOTICE files. Publicly accessible distribution assets do not by themselves prove ownership of every line of code. Ten mobile signed plugin versions have no byte-for-byte source-file match in the audited public Codeberg Git tree, and four older plugin versions have only partial matches; maintainer rights/provenance verification remains required.