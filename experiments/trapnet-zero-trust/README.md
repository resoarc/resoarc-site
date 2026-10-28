# TrapNet Zero-Trust Prototype v0.1 (development only)

**NOT production ready. DO NOT expose this HUB publicly, enable router port forwarding, or deploy on a personal LAN as a decoy.** This source is an isolated protocol proof of concept, not the existing production TrapNet. It intentionally cannot scan networks, listen as a honeypot, block IPs, remotely operate PCs, or auto-install updates.

## Roles

- `sensor`: produces a signed **non-PII synthetic or manually classified observation** to loopback only. It neither opens an inbound port nor captures packets.
- `hub`: accepts a strict signed report schema from pre-allowlisted nodes on `127.0.0.1:8788` only. Persists an append-only JSONL file and responds `received_unverified`. A valid signature is **not evidence of truth**.
- `feed-sign`: separate offline operator signs a short-lived, text-only warning feed. HUB never holds this key.
- `guardian`: checks offline feed signature, expiration, and monotonic version; displays warnings but cannot run commands or change firewall settings.

## Demo

Requires Go 1.23 or later. Run from this directory:

```sh
go test ./...
go run ./cmd/keygen -out sensor-keys
go run ./cmd/keygen -out feed-keys
```

Use `sensor-keys/node.json` to create a local `allowlist.json` mapping `node_id` to `public_key`:

```json
{"REPLACE_WITH_NODE_ID":"REPLACE_WITH_64_CHARACTER_ED25519_PUBLIC_KEY_HEX"}
```

In another terminal, run `go run ./cmd/hub -allowlist allowlist.json -ledger ledger.jsonl`. Then run:

```sh
go run ./cmd/sensor -key sensor-keys/private.hex -kind http_probe -port 80 -fingerprint sample-test-only
go run ./cmd/feed-sign -key feed-keys/private.hex -out feed.signed.json -version 1
go run ./cmd/guardian -feed feed.signed.json -pub feed-keys/public.hex -state guardian-state.json
```

The sample observation is explicitly synthetic. Do **not** misrepresent a demo record as real-world attack evidence.

## Trust boundary / limitations

- Node identity is verified, but **reports are not attested as factual**. The HUB must not generate global defensive actions from these reports.
- An attacker controlling a registered private key can submit fabricated signed reports. Multi-owner correlation, Sybil-resistance, rate-limit persistence, revocation, and evidence review are future work.
- HUB requires a manually curated allowlist and its receiver intentionally refuses remote access. Public TLS/mTLS ingress and operational controls are **not implemented**.
- Guardian is offline/read-only; signed feed isn't an executable policy, and **not** a TUF implementation. Proper TUF and independent root trust are required before software distribution.
- Metadata privacy needs threat modeling: no IPs or payloads in the v0.1 report schema; an unsalted hash of an IPv4 address is reversible and must not be used as a privacy measure.
- Keep private keys out of source control, protect the hub ledger as sensitive metadata, and secure operator workstations. A compromised signing key still endangers feed authenticity.

## Acceptance tests next

1. Build native Windows/Raspberry Pi binaries in CI and test isolated user accounts.
2. Unit/integration-test replay handling across Hub restarts, key revocation, rate limits, malformed oversized payloads, and Guardian rollback.
3. Introduce structured consent, data-retention limits, auditability, and independent validation before any public node enrollment.
4. Establish a real supply-chain update path using TUF, threshold offline keys, transparent releases, reproducible builds, and incident drills.
5. Test sensor isolation with default-deny egress on a dedicated VLAN/VPS and no route to home LAN.

See `docs/architecture.md` for architecture and deployment gates.

## v0.3: local integrity and offline-signed revocation snapshots (experimental)

**Still local-only. Do not deploy to the public Internet or a personal LAN.**

* Each accepted evidence record advances a SHA-256 chain with a separately
  checkpointed row count and digest (`ledger.jsonl.head`). A removed/changed
  record, incomplete tail, missing checkpoint or interrupted checkpoint update
  blocks HUB startup; write/storage failure poisons the running HUB. The
  `ledger.jsonl.lock` file enforces **one HUB writer per ledger**. On a crash,
  investigate and back up ledger + head before manually clearing a stale lock.
* An **existing unsealed v0.1/v0.2 ledger is rejected**, not silently trusted.
  After an offline backup and human review, run HUB once with `-bootstrap-ledger`
  to seal this specific historical ledger as a new baseline. This does **not**
  certify that historical records were genuine. The flag must not be used to
  suppress an unexpected mismatch where a checkpoint already exists.
* An optional **offline-signed, short-lived revocation snapshot** is read on
  every report. Missing, expired, equivocated, malformed, or rolled-back
  snapshots return HTTP 503. The signing private key stays OFF the HUB.
  Strictly increasing versions permit additions and removals only through a
  newly signed complete snapshot; rollback state is persisted on disk.
* Guardian refuses competing updaters via an exclusive `.lock` beside its
  state file. A stale lock stops updates until manually reviewed. It still
  cannot execute remotely supplied instructions or block traffic.

Generate a dedicated offline revocation keypair (do not reuse Sensor/feed keys):

```sh
go run ./cmd/keygen -out revocation-root
go run ./cmd/revoke-sign -key revocation-root/private.hex \
  -version 1 -out revocations.signed.json
# Configure local-only HUB with:
go run ./cmd/hub -allowlist allowlist.json -ledger ledger.jsonl \
  -signed-revocations revocations.signed.json \
  -revocation-root revocation-root/public.hex
```

To revoke a node, use the OFFLINE signing machine to create a new **full**
revocation snapshot with a higher version, then atomically place that signed
file on the HUB. Never transfer the private key to the HUB. Example:

```sh
go run ./cmd/revoke-sign -key revocation-root/private.hex \
  -version 2 -ids 0123456789abcdef0123456789abcdef \
  -out revocations.signed.json
```

### Security limitations requiring further work

This is **not** a complete zero-trust/attested network. SHA-256 chaining only
catches ledger edits against a separately protected head file; a privileged
attacker able to rewrite both can forge a consistent history. External signed
checkpoints/transparency, signed root key rotation, operator-independent
attestation, Sybil resistance, privacy audits, recovery tooling, 5-node lab,
checkpoint retention/compaction, and a TUF-based update path remain unbuilt.
A deleted revocation state file can also weaken rollback resistance unless
operators protect backups and trust roots. Recovery must never blindly reset
checkpoints. **No public release or automatic blocking is permitted.**

## v0.4: external witness against local HUB ledger rewrites (experimental)

`cmd/witness` independently validates a **closed offline copy** of the HUB
ledger plus `.head`, then signs a sequence-numbered, hash-chained checkpoint
into a history **outside the HUB trust boundary**. A separate auditor checks
signature, all previously witnessed row boundaries, and an externally pinned
history tip. The signer rejects continuation unless the prior pinned tip is
supplied. The first record requires explicit `-bootstrap-history`.

This reduces the risk of undetected retroactive ledger edits after a recorded
witness; it does **not** prove observation truth, resist witness-key compromise,
or establish a five-node production-grade system. Read the complete
[offline witness operations and recovery guide](docs/v0.4-witness.md) before
using; do not put witness private keys on the HUB or deploy publicly.

## v0.4 off-HUB witness (experimental)

A separate `cmd/witness` CLI now supports manual signature witnessing of **closed ledger snapshots** on a different host. A witness private key stays outside HUB. The independent history catches post-attestation edits to witnessed rows even if a privileged HUB attacker rewrites both local ledger and `.head`. An independently pinned history tip is required to detect rolling back the witness history itself. There is no automatic witness service or live-replication channel.

See [off-HUB witness security guide](docs/v0.4-offhost-witness.md). Added an in-memory five-identity adversarial test; this is not the planned multi-host isolation test. **No public deployment or Guardian auto-blocking.**

## v0.5 bounded evidence and safe offline snapshot

- `hub -max-ledger-bytes 67108864`: a **fail-closed** 64 MiB default capacity guard. An over-cap append returns HTTP 507; existing evidence is never deleted and replay IDs are not consumed.
- With HUB fully stopped, `go run ./cmd/snapshot -ledger ledger.jsonl -out /secure/export-0001` creates a verified, atomically published offline copy of the ledger and `.head` after acquiring the same writer lock. It refuses a running HUB or stale lock.
- Transfer the closed snapshot to a separately controlled Witness. This is not a snapshot taken while the HUB is accepting requests. See [`docs/v0.5-safe-snapshot.md`](docs/v0.5-safe-snapshot.md).
- **No automatic compaction or recovery yet.** Prior witnessed evidence and replay prevention take priority over freeing space. No production or public deployment.

## v0.6 witnessed ledger generations (development only)

The experimental `archive` package and `cmd/archive-sign` now support separately signed, independently pinned witnessed **older** ledgers. Preparing a new empty active ledger never modifies an older one; HUB restores archived event IDs and reception-time throttling before accepting reports. `ledger.jsonl.archives-required` guards against accidentally starting a new generation without a signed archive manifest, pinned manifest SHA-256 and public archive trust root. See `docs/v0.6-witnessed-ledger-generation.md` for commands and unresolved limitations.

**This is not automatic compaction/rotation or a verified production recovery system.** It scans all archived records on startup (bounded), requires a privileged operator to maintain external pins, and deliberately refuses missing evidence. Old archives may not be deleted. Tests do not establish safe handling of actual power loss, disk-full recovery or an attacker who controls both HUB and its protected service configuration.


## v0.10: Windows LAN-isolation preflight (read-only; HOLD)

The three-physical-host lab found that the Stick PC could initiate a direct TCP connection to a protected management service on the main PC. They share a home IPv4 subnet, so *host-to-host reachability exists* and an adversarial-facing Sensor must **not** be exposed there yet. This finding does not claim successful authentication or compromise.

Run the strictly read-only, single-authorized-RFC1918-target `lab/windows_isolation_preflight.ps1` on Windows to record an IP-redacted JSON verdict. A live connection returns exit **2** (`UNSAFE_DIRECT_REACHABLE`); a failed TCP connection returns exit **3** (`NOT_PROVEN`), **never a false PASS**. Public IPs, address scans, firewall changes, automatic RDP changes and remote commands are not part of this diagnostic. The Windows self-tests run without any network probes.

See [v0.10 network isolation preflight and safe VLAN migration](docs/v0.10-windows-lan-isolation-preflight.md). **Keep the whole PR in Draft; no public enrollment, production deploy or real honeypot on the shared home LAN.**
