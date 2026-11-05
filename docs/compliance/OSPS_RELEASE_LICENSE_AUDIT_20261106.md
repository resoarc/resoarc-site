# ResoArc released-asset licensing audit | 2026-11-06

**Scope:** exact GitHub `main` distribution files in `site/downloads/`, snapshot before the compliance PR; checksum evidence saved in [JSON](OSPS_RELEASE_LICENSE_AUDIT_20261106.json).

| Audit item | Observed |
| --- | --- |
| Source ZIPs inspected | 9 |
| Signed kintone installation ZIPs inspected | 11 |
| Total ZIP assets | **20** |
| Signed installation ZIPs with LICENSE/NOTICE in outer archive | **0 of 11** |
| Source ZIPs with LICENSE entry | **9 of 9** |
| Signed ZIP bytes altered by remediation | **No** |
| Effective user-facing notice delivery confirmed | **No, outstanding** |
| Every third-party component/license verified | **No, outstanding** |

### Reproducible audit

```sh
python scripts/audit_release_license_evidence.py
# Release gate (expected to FAIL until remaining obligations and delivery checks are closed)
python scripts/audit_release_license_evidence.py --strict
```

The test verifies each known ZIP SHA-256 and size, ZIP integrity, license entry inventory, signed package presence and first-party LICENSE / NOTICE companion. The default command returning 0 **does not mean** OSPS LE-03.02 or OpenChain conformance; `--strict` remains intentionally blocked.

### Status and safe path to closure

1. **Interim**: publish `site/downloads/LICENSE` and `site/downloads/NOTICE.md` next to the existing artifacts. They explain MIT and the separate third-party conditions while preserving original signed installers. This is not yet sufficient to prove each downstream user received the license.
2. **Distribution UX**: explicitly link license and notice adjacent to every signed package download button, or build a verified outer download bundle containing the byte-identical signed installer and appropriate license and notices. Avoid changing the inner signed file or publicly relied-on ZIP URLs without migration tests.
3. **License rights verification**: audit all actual inner package source files, source correspondence, nested dependencies and exceptions, record individual approvals, and provide applicable source-offer obligations.
4. **Artifact migration**: do not delete generated ZIPs from Git/source until the live Cloudflare Pages distribution scheme provides identical URLs or verified redirects, SHA-256 hashes and accessible source archives. Re-test current users' download/install scenarios before Git cleanup.
5. **Compliance closure**: execute the end-to-end distribution verification and actual license review, archive proof, then amend `distribution_evidence_verified` and `all_license_obligations_verified` only with URLs, hashes, reviewer evidence and timestamp.

This audit distinguishes the source repository from production deployment, and makes **no external certification claim**.
