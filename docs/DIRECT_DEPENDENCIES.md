# ResoArc direct language dependencies

**OSPS-QA-02.01, reviewed 2026-11-06.** This is not a complete system package inventory or an independently audited SBOM.

The original nine tracked plugin JavaScript package manifests were reviewed, each declaring **zero runtime dependencies and zero development dependencies**:

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

Future dependency changes must update the package manifest, lockfile when relevant, this document, the direct-dependency review JSON, and the component/release SBOM. The CI dependency inventory checker ensures new tracked package manifests are reviewed, but does not establish the correctness of all upstream licenses.

## ResoArc Sheet v1.0.0-rc.1 (reviewed 2026-11-18)

The nine previously reviewed zero-dependency plugin manifests remain unchanged.
A tenth package manifest is added for a *Draft PR / CI-only source mirror*:
`apps/sheet/rc1-src/package.json`. This is not a public product download.

- Runtime direct dependencies: **7**; development direct dependencies: **2**.
- npm lockfile (v3): **281** package entries including the root.
- The nine reviewed direct package names, version ranges, npm registry URLs,
  SRI hashes and declared license metadata are recorded in
  `docs/compliance/SHEET_RC1_DIRECT_DEPENDENCIES_20261118.json`.
- The complete first-party manifest and lockfile are individually SHA-256
  pinned. CI rejects any modification or new package without explicit re-review.
- The original nine zero-dependency plugin manifests remain mandatory, and
  no new unreviewed package manifests are accepted.
- The JSZip package metadata gives dual `MIT OR GPL-3.0-or-later` licensing.
  License declarations are not independent legal validation of all sources.
- This review neither approves an official Sheet download nor proves the exact
  source editions of nine transformed third-party browserified modules.
