# ResoArc production / GitHub reconciliation, 2026-11-08

## Cause

The Cloudflare Pages project `resoarc` uses **Direct Upload**, not
GitHub-linked automatic deployment. Isolated site-building worktrees had been
uploaded independently, while the official GitHub `main` stayed behind.

## Evidence and source selection

- Public production sitemap: **54** routes.
- Official GitHub `main` prior to this merge: **37** routes.
- Production-only routes: **27**. Main-only routes: **10**.
- Verified local release source: `integration/kintone-three-release-prep-20261107/site`
  (54 routes, 331 files). This is a separate, preserved operator worktree.
- **145 of 145** linked public static and data files matched that source by
  downloaded bytes and SHA-256.
- Of the 53 HTML pages fetched initially, **48** had matching parser-extracted
  text; the remaining pages may be affected by Cloudflare's HTML processing
  and should not be treated as byte-identical.
- All three previously unlocated product pages were found in that release
  worktree: `input-template`, `mail-compose`, `reuse-reset`.
- Initial transient failure loading `/tools/kintone-auto-number/` was retried,
  and a later HTTPS request returned HTTP 200.
- Reconciliation preserves the union of both site maps: **64 routes**,
  with a source tree of **339 files**.

## Merge and safeguards

1. Restored the verified public source as the baseline without erasing the
   eight previous-main-only files.
2. Merged the release Worker's SWWW read-only API and Outage Radar handlers
   with official main's optional privacy-minimized Analytics Engine tracking
   and live OpenSSF Scorecard handler. Keep explicit historical fallback.
3. Set `_routes.json` to invoke the Worker for pages, downloads and APIs
   (excluding normal `/assets/*` static files), rather than routing only
   `/api/scorecard`.
4. Merged production HSTS, CORS and Content Security Policy with narrowly
   scoped official badge image origins.
5. Updated the privacy notice to disclose potential optional aggregate
   telemetry and made new community pages discoverable.
6. Updated the ISO verification rule: a public ISO link, if advertised,
   must include a matching digest; the site currently states that the
   experimental ISO is not available for general distribution.
7. Added a **fail-closed** live-data guard checking three independently
   published SWWW files for exact byte matching. Deploys must also retain
   every live sitemap route.
8. Two synthetic credential URLs in the published ZIP's security test fixtures
   are narrowly exempted from the secret scanner using exact SHA-256 hashes
   of their original lines. All other secrets remain blocked.

## Acceptance evidence

- `python scripts/verify_site.py`: PASS.
- `python -m unittest discover -s tests -p test_*.py`: 20/20 passed.
- `node --check site/_worker.js`: PASS.
- `node --test tests/test_site_worker_reconciled.mjs`: 7/7 passed.
- `python scripts/check_repository_secrets.py`: 0 findings.
- `python scripts/verify_live_route_preservation.py`: 54 live
  routes retained by 64-route candidate.
- `python scripts/verify_live_data_preservation.py`: 3/3 live SWWW
  files equal.

A merged PR alone does **not** synchronize production. Full completion
requires merging to official GitHub `main`, Direct Upload of that exact
commit with the guarded deploy script, and live HTTP/API smoke tests.


## Signed QA distribution reconciliation, 2026-11-09

The live-derived QA manifest listed eight ZIP hashes different from the
immutable official GitHub Release mirror `resoarc-osps-distribution-mirror-20261106`.
The mirror packages passed exact SHA-256 pinning and all eight contents.zip
payloads matched current tracked plugin sources byte-for-byte. The live-derived
Kanban package had a contents.zip/source mismatch.

We preserved the live-derived eight packages and manifest under the isolated
PC evidence folder `site-reconcile-20261108/evidence/previous_live_qa_20261109`;
they were not deleted or overwritten as evidence. The canonical site now
contains the verified official mirror ZIPs, using their original names and
signatures, and restores the corresponding immutable signed QA manifest.

The public download checksum table, recognition JSON, and new
`docs/compliance/OSPS_RELEASE_35_LICENSE_INVENTORY_20261109.json` point
to exactly the mirrored bytes. Historical 2026-11-06 compliance inventories
remain unchanged as dated snapshots. Both CI and the deployment guard enforce
byte-level consistency; the deploy script hydrates missing audited ZIP assets
from GitHub Releases and refuses mismatches.

**Release qualification:** These packages are signed QA candidates, NOT
tenant-accepted/GA plugins. SHA-256 and source-byte identity are not a
cryptographic signature check or an independent legal rights attestation.
Cloudflare production is not changed until PR checks and live-data guards pass.


## 35-ZIP distribution reproducibility

The official 2026-11-06 Release mirror pins 20 historical ZIPs, whereas the
current site serves 35 ZIP assets. During reconciliation the Kanban alpha
source ZIP on the live-derived worktree differed from the immutable official
archive and the ResoArcOS v0.1.1-dev source ZIP was absent locally. Both were
restored from the official mirror using exact SHA-256/byte-size checks; the
previous Kanban ZIP was preserved in the isolated evidence folder.

The remaining 15 ZIPs are not yet present in an independent GitHub Release
mirror. To make a clean CI checkout and a reproducible deployment possible,
`scripts/hydrate_current_distribution.py` downloads only those missing
15 from `https://resoarc.com/downloads/`, accepts bytes **only if** SHA-256
and byte length match the repository-pinned active 2026-11-09 inventory, and
fails closed on mismatch. The 20 historical assets can only come from the
official immutable GitHub Release path. CI and deployment both hydrate the
historical mirror first, then the additional exact-hash current assets.

This is a continuity mechanism, not proof of independent long-term archive
availability, cryptographic signing or human rights approval. Independent
mirroring of the 15 remaining ZIPs is a follow-up requirement.
