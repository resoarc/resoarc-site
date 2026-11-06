# ResoArc direct language dependencies

**OSPS-QA-02.01, reviewed 2026-11-06.** This is not a complete system package inventory or an independently audited SBOM.

Nine directly tracked JavaScript package manifests were found, each declaring **zero runtime dependencies and zero development dependencies**:

| Package | Source manifest |
| --- | --- |
| Stable auto-number | `plugins/auto-number/package.json` |
| Beta auto-number | `plugins/auto-number/v1.1.0-beta/package.json` |
| Alpha conditional format | `plugins/conditional-format/v0.1.0-alpha/package.json` |
| Alpha conditional | `plugins/conditional/v0.1.0-alpha/package.json` |
| Alpha date calculator | `plugins/date-calculator/v0.1.0-alpha/package.json` |
| Alpha grid editor | `plugins/grid-editor/v0.1.0-alpha/package.json` |
| Alpha Kanban | `plugins/kanban/v0.1.0-alpha/package.json` |
| Alpha list search | `plugins/list-search/v0.1.0-alpha/package.json` |
| Beta tabs | `plugins/tabs/v0.1.0-beta/package.json` |

The website's browser tools use native Web APIs. Node is required for selected local tests, not as a browser-runtime package. The GitHub Actions site verification explicitly installs test-only `playwright==1.56.0`, `Pillow==11.2.1` and `beautifulsoup4==4.13.4`.

Three shipped ResoArcOS PC/Pi source ZIPs include `pyproject.toml` declaring Python 3.11+ and **build dependency** `setuptools>=77` with no declared Python runtime dependencies. System distribution packages and Linux kernel packages are separate from this direct-language record.

Third-party Noto Serif JP fonts (OFL 1.1), Unsplash media and browser/kintone platform services are not npm packages; their separate rights and system dependencies still require review. See `THIRD_PARTY_NOTICES.md` and `docs/compliance`.

Future dependency changes must update the package manifest, lockfile when relevant, this document and the component/release SBOM. The CI dependency inventory checker ensures new tracked package manifests are reviewed, but does not establish the correctness of all upstream licenses.
