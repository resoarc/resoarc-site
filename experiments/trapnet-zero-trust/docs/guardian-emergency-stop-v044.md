# Guardian offline emergency-stop guard v0.44

**Status:** Experimental draft. No production release, automatic remote stop,
process kill, firewall modification or update service is implemented.

## What changed

The read-only Guardian CLI checks `<value-of--state>.stop` immediately after
command-line parsing and **before opening feed, signer policy or other files**.
When the marker exists, Guardian refuses to display even a correctly signed
feed. It does not remove, replace or automatically clear the marker. A malformed
marker, symlink or unreadable marker also fails closed.

### Operator dry-run on an isolated local state

```sh
mkdir -m 700 /tmp/trapnet-guardian-lab
touch /tmp/trapnet-guardian-lab/demo.state.stop
# Using the Guardian test binary and test feed/policy only:
./guardian -state /tmp/trapnet-guardian-lab/demo.state -feed /tmp/test-feed.json \
  -policy /tmp/test-policy.json -rootpub /tmp/test-root-public.hex
# EXPECT: nonzero exit before reading the feed; no remote side effects.
```

For a genuine incident, an operator would stop any owned scheduled runner
outside this CLI, create the stop marker in the actual state directory, and
revoke relevant signing keys through an independently approved procedure.
**Never use this test path as an instruction to modify production without
inventory, authorization and rollback evidence.** Removing the marker is
an explicit manual change, not a proof that compromised data is healthy.

## Security boundary

- The Guardian source tests examine production Go imports for networking,
  process execution, syscall/unsafe/plugin entrypoints and explicit
  `os.StartProcess` usage. Negative tests show these are refused.
- Signed warning text is printed as inert text; it is not passed to a shell,
  network client, firewall API, installer, AI action, or subprocess.
- The source audit is a narrow, machine-checkable regression gate. It is
  **not** transitive dependency analysis or proof of no egress on a live host.
- Existing native Linux/Windows Guardian acceptance and Root rotation tests
  are separate and must pass at the exact candidate commit.

## Gate E2/E4 remaining steps

1. Verify a native Guardian binary on Windows/Linux/ARM64 under network
   capture and process-start auditing while feeding malicious signed text.
2. Confirm a production-equivalent **scheduler/launcher** honors the stop and
   doesn't re-enable it after power outage or updates.
3. Perform actual offline Root signer revocation and roll-forward/rollback
   with independent operators and verify no orphaned clients.
4. Capture signed human approval, emergency contacts and external review.

These are **not** complete merely because the unit tests pass.
