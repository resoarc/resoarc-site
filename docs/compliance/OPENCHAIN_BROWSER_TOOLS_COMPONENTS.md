# Initial component inventory: two browser-only utilities

**Snapshot:** 2026-11-06. **Review status: PROVISIONAL, not a verified SBOM.**

The source files, HTML delivery entrypoints and directly referenced local assets were inspected from public GitHub `main` using repository file reads. This is a provisional mapping; in particular, external font/photo provenance and published live bytes must be independently verified.

| In-scope file / component | Provisional rights | Observed usage | Remaining proof |
| --- | --- | --- | --- |
| `site/assets/tools/hash.js` | ResoArc MIT | Browser SHA-256 utility; no observed import/require or external URL in JS | License header verified, run release revision/hash and full runtime inspection |
| `site/assets/tools/csv.js` | ResoArc MIT | Browser CSV/TSV checker; no observed import/require or external URL in JS | License header verified, run source review and tests |
| `site/tools/hash/index.html`, `site/tools/csv/index.html` | ResoArc MIT for original content | Direct scripts and asset links | Preserve exact release and attribution |
| `site/assets/site-20261015-v10.css` | First-party portion MIT; embedded font references have separate license | Both HTML pages load the CSS | Review all CSS imports/font/asset references, hash source and deployment |
| `site/assets/recognition-20261017.css` | Provisional ResoArc MIT | Both tool pages load it | Verify third-party assets and hash |
| `site/assets/resoarc-icon.svg` and tool-specific `site/assets/tool-icons/{hash,csv}.svg` | Provisional ResoArc MIT | HTML icons/images | Check original ownership/embedded assets |
| `site/assets/tool-screens/{hash,csv}.webp` | Provisional first-party screenshots | Tool pages present images | Confirm image provenance and distribution permissions |
| `site/assets/fonts/noto-serif-jp-v10.woff2` | SIL Open Font License 1.1 | Referenced by shared CSS | Confirm exact original subset, include OFL full text and notices for actual recipients |
| `site/assets/hero-architecture.jpg` | Unsplash License, **not** MIT | Open Graph reference on tool pages | Confirm original photo attribution and allowed use; cannot relicense under MIT |
| `site/licenses/RESOARC-MIT.txt`, `site/licenses/NOTOSERIFJP-OFL.txt` | Respective full license texts | Repository includes license URLs | Confirm links visible to actual users |
| Browser Web Crypto / File APIs | Platform interfaces, not bundled OSS dependencies | Native browser calls | No external package dependency detected in JS text, but not a complete dependency scan |

**Important boundary:** source code search for `import` and `require` and absence of outbound URLs in the two JavaScript files are narrow observations, not a comprehensive SCA/security audit. Fonts and photographs stay in scope because the public HTML/CSS references them. A full SPDX/CycloneDX SBOM and evidence of compliance artifact delivery are outstanding.
