# TrapNet v0.60: E1 retention and privacy deletion, offline-only proof

**Status: opt-in synthetic offline staging only; live log retention and formal E1 remain PARTIAL. Public release HOLD.**

There is currently no production-ready, independently reviewed raw-Cowrie
log retention/deletion mechanism. This small tool is **not** a replacement for
such a mechanism. Its sole purpose is to establish safe technical primitives
without risking real activity logs or personal data.

## Safe offline-only behavior

`privacy/retention_offline.py` requires:

- An **absolute non-symlink directory** whose basename begins
  `trapnet-retention-offline-`; directory owned by the current local
  user, with no group/other permission bits. This excludes normal Cowrie
  private-var paths and prevents direct operation on live sources.
- A 0600, owner-only sentinel `.trapnet-retention-offline.json` whose
  exact JSON value is `{"schema":"trapnet.offline-log-retention.v060","synthetic_only":true}`.
- Only one-level, non-hardlinked regular files with an immutable naming
  convention `cowrie-YYYYMMDDTHHMMSSZ-<16 hex>.jsonl`, owner-only
  permissions and bounded count/size. Symlinks, nested dirs, unexpected
  names and world-readable or linked raw logs **fail closed**.
- A UTC cutoff timestamp. By default **dry run**, returning only counts and
  a SHA-256 digest of the complete, current offline deletion plan
  (directory identity, file identity/size/times, cutoff). **No raw event
  content, filenames, IPs or directory paths in returned JSON**.
- Deletion only with `--apply-with-approved-plan SHA256`, matching the
  immediately recomputed plan. It checks each exact file's identity again
  before unlinking, never scans recursively, preserves newer entries and
  reports only categorical counters.

A usable dry-run/apply CLI for **synthetic test fixtures only**:

```sh
python3 privacy/retention_offline.py --root /tmp/trapnet-retention-offline-demo \
  --cutoff-utc 2026-01-01T00:00:00Z
# Inspect output and separately approve plan_sha256:
python3 privacy/retention_offline.py --root /tmp/trapnet-retention-offline-demo \
  --cutoff-utc 2026-01-01T00:00:00Z \
  --apply-with-approved-plan "<verified plan_sha256>"
```

Never copy production Cowrie logs into a public CI runner to run these
commands. The lab uses synthetic data only and has no network access.

## What tests prove

14 Linux-dirfd tests cover default dry-run preserving old logs, explicit
plan approval deleting only old synthetic files, recent-file preservation,
wrong/stale plans, malicious symlinks, hardlinks, unsafe permissions and
roots, unexpected filenames, absent/forged sentinel, invalid cutoff and
absence of raw fields from the result. The test runner emits only anonymous
aggregated status JSON.

## E1 formal PASS still requires

- Inventory of which real services collect/store IP addresses, raw attacker
  payloads and connection metadata and how long each class is held.
- Legitimate collection basis, access ownership, retention schedule,
  encrypted off-host backups and retention of **all backup copies**.
- Paused-source deletion/rotation workflow with audit, legal hold,
  personal-data requests and incident-response responsibilities.
- Evidence of actual deployment, access restrictions and end-to-end
  deletion in production-equivalent storage, including replicas/backups.
- Independent human privacy/security assessment and approval.

Do not automatically infer E1 technical or formal PASS from this isolated
synthetic helper. Retention compliance involves policy and source ownership,
not just a successful delete call. Overall release remains HOLD.
