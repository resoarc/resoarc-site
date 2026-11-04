<!-- SPDX-License-Identifier: MIT -->
# TrapNet v0.61: Cowrie host metadata preflight

Status: experimental operator diagnostic. Public release HOLD.

## Scope
ops/host_preflight.py evaluates current Docker inspect settings and local
log-directory metadata without opening event contents or modifying services.
It checks container identity, nonroot execution, read-only rootfs, dropped
capabilities, process/CPU/memory limits, network bindings, volume layout,
file ownership and modes, and whether logs share the host root device.

The output includes only static finding codes and counts. There are no
filenames, network addresses or raw events in the result.

## Example (authorized Linux host only)
python3 experiments/trapnet-zero-trust/ops/host_preflight.py --container trapnet-cowrie --expected-container trapnet-cowrie --log-dir /path/to/log-directory --expected-network trapnet-sensor-strict

An operator may use --inspect-file with private Docker inspect JSON instead.
Such JSON can contain sensitive configuration and must not be published.

## Important limits
The tool never claims an enforced byte or inode quota, successful restoration,
data-retention compliance, independent review or permission to deploy.
Even if profile_result is PASS, formal_release remains HOLD.
A different filesystem device does not prove independent physical storage.
The inspection is point-in-time, and may race concurrent file changes.

## Regression test
python3 -m unittest discover -s experiments/trapnet-zero-trust/ops -p 'test_*.py' -v

GitHub Copilot CLI supplied separate adversarial review suggestions around
wrong-container inspect metadata, missing effective limits and deceptive
mount/permission configurations. This does not replace human review.
