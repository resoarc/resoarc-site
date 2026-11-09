# Reviewable non-executable assets in the ResoArc source tree

**Audit date:** 2026-11-06. **Current branch:** the generated distribution ZIP files have been moved to a separately verified GitHub Release and removed from the *current tracked tree*. Historic git commits are intentionally preserved; no history rewriting is performed.

The remaining source-tree binary assets are **34 renderable images/fonts**, not application executables or distributable installer blobs:

| Kind | Files | License metadata | Review approach |
| --- | ---: | --- | --- |
| PNG product/plugin icons | 9 | MIT first-party declarations via REUSE | Renderable image; file format, SHA-256 and path audited |
| WebP screenshots | 18 | MIT first-party declarations via REUSE | Renderable image; file format, SHA-256 and path audited |
| JPEG hero photo | 1 | LicenseRef-Unsplash | Third-party media; independently licensed, not re-licensed MIT |
| WOFF2 Noto Serif JP fonts | 6 | OFL-1.1 | Font binary, license and format reviewed; original upstream build provenance remains an external dependency |

Machine-readable 34-file filename, size, binary magic and SHA-256 manifest: [BINARY_ASSET_REVIEW_20261106.json](BINARY_ASSET_REVIEW_20261106.json). The mandatory `verify` job runs `scripts/check_binary_repo_assets.py` to reject any new executable or unreviewable binary, unexpected file formats or asset drift, and all known generated software archives from source control.

The 20 original ZIPs and sidecar LICENSE/NOTICE are retained as GitHub Release assets with exact SHA-256 matching the archived historical audit: [artifact release](https://github.com/resoarc/resoarc-site/releases/tag/resoarc-osps-distribution-mirror-20261106). CI retrieves the originals only **after** verifying the repository-pinned expected byte hashes. No private signing keys are stored.

**Precise claim boundary:** This is a reviewable-format and provenance-record check for the *current source tree*. It is not a malware scan of compiled fonts, an independent font provenance audit, a rewritten git history, or a product security certification. The actual public website deployment may continue to serve the same original ZIPs under legacy URLs after a deliberate verified publication.
