# TrapNet Zero-Trust Network: architectural decision record (2026-10-27)

## Purpose
Turn the existing TrapNet attack-observation experiment into a safe, opt-in public good. Separate observation, knowledge verification and consumption. Scope here is **only the independently testable protocol MVP**, not a production migration.

## Data flow

```
isolated decoy(s) / optional local sensor
         |
         | outbound signed minimal reports (no inbound management)
         v
 [HUB ingest: untrusted] -> [evidence quarantine / validation]
                                    |
                                    v
                        [human reviewed, separate offline signers]
                                    |
                                    v
                        [public immutable warning feed]
                                    ^
                                    |
                      guardian: outbound pull only; verify locally
```

## Hard invariants

1. No centrally initiated network access to clients; no remote shell, arbitrary script, plugin, or command execution in either client.
2. A signature establishes key possession and integrity **only**, not the truth of a report. Single-operator reports must never trigger network-wide blocking.
3. Default Guardian is a read-only warning display. No raw device telemetry is needed to subscribe.
4. Server-supplied feed is parsed as inert data using a versioned allowlist schema. Unknown content is rejected and high-impact actions are not expressible.
5. Software updates and warning feeds have **separate trust roots**. Release keys must not reside on HUB; move to threshold/offline TUF before wider distribution.
6. Sensors open inbound ports only in dedicated decoy environments with inbound/egress ACLs; no routes to trusted LAN or management hosts.
7. Sensor enrollment is allowlisted and revocable; add independent-operator reputation and corroboration to resist Sybil/data-poisoning attacks.
8. Avoid universal or reversible fingerprinting of participants. Public documents must state exactly what is sent and how long it is retained.
9. Central outage causes lack of fresh feed, not a fail-open command channel or denial of normal PC work.

## Distinct claims

- We can verify **who signed** the observation and whether bytes changed. We cannot cryptographically prove that the observation happened without trusted measurements / independent corroboration.
- Even multiple real observations can be deliberately induced by an attacker. Correlation is not attribution.
- Using a single VPS for ingest and analysis is acceptable only for a local lab; signing and release authority remain separate even in the prototype.

## Release gates

- Pre-alpha (this prototype): localhost only, synthetic or manually classified report, no auto response.
- Alpha: third-party audit; enforceable and tested isolation; public threat model; telemetry/PII impact assessment; cross-platform signed builds; recovery exercise.
- Beta: corroboration across *independent owners*, rejected-poisoning scenarios, public transparent append-only warning feed, operational key rotation and revocation.
- General release: matured secure update architecture, monitoring and incident response, documented user consent and stop/delete controls, acceptable false positive rate.

## Reference designs
- The Update Framework: https://theupdateframework.io/
- STIX / TAXII: https://oasis-open.github.io/cti-documentation/
- NIST SP 800-207 Zero Trust Architecture: https://csrc.nist.gov/pubs/sp/800/207/final
