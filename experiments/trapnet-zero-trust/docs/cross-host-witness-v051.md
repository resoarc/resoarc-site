# TrapNet v0.51: separate physical host Witness rehearsal

**Status: two-host operational rehearsal PASS. Formal D3 release gate remains PARTIAL. No public release, no production changes.**

This is an **operator-triggered synthetic-only** rehearsal that exercises
the real Go Sensor, HUB, snapshot, Witness and receipt-audit executables
on two actual physical computers, rather than just separate keys on one CI runner.

## Trust model

| Role | Host A: disposable Linux test container on isolated VPS | Host B: Windows Witness machine |
|---|---|---|
| Synthetic Sensor and HUB keys | Created and destroyed within container; never exported | Never receives private keys |
| HUB receipt and closed snapshots | Created with real Go executables in `--network none` container | Receives read-only copies only |
| Witness signing key | **Never present** | Created locally with actual Go `keygen`; deleted after the rehearsal |
| Witness signed history + pinned tip | Receives only the public verification evidence | Signed in two successive stages, independently pinned and retained |
| Inbound public listening ports | **None** | **None** |

Both computers are under the **same owner/operator**. Physical host separation
and non-transfer of the Witness private key are verified, but **administrative
independence is not**. This cannot be called an external independent auditor's
approval or formal D3 PASS.

## Reproducible procedure

1. Use an immutable source SHA, e.g. PR #46 head
   `495a550a8faa3ce198daa1043bfd4d2ad98346a5`.
2. Clone that exact commit into a fresh directory on Host A.
   In disposable `golang:1.23-alpine` builder with `--network none`,
   compile the actual Go keygen/Sensor/HUB/snapshot/Witness/receipt-audit
   binaries and the Windows equivalents of keygen/Witness/audit.
   Mount the source **read-only**, binaries output **write-only intended
   destination**, use `--cap-drop ALL`, `--read-only` and tmpfs build cache.
3. Run `lab/offhost_witness_two_snapshots.py` in a second isolated
   `python:3.12-alpine` container with `--network none`, `--read-only`,
   no privileges, temporary /tmp, read-only executable mount and empty
   output directory. It creates TWO different synthetic signed reports and
   HUB-signed receipts from a real loopback-only HUB, gracefully closes the
   HUB and copies consistent ledger snapshots with 1 and 2 entries. Sensor
   and HUB private keys are destroyed within the container.
4. Transfer only the generated handoff directory plus the **publicly
   reviewable test executables** to Host B. Verify every SHA256 listed in
   `handoff-manifest.json` before operating. Reject a wrong source SHA,
   unexpected files or a private-key-bearing handoff.
5. Run `lab/offhost_witness_windows_acceptance.ps1` on Host B with
   `-Handoff`, `-Output`, `-KeygenExe`, `-WitnessExe`,
   `-ReceiptAuditExe` and `-SourceCommit`. The script:
   - creates a fresh disposable Witness private key locally;
   - signs first snapshot as explicit genesis, pins tip1;
   - signs second snapshot only with tip1, pins tip2;
   - requires both historical HUB receipts to cross-audit against the
     second closed snapshot and Witness history;
   - requires the *rolled-back first snapshot* to be rejected against tip2;
   - exports only history, Witness public key and pinned tip2;
   - destroys the ephemeral Witness private-key directory even on failure.
6. Transfer the export-only-public directory, **not the private key**, back
   to Host A and run `sh lab/offhost_witness_linux_verify.sh
   <handoff> <public-export> <Linux-binary-dir>` on an already isolated,
   closed snapshot. It verifies the Witness-signed two-entry history,
   re-audits both HUB receipts and rejects rollback. The script strips
   Windows CRLF from the single pinned-tip text input before comparison,
   without modifying signed evidence bytes.

## What happened in the 2026-10-30 two-machine rehearsal

- Source: `495a550a8faa3ce198daa1043bfd4d2ad98346a5`.
- Linux producer: success; 2 distinct signed reports, 2 closed ledger snapshots.
- Handoff: 10/10 SHA256 source entries matched after SCP.
- Windows: signed Witness checkpoint sequence 1 and 2 with locally
  generated distinct signer; historical receipts 1 and 2 PASS against
  the latest snapshot; old snapshot FAIL as expected.
- Linux VPS: both historical receipts PASS after transferring only
  Witness signed history, public key and pinned tip; old snapshot
  FAIL as expected. No Witness private key present in transfer directory.
- Early single-checkpoint attempt correctly returned HOLD because a Windows
  CRLF trailing carriage return was included in the Linux text `tip`
  variable. After normalizing only the pinned-tip text, verification
  succeeded and the subsequent two-snapshot runner includes this check.
- All test data is synthetic. The original HUB on Host A, its existing
  loopback port and any Cowrie process were **not** stopped or changed.
  A separate Docker network namespace hosted the disposable Go HUB.

## What still prevents a formal D3 PASS

- Two different machines under **one account owner** do not prove
  two independently administered organizations, approval identities or
  split-signature governance. Need an independent Witness operator and
  authorized, separately protected key/custody.
- Long-haul offsite immutable tip anchoring, witness-key loss/rotation,
  controlled retention/deletion, disaster-power-cut recovery and
  disconnected network partition have not been exercised under the
  independent operational model.
- Third-party human review, Critical/High risk resolution and sign-off
  remain absent.

**D3 formal status: PARTIAL.** A2 and other release gates remain unchanged,
**overall PASS 1 / PARTIAL 17 / TODO 2, release HOLD.**
