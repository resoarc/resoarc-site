# TrapNet v0.48: opt-in signed HUB receipts (experimental)

**Status: DRAFT / HOLD.** A signed receipt proves **only** that a pinned
HUB signing key asserts the exact signed Sensor report was durably recorded
in the local verified HUB ledger. It does not establish independent Witness
verification, completeness of observation, or recovery of a missing interval.

## Local opt-in (not production deployment)

Make a separate, offline-controlled HUB receipt signing key and distribute
only its **pinned public key** to the trusted Sensor operator. The signer must
be distinct from the Sensor report key; these are separate roles.

```sh
go run ./cmd/keygen -out /private/lab-hub-receipt
go run ./cmd/hub -allowlist /private/allowlist.json \
  -ledger /private/ledger.jsonl \
  -receipt-key /private/lab-hub-receipt/private.hex

go run ./cmd/sensor -key /private/sensor/private.hex \
  -gap-reason storage_full -gap-outbox /private/spool/pending.json \
  -hub-receipt-pub /private/lab-hub-receipt/public.hex
```

The HUB is restricted to `127.0.0.1:8788` and its private key must be
a regular file with mode 0600. Signed receipt mode is off by default to
preserve existing clients; the Sensor explicitly opts in using the public
key file. In pinned mode, **an unsigned HTTP 202 is never sufficient**.
After local ledger sync and checkpoint save, HUB issues signed receipt
bound to full signed report SHA256, node/event identity, ledger tip,
ledger row count, receipt time and HUB signer identity.

## The formerly unresolved lost-ACK case

- A Sensor creates a single signed `coverage_gap` and fsyncs it to
  the durable outbox.
- HUB receives it, fsyncs the append-only ledger and checkpoint, but
  the HTTP 202 or its body is lost on the way back. Sensor keeps pending.
- Sensor manually retries the **same report** before the existing
  10-minute freshness deadline. HUB checks its actual ledger bytes and
  checkpoint, finds **exactly that signed report**, and signs a 409 receipt.
- The Sensor verifies the 409 receipt against its **independently pinned**
  HUB public key and the original immutable signed Sensor report. Only then
  may it remove the pending file.
- Wrong signer, changed event/body, forged ledger tip, invalid schema,
  malformed receipt, unsigned 202/409, unreachable HUB, poisoned ledger,
  archive-only event IDs and stale Sensor reports all remain **HOLD**.

This is not a public network service; it does not create any new HTTP
endpoint or remote execution path. No automatic all-clear, defense feed,
blocking instruction, unattended scheduler or remote key distribution
is introduced.

## Release blockers remaining

1. Signed **external Witness** anchored on a separately controlled host and
   independently retained receipt/ledger tips. The HUB signer is a claim by
   the HUB and could be compromised.
2. Audit and protect production signer key generation, rotation, recovery
   and revocation; use independently signed attestations of retained state.
3. An authenticated reconciliation mechanism for Sensor reports older
   than 10 minutes, multi-record ordering, offline durable queue and
   non-repudiable operator incident epoch closure. No automatic resigning.
4. Real LAN isolation, retention/deletion, power-loss and independent human
   security review.
5. Full cross-process E2E and adversarial integration acceptance at the
   exact final PR commit.

**A3/D2/D3 stay PARTIAL; overall public release remains HOLD.**
