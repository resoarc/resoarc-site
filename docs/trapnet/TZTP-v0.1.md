# TrapNet Zero-Trust Protocol (TZTP) v0.1 — proposed, not a production standard

Status: **experimental local-only prototype / design review** (2026-10-27).

## Roles
- Sensor: emits signed, *untrusted* observation reports to an ingestion API; never accepts remote shell commands.
- HUB: verifies syntax/signatures and enqueues evidence as **received_unverified**. AI correlation is advisory. It cannot sign software updates.
- Guardian: verifies locally pinned, signed, short-lived, *informational* warning feeds. Default no telemetry, network listener, firewall modifications, or arbitrary scripts.

## Directionality
Sensor -> HUB (outbound request only).
Guardian -> public signed feed (outbound pull only).
There is no HUB -> client initiated connection, and no Sensor <-> Guardian session.

## Report schema
A Report object has exactly seven fields:
- schema: `trapnet.report.v0.1`
- node_id: first 16 bytes of SHA-256(Ed25519 public key), lowercase hex
- event_id: random 16-byte hex identifier
- observed_at: timestamp, <=10 min old and <=2 min into future at ingress
- kind: bounded category string (not a command)
- target_port: 1..65535 for normal network events; 0 only for the reserved signed `coverage_gap` report
- campaign_fingerprint: 32-byte SHA-256 of **nonpersonal characteristic** (never hash raw IPv4 as a false anonymity technique).

SignedReport wraps `report` and `signature`, a 64-byte Ed25519 signature in hex over Go's canonical struct serialization of the report in the proof-of-concept. **Canonical JSON must be formally specified and test vectors published before interoperable clients**. Do not assume arbitrary JSON canonicalization agrees with Go's encoding.

## Experimental signed observation-gap extension (2026-10-29)

The reserved `kind=coverage_gap` is **not a network attack**. It uses
`target_port=0`, a SHA-256 fingerprint of a strict six-item missing-coverage
category, and the existing signed Sensor identity and replay-protected HUB
ledger. Only the allowed reason categories can be encoded, no arbitrary
narratives or raw IP/log contents.

The offline correlation tool treats an authenticated coverage-gap report
as an unreconciled observation interval and refuses to generate case
summaries. Restored logging does not automatically establish a healthy
interval, clear the gap or publish a feed. The Sensor's manual
`-gap-reason` option remains **loopback-only**, and automated durable
delivery, externally witnessed resolution and operator review are not
implemented. See `experiments/trapnet-zero-trust/docs/signed-observation-gap-v042.md`.

## Trust, privacy and poisoning safeguards
- Node allowlist and revocation before ingest; a valid signature shows key possession, not event truth.
- Reject unknown schema fields, large bodies, invalid timestamps, invalid signature, unknown node, replayed event IDs.
- Count independent *operators*, not node IDs; even 100 independent signatures cannot by themselves prove malicious intent.
- Verified traffic or anomalies must not automatically become a global blocklist.
- Personal PCs run Guardian-only by default and send no observation telemetry; do not promise anonymity merely because no identifying fields are sent.
- A compromised Sensor must lack paths to trusted LAN and should be rebuildable. No general household router port forwarding during pre-alpha.

## Warning feed v0.1
SignedFeed wraps a Feed with `schema`, monotonic `version`, `issued_at`, `expires_at`, and inert `warnings` objects containing category and summary only. Guardian pins an offline warning-signing public key, checks expiry and local monotonic state, and displays text only. This is **not TUF** and has no remote update support.

## Formal next gates
1. Independently review threat model, telemetry and legal basis.
2. Set secure cross-platform build, detached release signing / TUF-based updating, transparent evidence review.
3. Add operator-independence verification, durable rate limits, revocation and interop test vectors.
4. Run isolated 5-node adversarial tests including fake identities, valid-signed lies, replay, compromised HUB, false feed, revocation and recovery.
5. Only then consider a publicly reachable ingress with mTLS/TLS and quotas.

Do not publish collector IP or ports from this experimental branch.

Review & volunteer coordination: https://github.com/resoarc/resoarc-site/issues/31
References: https://theupdateframework.io/ | https://csrc.nist.gov/pubs/sp/800/207/final
