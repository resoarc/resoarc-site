# Cowrie persistent bounded storage: release migration gate

**Status: DRAFT / HOLD.** This is an operator runbook for a future change,
not an instruction to deploy to production, and not evidence that real Sonar
network segmentation, source signing or the Guardian public beta is ready.

## Why this gate exists

The current VPS Cowrie `/opt/resoarc-trapnet/var` is a host bind mount on a
large shared root filesystem. A container memory limit or Docker stdout log
rotation does **not** cap Cowrie's JSON event files. A full root disk could
impact unrelated services. A writable, bounded and **persistent** log
filesystem with a defined retention policy is a release prerequisite.

No unverified/absent events may be advertised as "zero attacks".

## What is tested (offline only)

`sonar/cowrie_ext4_persistent_rehearsal.py` creates a unique 16MiB ext4
loop image **inside its disposable staging directory**. It never accesses
production Cowrie mounts. The immutable preinstalled Cowrie image is run with
`--network none`, no published ports, a read-only root, dropped capabilities,
non-root UID, and CPU, memory, PID and Docker-log limits.

The rehearsal confirms: initial log append and healthy bounded filesystem,
ENOSPC in the isolated image, health-check HOLD, an offline snapshot of the entire synthetic Cowrie private var tree with
SHA-256 manifest, SIGKILL and container removal, verified full-tree restore,
ext4 unmount/remount, fresh Cowrie container identity, and subsequent log
append while the new file remains within the dedicated disk capacity.
The result is private metadata only. The script cleans up its temporary disk,
mount and containers in all reachable normal/error paths. Review the cleanup
before running as root.

**Offline manual execution only (authorized Linux test host):**

```sh
cd experiments/trapnet-zero-trust/sonar
python3 -m unittest discover -s . -p 'test_*.py' -v
# After confirming root permissions, free space, immutable local image ID:
# sudo python3 cowrie_ext4_persistent_rehearsal.py --image-id sha256:<PREINSTALLED-IMAGE-ID>
```

This 16MiB loop file is **not** the preferred production layout. In
particular, a sparse image backed by the shared host filesystem can still
consume that host's space; the rehearsal proves a bounded container-visible
filesystem, not a failure-independent separate physical disk.

## Proposed production change (not yet implemented)

1. **Freeze the scope.** Capture the running image digest, actual Docker
   mounts, non-root UID/GID, SELinux/AppArmor context, allowlisted ports and
   attached network. Inventory every file under the live private var,
   including rotated JSON logs and SSH host keys, without publishing contents.
2. **Choose truly independent storage.** Prefer a dedicated persistent block
   device/filesystem with an enforceable capacity limit, alerts and safe
   filesystem journaling. Alternatively use a strongly verified project quota
   and reserve space for other VPS services. A shared filesystem without
   effective quota does not pass the gate. Design backup capacity separately.
3. **Backup first.** Stop only Cowrie during a separately approved maintenance
   window, take a bounded, metadata-preserving offline backup of *all* private
   var files and ownership/permissions, record SHA-256 and an independently
   stored signed manifest. Check the backup is readable before changing
   Docker. Never copy sensitive raw Cowrie data to public repositories.
4. **Stage cutover with no public listener.** On an isolated cloned service,
   mount the proposed persistent storage and restore the full var tree,
   preserve UID/GID and security labels, re-create Cowrie with exactly one
   canonical writable var mount, no host-port mappings, minimal capabilities.
   Validate data, restart persistence, filesystem cap and health gate.
5. **Fault and rollback rehearsal.** Run disk-full, incomplete-log, SIGKILL,
   full container removal/recreate, filesystem remount, backpressure and
   backup restore. Confirm accepted log prefixes or explicitly mark a gap.
   Roll back to the preserved original host bind on any failure.
6. **Guarded live migration, not automated.** Require explicit operator
   approval, independent human security review and incident rollback
   ownership before changing the real deployment. Abort if observations,
   permissions or expected immutable image IDs differ from the approved
   manifest.
7. **Post-cutover monitoring.** Verify capacity, inode exhaustion, separate
   free-space alarm, log rotation and retention (including personal-data
   deletion), backup integrity, service liveness and raw-log integrity
   independently. Keep unverified epochs in HOLD; do not automatically
   release them on restart.

## Acceptance gates for B2/B3/A4

- [x] Read-only checker rejects shared/unbounded live log filesystem.
- [x] Real Cowrie on unique bounded persistent ext4 loop filesystem survives
      unmount/remount and disposable container recreation.
- [x] ENOSPC makes the log-health check fail closed.
- [x] Fail-safe isolated offline backup/restore preserves the entire
      synthetic Cowrie private var tree and its hash manifest.
- [ ] Production-quality independent storage layout with demonstrated
      capacity/inode limits, log rotation and off-volume backup.
- [ ] Explicit permissions/UID/GID and SELinux label round-trip verification
      across a different host and encrypted off-host backup.
- [ ] Recovery from real host crash/power loss, offline fsck and corruption.
- [ ] Log-source/HUB signed gap advisory, independently witnessed release.
- [ ] Operator-approved live cutover, human review and rollback exercise.

These checks are a necessary subset of the broader TrapNet release gate.
Do **not** mark the overall B2/B3/A4 as complete or publish an installable
Guardian/Sensor solely because this isolated rehearsal succeeds.
