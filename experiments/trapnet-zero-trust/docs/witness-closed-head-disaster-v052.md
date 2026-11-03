# TrapNet v0.52: full Witness closure, crash/recovery and partition HOLD

**Status:** Draft release-gate hardening. Public release remains **HOLD**.

## Security defect found

The existing `witness.Audit` deliberately checks all *existing* signed
history checkpoints against a ledger. A ledger may have valid newer rows
**after** the most recently signed Witness checkpoint, and prefix-only
historical auditing can still succeed. This is appropriate for browsing
historical evidence. It is **not sufficient** to assert that an entire
closed snapshot, or a HUB receipt referring to an unwitnessed row, has
been independently approved.

Because `receiptwitness.Audit` previously called that prefix-only
helper, a dishonest HUB could append a row, update its *own*
`ledger.jsonl.head`, and produce a valid HUB receipt for a row not
covered by the independently pinned Witness history. **Do not treat
older green CI runs as proof that this case was checked.**

## Changed acceptance logic

New `witness.AuditClosed` requires all of:

1. Independently pinned, exactly formatted SHA256 Witness history tip.
2. Valid, continuous, Ed25519-signed Witness history with that exact tip.
3. The *entire* closed ledger snapshot and its local .head pass integrity.
4. The final **independently signed Witness checkpoint** has the same
   row count and digest as the *end* of the closed ledger. No unwitnessed tail.

`cmd/witness -mode verify` and `receiptwitness.Audit` use this stricter
function. The old `witness.Audit` remains only for explicitly historical
prefix reading and cannot authorize a release decision.

## Fail-closed recovery tests

Added disposable, non-networked Go tests for:

- Stale crash lock: new signing is rejected; original signed history is
  unchanged; manually verified removal of only test-created lock
  permits append with the externally pinned previous tip.
- Torn appended history: refused; restored exact signed backup plus
  original pinned tip is required. Re-bootstrap is rejected.
- Clock rollback and same-time checkpoint: refused without altering
  history. A monotonic timestamp may proceed.
- Rollback of both ledger and Witness history to previously valid old
  bytes: externally pinned **new** tip still rejects. Exact latest
  backup restoration re-enables independent audit.
- Simulated 48-hour network partition with zero new report rows:
  historical proof can still be inspected; no duplicate checkpoint
  or observation all-clear is minted.
- Valid signed first-row HUB receipt plus a syntactically valid newer
  HUB-only ledger row and updated HUB .head: the entire receipt/Witness
  cross-audit must **reject**, not silently accept an unwitnessed tail.

These simulate *crash artifacts and retention boundaries*. They do
**not** turn a simulated lock into a real power-loss trial, nor do
they prove an independently owned Witness organization or immutable
offsite retention.

## Formal PASS gaps

D3 still needs at least one independent, separately administered
Witness custodian and operational evidence for offsite immutable
history pinning, actual power-loss restore, clock skew/partition
recovery with an accepted incident policy, signer key rotation/
revocation, and independent human approval. A3 remains subject to
long-outage multi-report durable queue and genuine event-epoch
reconciliation. No automatic gap clearance or public feed action
may rely on prefix-only evidence.

**D3 PARTIAL, A3 PARTIAL, release HOLD.**
