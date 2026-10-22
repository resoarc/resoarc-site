# Third-party notices (QA v0.6)

This is a local-only development preview. It has NOT passed a complete production distribution license or SBOM audit. The following direct runtime dependencies were identified from the installed package manifests on 2026-10-21.

| Package | Version | Package license | Source |
| --- | --- | --- | --- |
| @fortune-sheet/react | 1.0.4 | MIT | https://github.com/ruilisi/fortune-sheet |
| @corbe30/fortune-excel | 2.3.4 | MIT | https://github.com/Corbe30/FortuneExcel |
| jszip | 3.10.1 | MIT OR GPL-3.0-or-later (MIT option selected) | https://github.com/Stuk/jszip |
| @xmldom/xmldom | 0.9.12 | MIT | https://github.com/xmldom/xmldom |
| react | 18.3.1 | MIT | https://github.com/facebook/react |
| react-dom | 18.3.1 | MIT | https://github.com/facebook/react |

The development-only browser test runner uses playwright-core 1.64.1 (Apache-2.0); the development-only toolchain includes Vite. Their source distributions are not packaged with the static offline preview.

Several transitive runtime packages are included within the built JavaScript bundle and MUST be inventoried before any public redistribution. The React, FortuneExcel and JSZip license texts are included in the development environment in `node_modules`. FortuneSheet's npm runtime package declares MIT but does not contain a standalone LICENSE file in this installation; obtain the official notice and attribution from the upstream repository before general release.

**Release gate:** Include all required license texts, copyright holders, transitive dependency notices and a software bill of materials (SBOM) before public distribution. Do not treat this preliminary notice as complete compliance approval.