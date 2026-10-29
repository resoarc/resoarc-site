# TrapNet v0.49: HUB receipt × independently signed Witness history cross-audit

**DRAFT, public release HOLD.** This is a purely **offline read-only audit**
that requires a closed snapshot of the HUB ledger, an off-HUB Witness
history and a **separately pinned** history tip and public key. This does
**not** contact the HUB or automatically clear the outstanding gap.

## What this audit proves

Using three independently provided public keys (Sensor report, HUB receipt,
Witness checkpoint) and the externally fixed Witness history tip:

1. Verify the original Sensor's Ed25519-signed report, **even if historical**
   (do not replay or resign it with a fresh timestamp).
2. Verify the HUB's Ed25519-signed receipt refers to that exact full signed
   Sensor report, claimed ledger tip/row count, HUB identity and time.
3. Verify the off-HUB Witness's signed append-only checkpoint history against
   the externally pinned history tip. Refuse missing, changed or shortened
   Witness history.
4. Validate the closed ledger copy against its checkpoint and ALL the
   previously witnessed row boundaries.
5. Recompute the HUB's rolling digest at **exactly the row count claimed
   in the receipt**, even if the independent Witness checkpoint includes
   later reports. Require a matching full signed report and original
   received_at timestamp in the first N records.
6. Reject signer-key reuse, wrong or forged keys, altered report, altered
   checkpoint, missing event, wrong receipt tip, maliciously modified
   history and unreadable/symlinked/oversized ledger.

A successful audit yields only
`RECEIPT_WITNESS_AUDIT_PASS (historical receipt only; not an observation all-clear)`.

## Offline operator flow (requires two *actually separate* custodians)

The HUB operator sends a **stopped-HUB snapshot** made with `cmd/snapshot`
plus the signed HUB receipt and original signed report to a separately
operated Witness machine. The Witness custodian must use their own key and
privately retained history; their custody must not depend on HUB ownership.
Publish/anchor the latest Witness tip **outside** the HUB and Witness state
directory. Transferring arbitrary live/unverified logs is not recommended.

Then, on the independent Witness auditor machine only:

```sh
./receipt-audit \
  -ledger /independent/snapshot/ledger.jsonl \
  -history /independent/history.jsonl \
  -witness-tip <independently-pinned-history-tip> \
  -witness-pub /independent/trusted-witness-public.hex \
  -hub-pub /independent/trusted-hub-public.hex \
  -sensor-pub /independent/trusted-sensor-public.hex \
  -report /independent/original-signed-report.json \
  -receipt /independent/hub-signed-receipt.json
```

Failure exits nonzero, does not export raw content or edit evidence. A
successful historical receipt **does not** establish that observation had
no gap, that an attack was prevented, or that a future report will be
delivered. No automatic all-clear or Guardian command is introduced.

## Reproducible CI evidence

The regression suite checks valid three-signature cross-audit as well as
forged signed receipts, wrong snapshot digest, missing event, bad original
Sensor key, wrong and reused Witness key, altered Witness history and a
history tip that was rolled back. The integration lab builds real
`keygen`, `sensor`, `hub`, `snapshot`, `witness` and
`receipt-audit` CLI binaries and performs the chain on disposable offline
copies. It proves the code path, **not two real independent operators**.

## Still missing

- A second, genuinely independent host/organization maintaining its
  Witness signing key and history under separate permissions and policy;
  a CI test whose ephemeral keys reside on one runner is not independence.
- Attested immutable off-host retention of the Witness tip with
  recovery after loss, reboot, timestamp divergence or network partition.
- Full incident epoch closure and durable multi-event outbox for outages
  longer than the Sensor report's 10-minute freshness window.
- Signed key rotation/revocation, privacy and independent human security
  audit before production operation.

**D3 remains PARTIAL and A3 remains PARTIAL. Release HOLD.**
