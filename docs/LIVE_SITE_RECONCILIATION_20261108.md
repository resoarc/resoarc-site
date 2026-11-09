# Direct Upload Pages route-drift audit (2026-11-08 JST)

**Deployment blocked on purpose.** Do not replace production with a smaller canonical Git site/ tree.

## Evidence

Official GitHub main: 7d942bfb4e4388c3705b3dae41b9fdc98893bedd.

Production checks via HTTPS from the project operator workstation:

- https://resoarc.com/ -> HTTP 200.
- https://resoarc.com/products/ -> HTTP 200.
- https://resoarc.com/os/ -> HTTP 200.
- https://resoarc.com/community/ -> HTTP 404.
- https://resoarc.com/en/ -> HTTP 404.
- Production sitemap.xml has **54** URLs; canonical site/sitemap.xml has **37**.
- **27 URLs** exist in production sitemap but are absent from the Git sitemap; **10 URLs** are Git-only, including the two new pages.

Production-only paths (as verified on 2026-11-08 JST):
- /education/
- /education/circuit/
- /education/programming/
- /guide/backup-migration/
- /products/backup-migration/
- /products/development-status/
- /products/kintone/attachment-count/
- /products/kintone/csv-export/
- /products/kintone/field-help/
- /products/kintone/input-template/
- /products/kintone/list-aggregate/
- /products/kintone/lookup-suggest/
- /products/kintone/mail-compose/
- /products/kintone/qr-code/
- /products/kintone/record-toc/
- /products/kintone/related-links/
- /products/kintone/release-integrity/
- /products/kintone/reuse-reset/
- /products/kintone/save-navigation/
- /products/kintone/tabs/
- /products/kintone/text-normalizer/
- /security/
- /security/advisories/php-20261021/
- /security/weather/
- /source/
- /status/
- /trust/

Git-only paths include seven legacy /tools/kintone-*/ pages, /products/kintone/qa/, /community/ and /en/. Git sitemap entries are not evidence of live delivery.

Local historic worktrees osps-baseline1-prod-20261107 and growth-media-20261108 contain 51 of 54 currently published routes, but HTML/assets are not proven byte-identical to current production. Importing them without careful reconciliation may overwrite newer live content. These trees are evidence candidates, not deployable backups.

## Automatic safety gate

scripts/verify_live_route_preservation.py now runs inside scripts/deploy_canonical.ps1 before wrangler pages deploy. It fetches the live sitemap from a fixed HTTPS URL, validates host and paths, then requires every live route to exist both in candidate sitemap and as a static index.html file. Network failures, invalid XML, lost pages and missing HTML all block deployment. It never overwrites production or auto-migrates files.

Proof: the current candidate produces nonzero exit code, with **27 missing routes**, so the dangerous downgrade is rejected. Unit tests cover preservation, added routes, path traversal, foreign domains, missing files and malformed XML.

## Reconciliation and release gates

1. Identify actual source for all 27 production-only routes and their dependent JS/CSS/images/fonts, including the 3 routes absent from local 51-route snapshots.
2. Validate public file content against trustworthy local development evidence, preserving old product downloads and licensing; do not pull arbitrary generated binaries into Git.
3. Compare all shared pages/assets with current production to avoid silent rollback. Preserve SWWW data-source freshness and service-specific deployment paths.
4. Rebuild a complete canonical site/ tree and sitemap; run scripts/update_manifest.py, scripts/verify_site.py, provenance/license/secret checks and CI.
5. Review the full diff, merge only after all checks pass, then run scripts/deploy_canonical.ps1 against exact merged main and verify apex, www, Pages hostname and immutable ZIP SHA-256.
6. Only after safe site deployment, activate Cloudflare Analytics Engine binding RESOARC_ACTIVITY; confirm events arriving and disclose first-measured date.

Cloudflare redirect rules for legacy download URLs can bypass a Pages Worker. Such requests may be uncounted even after optional binding is enabled; reconcile with Cloudflare data before publishing download statistics.

No production deployment or analytics activation occurred in this audit.
