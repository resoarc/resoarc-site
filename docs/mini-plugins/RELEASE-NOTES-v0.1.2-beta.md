# ResoArc Mini Plugins v0.1.2-beta

Date: 2026-10-17

## Scope
18 independent, free kintone PC web plugins; same plugin signing identities as v0.1.1-beta.

## Changes
- Added field-value type validation for editable records and disallowed writes to system/read-only fields.
- Removed repeated field help hints after re-render.
- Extended lookup field codes to Japanese and other Unicode letters/digits; query escaping and 100-character search bound retained.
- Canceled in-flight attachment downloads when preview dialog closes, with object URL cleanup.
- Added 8-second timeout for external postal address searches.
- Protected numeric aggregation against Infinity.

## Test results
- 18/18 plugin manifests and runtimes generated.
- 31/31 simulated event handlers executed successfully.
- 17/17 Chromium interaction checks passed (previously 10), including CSV formula injection neutralization, external scheme/link rejection, URL redirect same-origin policy, Unicode lookup, request cancellation, postal address completion, and field-type validation.
- 18/18 signed ZIPs independently verified; all 18 retained the original public-key fingerprints.
- 38/38 static site assets passed SHA-256 integrity check.
- 18/18 site download links resolve within the staged distribution; mobile-width search UI checked.
- Signing keys were excluded from public source/site distribution.

## Status / release gates
**BETA ONLY.** No real kintone tenant installation, permission matrix, other-plugin coexistence, or mobile checks have been completed. The static site build is prepared but *not deployed* to resoarc.com. Do not call this a production-ready release.

The signed beta ZIPs, source archive and staged site files were generated as conversation artifacts separately. This GitHub branch currently holds release notes and the verification handoff, not a claim that the binary files are hosted here.

## Next verification gates
1. Install each signed plugin in a dedicated test tenant, map valid field codes, and confirm install/update behavior.
2. Test create/edit/detail/index and saved record data; include reuse, records with and without attachments, file permissions, guest spaces, non-ASCII field codes.
3. Test other-plugin coexistence, repeated events, large attachments, network failures, mobile unsupported-state messaging, and browser support.
4. Publish public source and ZIPs only after verifying the test results and excluding private keys.
5. Deploy the catalog and update navigation/release announcements, then verify HTTP downloads and checksums in production.
