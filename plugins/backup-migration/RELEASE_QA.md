# ResoArc Backup & Migration v0.3 Release Quality Gate

Status: **Release candidate under validation; NOT approved for production deployment**
Updated: 2026-10-16 (JST)

## Automated evidence

- [x] All 46 Node test cases passed on the Windows development computer.
- [x] A simulated kintone API round-trip transferred **501 source records**, including a nested table and a shared attachment. It created only a new *preview* app, simulated a lost response after 50 committed rows, resumed the remaining 451 rows, and confirmed that a third run added zero duplicates.
- [x] **Actual Edge headless browser smoke test with mocked kintone APIs**: dedicated BrowserCDP Edge loaded the production JavaScript bundle, rendered the management-app controls, created and read a 501-record ZIP, previewed and restored 501 records in 26 batches, and confirmed a second preview offered zero new records. The same real-browser script rejects a tampered ZIP, a destination without a unique restore marker, and an incorrect manual confirmation phrase **before any destination record write**. It also creates a **new app preview draft** via browser UI, verifies the unique restore marker exists, and asserts that **no deploy endpoint or existing-record modification** was used. The browser test exited successfully. No tenant login, cookies, or real API writes were used. Reproduce with `npm run test:browser` on Windows Edge or Linux Chrome; the runner uses a disposable browser profile.
- [x] ZIP archive hardening rejects duplicate entry names and enforces a non-disableable 50,000-entry ceiling, in addition to the existing 25MiB byte limit. Three regression tests cover duplicate entries and entry-count limits. Two more tests confirm that the tenant probe rejects unsafe origins and invalid app IDs.
- [x] Browser UI regression simulates a first batch committed but its HTTP response lost: the UI stops, an explicit re-preview reports 20 completed and 481 pending, and a confirmed resume finishes all 501 with no duplicates.
- [x] Cursor tests cover multi-page reads, invalid pages, stalls, excessive row counts, cleanup on failure, and stopping before destination writes.
- [x] Archive tests cover SHA-256, corrupted contents, attachments, a large compressed payload, ZIP traversal names, and dangerous field-code rejection.
- [x] Field-planning tests cover compatible mappings, incompatible types, required/choice checks, and rejection of unsupported kintone field codes.
- [x] Patched `fflate` to `0.8.3` after detecting CVE-2026-45820 in `0.8.2`; the npm production dependency audit reports **0 known vulnerabilities**. The redistributed MIT license matches the installed upstream file.
- [x] A malformed ZIP64 sentinel parsing case runs in a child process with a hard timeout, so a decompression regression cannot hang the entire test suite.
- [x] Browser build reproduces the committed distribution in CI.
- [x] A standalone browser-smoke launcher has passed with an isolated **fresh Edge profile** on Windows. This is now also a required step in the dedicated GitHub Actions workflow, subject to its first CI run.
- [x] GitHub Actions: Verify ResoArc Backup Migration and Verify public source passed for merge commit `2df9bc70377989fe52edb2d91bc1ebffc93e9b11`. The updated workflow also passed on GitHub Linux Chrome for commit `a77f56e3e889d39d1a91b70ad5214d3062a99633` (both the migration CI and public source CI); three additional UI safety checks require the next run.
- [x] No desktop files created. Work is under the project's Documents/GitHub folder.
- [x] A safe, read-only CDP tenant readiness script is available at `scripts/tenant-api-probe.mjs`. On the development tenant, it returned **HTTP 401** for both GET app details and GET form fields. It never accesses response bodies or authentication secrets; malformed origins and IDs are rejected before browser access.
- [ ] **Authenticated, real kintone tenant API round-trip** (not completed). The isolated BrowserCDP profile remains unauthenticated; the normal Edge sign-in is a different browser profile.
- [ ] **User permission variation and inaccessible records** on a real tenant (not completed).
- [ ] **Actual preview app creation/deployment and restore** in an isolated real tenant (not completed).
- [ ] **Actual browser cancellation/session expiration and recovery** (not completed).

## Required isolated tenant procedure

Prepare **three new test applications**, not an existing business application:
1. A source app with a single-line text, number, selection, attachment, and table containing text/attachment. Add at least 3 non-sensitive dummy records, including an empty file field and a duplicate attachment.
2. A dedicated `ResoArc Backup` management app matching the six field codes in README.md. Restrict app and record access to the test operator.
3. An empty destination app with compatible fields and an editable, `unique=true` single-line `ResoArcRestoreKey` field. This must be an otherwise unused test app.

Run the following checks in the authenticated browser. **Never copy session cookies or passwords into logs.**
- [ ] In the source tenant, inspect `/k/v1/app.json` and `/k/v1/app/form/fields.json` with the read-only `scripts/diagnose-kintone-session.js` diagnostic. Confirm both read permissions.
- [ ] Install the built browser JS **on the management app only**, refresh its record index, verify a single operation panel appears, and check the console for initialization errors.
- [ ] Back up the source, confirm the management record's `Archive`, `SourceAppId`, `ArchiveHash` and count, download the ZIP, and independently confirm its SHA-256.
- [ ] Restore preview to the empty test destination, verify exact source/target field counts, skipped field names, and planned writes **before** confirmation.
- [ ] Restore once, compare all supported fields, table rows and attachment bytes, and verify unique `ResoArcRestoreKey` markers. The original IDs and audit trail are intentionally not cloned.
- [ ] Preview and restore the same archive again. Confirm `0 new records`, no duplicates, and unchanged original data.
- [ ] Test an incompatible target type and a missing unique marker. Confirm both stop **before** any record write.
- [ ] Test app creation preview; create a fresh preview app only; verify it remains pre-live and no existing app is modified. Manually deploy only after reviewing field settings.
- [ ] Test an interrupted restore on *test data only*. Verify confirmed already-written rows are skipped after explicit preview and retry; no blind automatic retry.
- [ ] Sign in as a user without required view/add permissions. Confirm safe failure and that an incomplete backup is not mistaken for full tenant data.
- [ ] If cross-tenant migration is advertised, test import of a ZIP through the approved offline channel, confirm mapping and actual restored bytes in another isolated tenant.

## Security and operational boundaries

- This is **append-only migration**, not a full disaster-recovery backup: it omits historical metadata, app permissions, process history, views, some field types, and inaccessible records.
- It is **not a transaction** across all batches. Failed restores can leave some newly inserted records.
- Record visibility is defined by current kintone permissions. A backup cannot assert that all tenant records were readable.
- An external ZIP has internal SHA-256 integrity checks, not a cryptographic signature proving origin. Only import from a trusted source.
- The 25 MiB uncompressed and ZIP size limit, the 50,000-entry ZIP limit, and the 20,000-record limit are explicit abort conditions, not silent truncation.
- Store a separate encrypted/off-tenant copy if continuity after tenant loss is required.
- No API tokens, session cookies, passwords, customer data or personally identifying evidence should be committed to the public repository.
- Releasing a stable public build must not be confused with deploying into a user's kintone account.

## Release decisions

- **Automated code quality gate:** PASS, subject to latest CI after all documentation updates.
- **Real-world integration gate:** BLOCKED pending isolated tenant tests and browser access.
- **Public production release:** **NO-GO** until the real-world integration gate passes.
- **Developer preview:** May remain available for review on a Draft PR with conspicuous alpha limitations, not promoted as production-ready.

For reproducibility run `npm ci && npm run check` inside `plugins/backup-migration`, then inspect `git diff --exit-code -- dist/resoarc-backup.js`.
