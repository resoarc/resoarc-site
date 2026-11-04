# TrapNet v0.59: B2 bounded Cowrie runtime & inode containment acceptance

**Status: isolated component experiment. Public release HOLD.**

## Why this exists

Previous Cowrie evidence already covered the 16MiB ext4 ENOSPC and full
private-var backup, SIGKILL, remount and container recreation. However,
inspecting intended Docker flags alone does not prove that the non-root
runtime really lacks capabilities or that its root filesystem rejects writes.
A block-capacity test also does not prove an independently bounded **inode**
budget. Both were still listed as open B2 technical subconditions.

## Added independent tests

Run `lab/real_cowrie_b2_boundaries.py` only on a disposable authorized
Linux CI runner as root, with the pinned immutable Cowrie image
`sha256:17191d19f02bb9b9d9ebda0578f96bd13f764c10a7b5c11a1b50f6eb6c973a9a`.

The lab reuses the *real*, network-disabled Cowrie + isolated 16MiB ext4
backup/remount/recreate test, adding an opt-in runtime hook to examine the
actual newly recreated container:

- Pinned image ID, rootfs read-only, UID/GID 999:999, capabilities ALL
  dropped, `no-new-privileges`, not privileged.
- PID limit 64, memory/swap 192MiB, CPU 0.3, Docker local log caps,
  exactly one bounded private var mount, constrained /tmp tmpfs.
- Docker network mode `none`, no published host port, no Docker socket.
- Inside the actual non-root Cowrie container, read `/proc/self/status`
  to verify CapEff=0 and *attempt* a write to the read-only root
  (`/cowrie/.b2-probe-should-not-exist`) which must fail.

After the real Cowrie has been stopped, the lab creates a **second**
disposable 16MiB ext4 image with only 128 inodes. It must:

1. Be mounted separately from the Cowrie-private-var device and have a
   small, bounded inode count.
2. Exhaust actual inodes with small synthetic files while block capacity
   remains available, observing `ENOSPC` and `f_ffree==0`.
3. Remove only an explicitly named synthetic old fixture, prove inode
   capacity returns and a new file is writable.
4. Retain the independently hashed newer fixture unchanged and make no
   automatic historical all-clear claim.
5. Unmount and delete its image even on failure. The original Cowrie
   trial also cleans up its own Docker container, ext4 image and mount.

No real attack logs, private signing keys, host credentials, user identifiers
or production container names are uploaded. The CI artifact contains **only**
categorical check counts and public safe flags.

## Genuine limitations

The reusable lab's loop-backed ext4 files still live on a shared host disk.
This is **not evidence of independent production-quality physical storage**.
The explicit deletion test proves inode release and retention of a newer
synthetic file. It is **not** a complete real log rotation / personal-data
retention-deletion policy; E1 must cover that separately.

Before B2 can receive formal PASS, the deployer must provide a verified
independent/quotad production log volume, inode and size monitoring, a
bounded backup and restore plan, rollback owner approval, and actual
production-equivalent review. This experiment neither migrates Cowrie
nor changes the live VPS.

**B2 isolated runtime/storage subtests may be PASS after CI, but the
formal B2 release gate stays PARTIAL. Entire product stays HOLD.**
