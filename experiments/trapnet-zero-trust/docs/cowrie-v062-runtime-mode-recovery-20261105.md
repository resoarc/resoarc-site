# TrapNet v0.62: Cowrie log-mode recovery and observed monitoring gap

**Status: runtime remediation applied on the operator's VPS on 2026-11-05; whole-network public release HOLD.**
This document contains no attack content, source IPs, private server names, secrets, or private backup archives.

## Incident and what was actually measured

- 2026-11-05 10:12:20 JST: the active `cowrie.json` had file mode **0664** and was modified. The log directory remained 0700, owned by the Cowrie service UID. Previously rotated log files were 0600.
- 2026-11-05 10:12:50 JST: Cowrie's last recorded stop time. The existing fail-closed guard reported `bounded_storage_or_log_permission_drift`, and `stop.sh` stopped Cowrie, Edge and Web.
- 2026-11-05 22:39:49 to 22:39:52 JST: systemd safe-start restored Web, Cowrie and Edge. Post-start `boundary_check.py`, bounded-storage guard, log-mode preflight and Edge-to-Cowrie connectivity passed.
- **At least ~12 hours 27 minutes of missing live observation must be treated as an unverified gap**, never as zero attacks. The signed HUB observation-gap chain was **not** updated or independently witnessed by this incident work.
- The new active log's exact mode 0664 is observed; the precise software operation creating or chmodding it is not proven. It may occur during file rollover, but that remains a hypothesis.

## Hardened behavior

`ops/log_mode_recovery_v062.py` is a narrow runtime normalization step before the existing fail-closed bounded-storage check.

- Requires an existing dedicated bounded mount that differs by filesystem device ID from the host root.
- Requires the raw-log directory to be regular, service-owned (UID999) and mode 0700, with **no symlink in its path**.
- Requires every directory entry to be a regular file, owned by service UID, with one hardlink and mode 0600, except exactly `cowrie.json` with mode 0664.
- If and only if the active file matches that **known** condition, an explicit `--repair-known-mode` call opens it with no-follow, verifies pinned inode/device and file metadata, then performs `fchmod(0600)`. No raw log bytes are read.
- Without `--repair-known-mode`, the same anomaly yields HOLD (diagnostic dry-run); all unknown modes, ownership or file-type changes also yield HOLD.
- The existing `guard.sh` still triggers protective shutdown when the repair or the bounded-storage inspection fails. A successful repair leaves a constant-code syslog event.
- The operator protected the pre-change `guard.sh` privately before the atomic edit, and did not deploy raw backup data to GitHub.

## Evidence

- 14/14 synthetic POSIX tests passed on an authorized isolated Linux filesystem; Windows validated 6 platform-neutral tests with 8 POSIX tests intentionally skipped.
- The actual VPS dry run detected one candidate, returned HOLD and did not modify it. An explicitly approved repair changed the single 0664 active log to 0600.
- The original log permission/ownership checks, mount gates, isolation checks, internal Edge-to-Cowrie reachability and the manual resource guard check passed after the safe-start.
- No public port or firewall policy changes, data deletion, key rotation, or automatic release-state promotion were performed.
- Independent human verification of the incident and preventive fix has **not** occurred.

## Still missing for formal release

- **A3**: append an authenticated signed observation-gap report to HUB/Witness, independently verify the missing epoch and receipt, then rehearse durable multi-event catch-up.
- **B2**: prove real host crash/remount recovery and independent change review; a bounded loop-backed ext4 image is not a physically independent disk.
- **E1**: verify actual backup retention/deletion and personal-data inventory, and investigate underlying log rollover behavior at the image/source level.
- **E3**: independent person-led review and Critical/High closure.

Release scorecard remains at **technical PASS 3 / PARTIAL 15 / TODO 2**, **formal PASS 1 / PARTIAL 17 / TODO 2** until an independent gate decision is recorded.
