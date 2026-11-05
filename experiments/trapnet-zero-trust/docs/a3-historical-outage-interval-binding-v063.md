# TrapNet v0.63: historical outage interval sidecar, offline verification

Status: **experimental evidence tooling only. A3 formal PARTIAL, D3 PARTIAL, E3 TODO and general public release HOLD.**

## Why the v0.1 signed coverage_gap is not sufficient alone

The existing Sensor's signed `coverage_gap` is a finite reason category plus an event ID and current observation time. It **does not sign historical outage start/end timestamps**. After the 2026-11-05 VPS stop, merely sending `recovery_gap` today could not establish when observation stopped or whether attacks occurred while offline.

## v0.63 addition

The new `outageproof` package defines a separately signed operator sidecar with:

- explicit UTC outage start, end, and later operator attestation time;
- `observation_unknown_not_zero` as the only permitted semantic label;
- only a finite categorical source (`docker_state_guard_metadata`) and SHA256 of a small **redacted** source manifest;
- the exact Sensor node ID, report event ID, canonical signed Sensor report SHA256, and canonical signed HUB receipt SHA256;
- an Ed25519 signature from a pinned **third**, distinct operator key.

`outageproof.Verify` verifies the real Sensor signature and its original HUB-receipt freshness window, exact signed HUB receipt against an explicitly pinned HUB public key, the separate operator signature and chronology, and the original redacted source-manifest bytes. All three pinned public keys must differ.

The read-only `cmd/gap-interval-audit` verifies canonical, bounded JSON evidence files and outputs only fixed categorical statuses. It never accesses a live HUB, writes logs, rotates keys, sends a report or clears HOLD. The exact required CLI inputs are:

```text
gap-interval-audit -report signed-recovery-gap.json -hub-receipt signed-hub-receipt.json \
  -operator-interval operator-signed-interval.json -source-manifest redacted-source-manifest.json \
  -sensor-pub trusted-sensor-public.hex -hub-pub trusted-hub-public.hex \
  -operator-pub trusted-operator-public.hex
```

The operator's private key stays outside the repository. There is **no automatic signing** of this historical incident. The API `outageproof.Sign` is only for an operator with their own private key and independent knowledge of the evidence. Do not reuse a production Sensor/HUB root key as an operator key.

## Proof versus nonproof

- `cryptographic_binding_verified=true` means only that the existing signed Sensor report, signed HUB receipt and separately signed operator interval are mutually bound to the supplied source manifest.
- It does **not** establish that the operator's outage timestamps are accurate, that the interval had zero attacks, that the Sensor was allowlisted and unrevoked at delivery, or that no earlier/later observation gaps exist.
- It does **not** establish closed independent Witness history, hardware failure survival, independent human review, or approval to distribute Guardian.
- The read-only public incident manifest `release/live_gap_20261105_v062.json` explicitly reports no signed Sensor gap or independently witnessed acknowledgement for the incident. Do not alter those flags until authentic signed evidence actually exists.

## Verification

```sh
cd experiments/trapnet-zero-trust
go test -race ./outageproof ./cmd/gap-interval-audit -count=1
go vet ./outageproof ./cmd/gap-interval-audit
```

Tests use three deterministic **synthetic-only** private keys, never production secrets, and cover source/interval/report/receipt tampering, key substitution, role-key collisions, stale Sensor-to-HUB admission, future/backdated assertions, duplicate/unknown JSON keys, symlinks and oversize evidence.

**Next genuine A3 decision:** an authorized operator must verify source metadata, create a real current-time `recovery_gap` signed Sensor event and durable signed HUB receipt **without claiming missing events were recovered**, separately sign the exact interval using a legitimately controlled third key, then arrange a closed, externally pinned Witness audit. No independent operator or actual signed outage sidecar was obtained by this PR.
