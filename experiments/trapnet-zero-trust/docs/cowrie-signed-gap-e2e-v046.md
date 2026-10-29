# TrapNet v0.46: Broken Cowrie JSON to signed gap across real loopback HUB

**DRAFT / release HOLD.** This experiment ties together three already-tested
components without modifying the live Cowrie or opening a public port:
`cowrie_log_health`, `cowrie_gap_advice`, and the Sensor's durable signed
outbox/HUB HTTP handler.

## Operator-only bridge

The new `sonar/cowrie_gap_lab_bridge.py` is intentionally **not** an
unattended service and is **lab-only**. It requires all paths inside a private,
disposable directory containing an exact `.trapnet-disposable-gap-lab-v046`
marker. It refuses paths outside the temporary lab, an existing pending gap,
stale lock, public key file permissions, symlinks and an unspecified signer
binary. It reports no raw Cowrie events, credentials, addresses or payloads.
The default does not send anything.

If a valid event-log failure is detected, `--emit` calls the existing local
Sensor once with fixed argv, preserving the outbox on a failed delivery.
It does not automatically create a new gap after a previous send or turn
a healthy snapshot into an 'all clear'. The built-in Sensor still enforces
`http://127.0.0.1:8788/report` only. This is not a live production collector.

## CI integration acceptance

```sh
cd experiments/trapnet-zero-trust
python3 -m unittest discover -s sonar -p 'test_cowrie_gap_lab_bridge.py' -v
python3 lab/signed_gap_end_to_end.py
```

The native test on a GitHub-hosted Linux runner:

1. Refuses to run if port 8788 is already occupied; no other network
   connection is needed.
2. Builds the real Sensor, HUB and keygen from the checked-out commit.
3. Generates one-time keys and a disposable Cowrie-shaped JSON file with
   a malformed event line. **This is a synthetic damaged log, not a live
   Cowrie service or evidence of a real attack.**
4. Confirms a read-only check identifies `log_corrupt` without sending.
5. Explicitly arms one send while HUB is unavailable. The Sensor must leave
   the same signed gap in its private durable outbox.
6. Starts the actual HUB HTTP listener on loopback, sends the **same** queued
   bytes with `-retry-gap-outbox`, verifies 202 acceptance and that the
   signed report appears in the real fsynced HUB ledger.
7. Replays the original signed report and expects a 409, without publishing
   a feed or executing a client command.
8. Kills the disposable HUB and removes all temporary keys, logs, state
   and binaries on exit.

## What's still missing for A2/A3 formal PASS

- Reproduce with the **actual isolated Cowrie Docker** when the real
  `cowrie.json` becomes torn/missing, on quota-managed *persistent* storage.
- A production-quality, correctly authorized automatic health collector
  with a durable **multi-event** queue and explicit overload behavior.
- Authenticated independently verifiable HUB acknowledgment, long-outage
  incident epochs and reconciliation of a 202 ACK lost before arrival.
- Off-HUB independent signed Witness and actual signed gap-aware advisory
  reconciliation, source-to-deployment provenance and external human review.
- Explicit production authorization, data retention/deletion assessment,
  and repeat after crash or power failure. The local lab never marks the
  broader release gate PASS.

A test pass only demonstrates the loopback data path and fail-closed behavior.
