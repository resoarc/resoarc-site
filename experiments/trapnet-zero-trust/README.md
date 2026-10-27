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
attacker able to rewrite both can forge a consistent history. Independent externally pinned witness checkpoints are implemented in the experimental `cmd/witness` (see [v0.4 witness runbook](docs/v0.4-witness.md)). Strong multi-party transparency, signed root key rotation, operator-independent
attestation, Sybil resistance, privacy audits, recovery tooling, 5-node lab,
checkpoint retention/compaction, and a TUF-based update path remain unbuilt.
A deleted revocation state file can also weaken rollback resistance unless
operators protect backups and trust roots. Recovery must never blindly reset
checkpoints. **No public release or automatic blocking is permitted.**


## v0.4: off-HUB witness with independent tip pinning (experimental)

`cmd/witness` signs stable, copied HUB ledger snapshots **off-HUB**, chains the signed history, and refuses continuing without a previously pinned witness tip. `verify` also requires an independently saved latest tip. It does not attest to observation truth and does not authorize public Sensor enrollment or automated blocking. See [offline operations, recovery and attack tests](docs/v0.4-witness.md).


## v0.4: independently witnessed evidence (experimental)

The offline-only cmd/witness utility computes the same SHA-256 chained ledger digest as HUB, verifies a closed snapshot and signs witnessed row boundaries **on a separate host**. Witness history is signed, sequential, hash-linked and designed to live outside HUB; operators must separately pin the latest history tip to detect rollback. Newer rows are unwitnessed until the next attestation. No trusted time source, auto witnessing, key rotation or automatic defense decisions are included.

An in-memory five-identity adversarial regression test exercises replay, forged reports, old timestamps and static revocation. **This is not a five-host deployment and does not establish independent operator identities or Sybil resistance.** See [v0.4 off-HUB guide](docs/v0.4-offhost-witness.md). Public deployment remains HOLD.
