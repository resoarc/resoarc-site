# ResoArc release user guides and version-to-documentation map

**2026-11-06 edition.** OSPS-DO-01.01 evidence. This guide covers public browser tools, signed kintone QA downloads and ResoArcOS developer source snapshots; it does **not** suggest that QA/alpha products are production-approved.

## Universal precautions

- Verify the full product name, version, public SHA-256, source/release link and applicable LICENSE/NOTICE before using a downloadable archive. Preserve these notices when redistributing.
- Never upload business credentials, tokens or confidential files to an unknown destination. Browser-only tools process files in the local page unless a tool explicitly states otherwise.
- Signed plugin ZIPs are only installable as the **outer ZIP**. Never upload its inner `contents.zip` as a kintone plugin, or rewrite the signature.
- The signed QA batch is **not tenant validated** and explicitly **not for production rollout**. Test with a separate sandbox and backup; review plugin access permissions. Source-only alpha builds are examples, not certified deployment packages.
- For help, limitations or defects see `SECURITY.md`, `CONTRIBUTING.md` and the [GitHub issue tracker](https://github.com/resoarc/resoarc-site/issues).

## Browser tools

These tools have a direct page with inputs, a processing action, outputs and stated limitations. For file-based utilities, choose a local file in the page, run its check, inspect the result and manually decide whether to export or modify data. No automatically applied kintone changes should be assumed.

| Tool | User operation | Public user page |
| --- | --- | --- |
| SHA-256 file checker | Choose a file, calculate the hash and compare it against the distributor's trusted checksum | [hash](../site/tools/hash/index.html) |
| CSV/TSV structure validator | Choose CSV/TSV, inspect encoding/structure and row or column diagnostics before import | [csv](../site/tools/csv/index.html) |
| qAIUIck v0.2 beta demo | Open the demo, enter a memo and press Enter or Add; remove a memo with Delete. Records stay in that browser's localStorage, are not backed up, and may be cleared. Do not enter confidential data. See the product page for the downloadable source ZIP and localhost-only SQLite sample. | [qAIUIck demo](../site/tools/qaiuick-demo/index.html) |
| Bulk-change preflight | Input a change dataset, preview and inspect problems before making any bulk update elsewhere | [bulk-preview](../site/tools/kintone-bulk-preview/index.html) |
| App configuration diff | Select two JSON configuration exports, inspect differences and mismatched fields | [app-diff](../site/tools/kintone-app-diff/index.html) |
| Permission definition audit | Supply a permitted kintone permission export to inspect access rules | [permission-audit](../site/tools/kintone-permission-audit/index.html) |
| Import preflight | Choose data and optional form definition, inspect broken references and incomplete rows | [import-check](../site/tools/kintone-import-check/index.html) |
| Duplicate detection | Load candidate data and inspect duplicates; review before deleting original records | [duplicates](../site/tools/kintone-duplicates/index.html) |
| Lookup consistency audit | Load lookup/reference exports and inspect inconsistent/missing keys | [lookup-audit](../site/tools/kintone-lookup-audit/index.html) |
| Cross-app aggregation | Supply authorized local datasets, inspect aggregate results and input assumptions | [cross-aggregate](../site/tools/kintone-cross-aggregate/index.html) |
| Browser report/PDF output | Provide a dataset, inspect preview and use the browser's print/PDF function | [print-report](../site/tools/kintone-print-report/index.html) |

For Web8 GA v1.0.0, the frozen source archive contains LICENSE and the corresponding `docs/WEB8_V1_RELEASE.md` release notes. There are eight GA kintone-related browser tools in that release; do not confuse them with the eight signed QA plugins below.

## kintone installable plugins and source-only alpha versions

1. In a **nonproduction** kintone tenant, inspect the relevant plugin and prepare the prerequisite fields or space elements described on its page.
2. Open kintone administration and add the downloaded **signed outer ZIP**. Verify the plugin is shown in the intended application, then configure its options according to that application.
3. Test with disposable records, confirm behavior on desktop/mobile as supported, and check the product's known limitations. Do not assume cross-app permissions, change propagation or server-side validation without tests.
4. Keep the approved archive, its published SHA-256 and license/notice documentation together. Roll back by disabling the plugin or restoring the sandbox backup if the QA behavior is unacceptable.

| Plugin / feature | Main configuration or operational purpose | Public user page |
| --- | --- | --- |
| Auto-number | Configure numbering target fields, format and scope; validate sequence behavior without collisions | [auto-number](../site/tools/kintone-auto-number/index.html) |
| Tabs | Add a form space with element ID `resoarc_tabs`, then assign field groups and tab titles | [tabs](../site/tools/kintone-tabs/index.html) |
| Conditional fields | Define visibility and required-field rules; test order and conflicting conditions | [conditional](../site/tools/kintone-conditional/index.html) |
| Conditional formatting | Configure rule expressions/colors in a test app, check rule priority and accessibility | [conditional-format](../site/tools/kintone-conditional-format/index.html) |
| Date/period calculator | Configure source and output dates/periods, test edge cases such as blanks and date boundaries | [date-calculator](../site/tools/kintone-date-calculator/index.html) |
| Advanced list search | Select supported indexed/search fields, test filter combinations and permissions | [list-search](../site/tools/kintone-list-search/index.html) |
| Grid editor | Configure editable columns, validate drafts before saving and preserve original records | [grid-editor](../site/tools/kintone-grid-editor/index.html) |
| Kanban display | Configure grouping/status fields and test card movements/permissions in the sandbox | [kanban](../site/tools/kintone-kanban/index.html) |

The [signed QA bundle and known limitations](../site/products/kintone/qa/index.html) is the release-specific place to confirm each QA ZIP/version/plugin ID. Five alpha features are also available as **source-only** archives. A source ZIP is for examination and local development and must not be installed as an already-signed package.

## ResoArcOS PC and Pi source snapshots

The ResoArcOS developer materials are **not a general-purpose supported production OS**. Follow the source archive's README, build scripts and verification tests only in a disposable laboratory or VM. Review licensing, integrity checks and the limitations on the [OS overview](../site/os/index.html), rather than assuming an ISO is fit for physical PCs. The PC v0.1.0-dev, v0.1.1-dev and Pi firstboot v0.2.1-alpha source ZIPs each carry source/build instructions and a Python package manifest. Source archive integrity is checked by the CI and associated SHA-256 evidence.

## All historically distributed ZIP assets (20)

These links are listed to ensure no source/QA release loses its corresponding product documentation. Source and signed installable distributions have distinct use cases.

- Auto-number: `resoarc-auto-number-v1.0.0.zip`, `resoarc-auto-number-v1.1.0-beta.zip`, `resoarc-auto-number-signed-qa.zip` → [auto-number guide](../site/tools/kintone-auto-number/index.html)
- Tabs: `resoarc-tabs-v0.1.0-beta.zip`, `resoarc-tabs-signed-qa.zip` → [tabs guide](../site/tools/kintone-tabs/index.html)
- Conditional fields: `resoarc-conditional-signed-qa.zip` → [conditional guide](../site/tools/kintone-conditional/index.html)
- Conditional formatting: `resoarc-conditional-format-v0.1.0-alpha-source.zip`, `resoarc-conditional-format-signed-qa.zip` → [format guide](../site/tools/kintone-conditional-format/index.html)
- Date calculator: `resoarc-date-calculator-v0.1.0-alpha-source.zip`, `resoarc-date-calculator-signed-qa.zip` → [date guide](../site/tools/kintone-date-calculator/index.html)
- Grid editor: `resoarc-grid-editor-v0.1.0-alpha-source.zip`, `resoarc-grid-editor-signed-qa.zip` → [grid guide](../site/tools/kintone-grid-editor/index.html)
- Kanban: `resoarc-kanban-v0.1.0-alpha-source.zip`, `resoarc-kanban-signed-qa.zip` → [kanban guide](../site/tools/kintone-kanban/index.html)
- List search: `resoarc-list-search-v0.1.0-alpha-source.zip`, `resoarc-list-search-signed-qa.zip` → [search guide](../site/tools/kintone-list-search/index.html)
- Web8: `resoarc-web8-v1.0.0-source.zip` → [Web8 catalog](../site/products/web/index.html)
- ResoArcOS: `resoarcos-pc-v0.1.0-dev-source.zip`, `resoarcos-pc-v0.1.1-dev-source.zip`, `resoarcos-pi-firstboot-v0.2.1-alpha-source.zip` → [OS overview](../site/os/index.html)

**Integrity and mirror:** [immutable SHA-256 audit](compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json), and [GitHub historical archive release](https://github.com/resoarc/resoarc-site/releases/tag/resoarc-osps-distribution-mirror-20261106). The archive release contains the same historical ZIP bytes plus the first-party LICENSE and NOTICE, but not a blanket security certification.

**Limitations:** Publication of this map does not prove every individual user's receipt of notices, nor that every experimental capability is supported. This is a source/release documentation index; review actual product-specific pages before release.
