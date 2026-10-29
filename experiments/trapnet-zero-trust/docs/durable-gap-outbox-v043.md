# TrapNet signed-gap durable outbox v0.43 (local-only)

**Status: DRAFT, no production deployment or public-release approval.**

The Sensor's signed coverage-gap notice is now staged to a private local
single-item outbox **before** attempting the loopback HUB POST. An interruption
between signing and receipt cannot silently generate a different event ID.
The outbox never stores raw network logs, passwords or arbitrary attacker text.

## CLI (experimental and operator-controlled)

On the same trusted host as the experimental loopback HUB:

```sh
# Use an operator-owned directory with mode 0700 (pre-create it):
mkdir -m 700 /home/operator/trapnet-private

# Manual, authenticated one-shot notice. Do NOT run without an actual reason.
go run ./cmd/sensor \
  -key /home/operator/trapnet-private/sensor-private.hex \
  -gap-reason storage_full \
  -gap-outbox /home/operator/trapnet-private/pending-gap.json

# If connection failed, retry the SAME signed event while it remains current:
go run ./cmd/sensor \
  -key /home/operator/trapnet-private/sensor-private.hex \
  -gap-outbox /home/operator/trapnet-private/pending-gap.json \
  -retry-gap-outbox
```

The existing Sensor command retains its `127.0.0.1:8788/report` endpoint
restriction. Redirects are disabled for both ordinary and gap reports.

## Fail-closed behavior

- Single absolute outbox path, private parent and `0600` pending notice.
  No overwrite: another unacknowledged gap must not be replaced by a new one.
- `O_EXCL` lock prevents concurrent writes or retry on the same path.
  A lock abandoned by process death is intentionally *not* automatically
  deleted. Only an owner can inspect/remove it using a separate manual process.
- Pending bytes and disk writes are synced before HTTP is called. A partial or
  malformed pending record is held for operator repair, never sent.
- Retries load the **original** signature and event ID. A stored notice is
  verified against the Sensor's current public key and the current time.
- `202` plus an exact bounded `{"status":"received_unverified"}`
  response is required to remove the pending notice; all other status codes,
  malformed responses, transport errors, changed files or unknown outcomes
  keep it in HOLD. In particular `409` does *not* imply safe receipt.
- The outbox directory is fsynced after staging and after removal. If the
  filesystem cannot attest durability, the operation fails closed.
- A 10-minute-old report becomes stale under the existing protocol. The
  outbox will **not** silently update its timestamp, resign a different event
  or assert that the past interval is complete.

## What's still missing before an actual distributed release

1. Independently authenticated durable HUB acknowledgments and reconciliation
   query for the crash-after-202 / retry-409 ambiguity. Current HTTP receipt
   is trusted only on the local loopback test path, not over a public network.
2. Bounded queue with multiple pending observations and ordering guarantees.
   This is deliberately *single item only* until multiple epoch handling is
   independently reviewed.
3. Fault-tolerant prolonged outages: beyond the freshness window, a replayed
   report is correctly rejected. External Witness and operator-signed incident
   recovery are mandatory to reconcile long outages.
4. Cowrie read-only health probe integrated with the queue, actual isolation,
   full private storage quota/retention, and independent human review.
5. Cross-platform runtime permissions and directory sync behavior, power-loss
   recovery, secret-key storage and operator/manual stale-lock recovery tests.

**No automatic healthy/clear message, Guardian command, firewall block,
public feed or background upload was added.**
