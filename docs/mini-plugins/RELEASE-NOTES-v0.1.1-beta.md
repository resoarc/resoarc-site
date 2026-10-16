# ResoArc Mini Plugins v0.1.1-beta

18 independent, free kintone desktop mini plugins (evaluation builds).

## Catalog
1. input-template
2. reuse-reset
3. text-normalizer
4. field-help
5. save-navigation
6. mail-compose
7. list-aggregate
8. csv-export
9. attachment-count
10. table-row-tools
11. qr-code
12. record-toc
13. related-links
14. sticky-list
15. file-preview
16. lookup-suggest
17. postal-address
18. barcode-scan

## Quality status, 2026-10-16
- 18 source implementations and independently signed beta ZIPs built locally.
- JS syntax checks passed; 31 mocked event registration/execution checks passed.
- 10 Chromium browser mock interaction checks passed, covering settings, redirect, authenticated file fetch, lookup select, QR canvas, help fallback, table row clone, and barcode fallback.
- Static site release assembled separately and checked for valid ZIP targets.
- No real kintone tenant install or compatibility test yet. Keep v0.1.1 as beta.
- Do not publish the archived signing keys, credentials, or development work paths.

## Key changes from beta 0.1.0
- Add X-Requested-With to file download requests.
- Optional official lookup refresh via runLookup configuration.
- Redirect suppression for stay setting.
- Limit record table-of-contents to supported detail screen.
- Correct field help placement for detail versus create/edit screens.
- Harden header control lifecycle.

## Publication checklist
- Import every signed ZIP in a dedicated test tenant and configure test application fields.
- Verify field types, permissions, guest spaces, large attachments and cross-plug-in coexistence.
- Complete independent security review and attribution check.
- Upload static site release assets under /tools/mini-plugins/ and /downloads/mini-plugins/.
- Validate every download from the deployed site and update navigation and release information.

This is staging documentation only. No production-site deployment has occurred.
