# Signed observation-gap reports (experimental v0.42)

**Release status: DRAFT / HOLD.** This introduces a manual, authenticated
failure-report path using the existing signed Sensor -> loopback HUB report
endpoint, not an unattended event collector or a public defense feed.

## Problem

A Cowrie service can continue accepting SSH while its JSON event log is
partially written or absent. Silence is not evidence of safety. Recovered
storage does not prove that every event was captured. The public release
gate must not silently turn an observation gap into a zero-attack interval.

## Message and signature

Registered Sensors use existing `protocol.Report` and Ed25519 signature,
with the reserved shape:

- `schema=trapnet.report.v0.1`
- `kind=coverage_gap`
- `target_port=0` (not an attack target)
- `campaign_fingerprint=sha256("trapnet.coverage-gap.v1:" + reason)`
- `reason` drawn from only:
  `log_unavailable`, `log_corrupt`, `storage_full`,
  `transport_outage`, `recovery_gap`, `unknown`
- random event ID, allowlisted node ID, and time-limited `observed_at`

Raw addresses, passwords, log lines and operator narratives are never sent.
An invalid reason, incorrect port, changed signature, unregistered key or
stale event must be rejected. These notices inherit the HUB's existing
replay, rate and persisted ledger integrity checks.

**What this proves:** someone holding an allowlisted Sensor signing key
submitted a typed claim about *possible missing observations* at one time.
It does not prove the claim is true, detect every gap, attest all previous
intervals, or establish node/operator independence.

## Example: manual local-only operator drill

With an explicit local test identity and an isolated loopback HUB:

```sh
go run ./cmd/sensor -key sensor_private.hex \
    -hub http://127.0.0.1:8788/report -gap-reason storage_full
```

The Sensor accepts only the loopback URL in this experimental version.
The failure category is a one-shot **manual assertion**, not an automatic
read of live Cowrie or an incident alert. If the HUB is unavailable, the
send fails; robust offline queuing and authenticated delivery acknowledgments
are still required.

The HUB appends the report to its normal signed evidence ledger with
receipt time and replay protection. No firewall or Guardian command is sent.

The offline `correlate.Analyze` triage now refuses **all** results when
it sees a valid `coverage_gap` report in the supplied verified ledger
snapshot. It must not count the gap as an attack, score operator confidence,
or present a feed as healthy. There is intentionally no `coverage_ok`,
`recovered` or automatic-clear report type.

## Independent verification and release TODO

- [x] Strict typed gap reason; zero target port only for `coverage_gap`
- [x] End-to-end Ed25519/HUB accepted response, restart replay and
      revoked-key rejection exercised in no-network Go tests
- [x] Offline correlation refuses to produce candidate results on a
      signed gap even when ordinary attack events coexist
- [ ] Wire read-only Cowrie health failure to a persistent, protected
      **offline queue** (loss and crash recovery tests required)
- [ ] Ack, bounded retries, idempotence and expiry controls for delivery
- [ ] Externally signed Witness proof linking gap report to the actual
      source observation window (compromised Sensor case)
- [ ] Handle partitioned HUBs, damaged logs, concurrent reports and
      operator enrolment/exit with incident runbook
- [ ] Require independently witnessed manual epoch reconciliation before
      an advisory feed can resume
- [ ] Privacy/retention review and independent human security review

Do not merge this as general defense-network readiness. The design is
deliberately more conservative than a green "all clear" signal.
