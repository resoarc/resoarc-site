# TrapNet v0.50: A2 real Cowrie log fault matrix / formal acceptance evidence

**Status: experimental / release HOLD. This is not an independent security sign-off.**

## What was missing

Prior CI proved genuine Cowrie ENOSPC, full private-state restoration,
and synthetic broken JSON → signed `coverage_gap` → durable HUB ledger.
The public A2 checklist also requires **real Cowrie-generated JSON** being
missing, partially torn, or duplicated, plus the correct fail-closed signed
notice and persistent HUB replay refusal.

## Isolated test implementation

`lab/real_cowrie_fault_matrix.py` now deliberately uses **actual SSH events
written by a real pinned Cowrie Docker container**. The test runs under
a disposable 16MiB ext4 image, network-disabled non-root Cowrie,
read-only container root, no public ports and local-only HUB.

After the normal SIGKILL/full-var restoration/SSH-recreation exercise is
complete, the disposable Cowrie process is stopped. Its genuine private
`cowrie.json` bytes are copied only inside the test process. Three separate
fault cases are injected into that local test file:

| Fault | Expected diagnosis | Signed Sensor coverage gap |
|---|---|---|
| Missing `cowrie.json` | `JSON_LOG_MISSING` | `log_unavailable` |
| Genuine rows followed by a partial torn row | `JSON_LINE_INVALID` | `log_corrupt` |
| Exact duplicate of a genuine JSON row | `JSON_LINE_DUPLICATE` | `log_corrupt` |

For each scenario, the diagnosis must never claim observation coverage.
The operator-only bridge must not send by default; an explicitly armed
send while HUB is absent must preserve an **independent signed original**
in a separate, restrictive durable outbox. The exact genuine log is
restored after every scenario even if a test fails.

After all three faults, a disposable real Go HUB is started on
`127.0.0.1:8788` only. It must persist exactly three differently signed
Sensor events, discard their pending files only after accepted delivery,
gracefully stop/restart with an intact checkpoint, and reject replay of
all three originals with HTTP 409. Repair of the log must not claim
that any historical missing observation interval became healthy.

The new `cowrie_log_health.assess` detects **byte-identical repeated
JSON rows** using SHA-256 digests in local memory. SHA256 values and
raw events are never emitted. This deliberately classifies ambiguous
duplicates as corrupted coverage, rather than an attack event. Similar
but nonidentical rows, e.g. similar event types with new timestamps,
are not falsely classified as exact duplicates.

### Gate acceptance limits

An A2 **component test** can pass once the exact CI commit's real-container
end-to-end job, Python unit tests, cleanup attestations and digests succeed.
A2 **formal release PASS** still requires the test's original evidence to be
retained/pinned and reviewed by an independent operator, together with
production-equivalent observation-window continuity, off-host witnessed
receipts, and a documented disaster recovery procedure.

The CI runner and ephemeral credentials are owned by the same test
infrastructure. **A green CI result alone is not an external auditor's
signature.** No live Cowrie logs or production service settings are changed.
Do not treat an undetected event deletion or nonidentical duplicate as
proof of completeness. No automatic all-clear, firewall block or public
feed is generated.

**Overall release remains HOLD until each formal acceptance criterion is met.**
