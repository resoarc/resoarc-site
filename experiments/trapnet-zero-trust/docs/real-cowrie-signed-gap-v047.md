# TrapNet v0.47: real isolated Cowrie ext4 -> signed missing-coverage report -> HUB

**Status: DRAFT / release HOLD.** No live VPS Cowrie, production log,
public port, external communications or client devices are modified.

## Exact provenance and scope

The GitHub Actions job pulls only
`cowrie/cowrie@sha256:69e3317c6ecf8811d18faecb8a2fcedee0af1f0f864b50de07b688c7409f515c`
and asserts that its local immutable image ID is
`sha256:17191d19f02bb9b9d9ebda0578f96bd13f764c10a7b5c11a1b50f6eb6c973a9a`.
Anything else fails before creating trial resources.

In a private temporary directory, an operator-triggered privileged CI lab
mounts an **isolated 16 MiB loop-backed ext4 image**, creates an ephemeral
Cowrie container with `--network none`, no host ports, read-only root,
non-root UID, no added capabilities, no new privileges and bounded resources.

The script triggers an SSH connection **from inside** the disposable
container and verifies real Cowrie event JSON exists. It backs up all private
var state, fills only the disposable 16 MiB ext4 filesystem to ENOSPC and
confirms the pinned health checker refuses the full volume.

The new, optional `failure_hook` and `recovery_hook` in the existing
ext4 rehearsal execute the following additional workflow:

1. While the real Cowrie ext4 volume is full, create private disposable
   signing keys in the test lab. Check that the **real Cowrie log** health
   result is `storage_full`, initially without transmitting anything.
2. Explicitly arm the lab-only signed Sensor. The HUB is offline, so the
   immutable signed `coverage_gap` is preserved in its private disk outbox.
3. Kill only the disposable Cowrie, restore and verify the SHA-256 manifest
   of its whole private-var tree, unmount/remount ext4, recreate Cowrie
   from the exact image, trigger fresh SSH events, and confirm log health.
4. Start the **real Go HUB** bound only to `127.0.0.1:8788`.
   Re-submit the original signed report, require HUB's fsynced ledger
   receipt and confirm the exact original evidence is persisted.
5. Gracefully stop and restart that HUB and verify duplicate submission
   is refused after restart. Restored Cowrie health must **never**
   automatically erase the prior signed gap.
6. Remove all ephemeral Docker containers, loop mounts, test identities,
   private event logs, binaries, and outbox data. The only CI artifact is
   key-free JSON flags, measured capacity and anonymous event counts.

## Intended evidence and limitations

- This uses a **real running Cowrie Docker container**, unlike v0.46's
  synthesized `cowrie.json`, and combines real ENOSPC with signed
  Sensor/HUB transport.
- Linux CI's actual loop-mount support and image digest acceptance are
  prerequisites. If either fails, keep the result HOLD; never quietly skip.
- The 16 MiB sparse loop image is a laboratory method, not a recommended
  production storage design and does not bound the host's backing device.
- An actual power cut, crash-damaged log replay, network-partitioned
  multi-HUB deployment, externally signed receipt and independent Witness,
  offsite backup, personal data deletion, and real household LAN isolation
  are NOT proven by the test.
- This does not auto-send a production alert, clear gaps, publish a rule
  feed or grant release approval.

CLI is intentionally privileged and **should only be used on disposable
CI infrastructure that you control**:

```sh
# CI executes equivalent steps, after exact digest pull and ID validation.
sudo env PATH="$PATH" python3 lab/real_cowrie_signed_gap_e2e.py \
  --image-id sha256:17191d19f02bb9b9d9ebda0578f96bd13f764c10a7b5c11a1b50f6eb6c973a9a
```

A2/A3/A4/B2/B3 remain PARTIAL until their full gate criteria, independent
operational verification and release approvals are met.
