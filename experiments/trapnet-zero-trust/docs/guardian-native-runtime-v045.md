# TrapNet v0.45: Native Guardian Linux runtime syscall audit

**Release gate remains HOLD.** This CI test narrows Guardian's C4/E2
verification gap. It is NOT an independent review, not a proof of all code
paths, and not a public signed package.

## What the test actually does

On the ephemeral GitHub Actions Linux runner:

1. Build `guardian`, `keygen` and `feed-sign` from the exact PR checkout.
2. Generate disposable Ed25519 signing keys and create a correctly signed,
   informational feed whose summary contains shell/PowerShell-looking text.
3. Launch the **real Guardian binary** under Linux `strace -f` capturing
   network and process-execution syscalls. The sole permitted syscall in the
   filtered trace is the initial `execve` of the expected Guardian binary.
4. Verify that the feed is printed as literal text, a synthetic side-effect
   marker is never created, and no network syscall or subsequent process
   execution appears.
5. Create an offline `<state>.stop` marker, re-run under the same syscall
   audit, and confirm the Guardian refuses. Remove the marker explicitly and
   confirm a signed informational feed can be read again, still without
   network or process syscalls.
6. Remove temporary binaries, private keys and raw strace logs. Retain only
   the key-free JSON pass/fail summary in CI artifacts.

The CI installs `strace` if missing. Missing `strace`, malformed traces,
unexpected system calls and missing initial `execve` all **fail closed**.
Parser unit tests include fake `socket`, `connect`, `execveat`, extra
`execve`, dropped-trace-like lines and unexpected target paths.

Run only on an isolated Linux test host with Go and strace available:

```sh
cd experiments/trapnet-zero-trust
python3 -m unittest discover -s release -p 'test_*.py' -v
python3 release/guardian_native_syscall_audit.py --source . --output ./guardian-native-syscall-audit.json
```

### Remaining C4/E2 verification

- Audit the exact signed **distribution binary**, not only CI-built test
  executable. Ensure executable source-to-binary provenance.
- Run native Windows network/process tracing, and **native ARM64 hardware**
  analysis (cross-compilation is not a runtime audit).
- Examine transitive dependencies, dynamic loader/plugin injection, hostile
  host privileges and all alternative runtime paths.
- Validate privacy retention/deletion and obtain an independent human
  security review before labeling C4 or E2 PASS.

There is deliberately no network listener, telemetry, remote shell or
automatic firewall action in Guardian.
