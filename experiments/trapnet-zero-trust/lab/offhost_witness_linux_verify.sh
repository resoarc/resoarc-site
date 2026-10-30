#!/bin/sh
# Read-only, off-host signed history verification. No Go private keys needed.
# Usage: sh offhost_witness_linux_verify.sh /handoff-two /public-export /bin-tools
set -eu
test "$#" -eq 3
handoff=$1
public=$2
bindir=$3
test -f "$handoff/handoff-manifest.json"
test -f "$public/history.jsonl"
test -f "$public/witness-public.hex"
test -f "$public/pinned-tip-2.txt"
test ! -e "$public/private.hex"
tip=$(tr -d '\r\n' < "$public/pinned-tip-2.txt")
case "$tip" in
  *[!0-9a-f]*|"") echo INVALID_WITNESS_TIP;exit 3;;
esac
test "${#tip}" -eq 64
"$bindir/witness" -mode verify \
  -ledger "$handoff/snapshot-2/ledger.jsonl" \
  -history "$public/history.jsonl" \
  -pub "$public/witness-public.hex" -expected-tip "$tip" >/dev/null
for n in 1 2; do
  "$bindir/receipt-audit" \
    -ledger "$handoff/snapshot-2/ledger.jsonl" \
    -history "$public/history.jsonl" \
    -witness-tip "$tip" \
    -witness-pub "$public/witness-public.hex" \
    -hub-pub "$handoff/hub-public.hex" \
    -sensor-pub "$handoff/sensor-public.hex" \
    -report "$handoff/signed-report-$n.json" \
    -receipt "$handoff/signed-hub-receipt-$n.json" >/dev/null
done
# Latest Witness history must NOT validate against rolled-back snapshot 1.
if "$bindir/receipt-audit" \
    -ledger "$handoff/snapshot-1/ledger.jsonl" \
    -history "$public/history.jsonl" \
    -witness-tip "$tip" \
    -witness-pub "$public/witness-public.hex" \
    -hub-pub "$handoff/hub-public.hex" \
    -sensor-pub "$handoff/sensor-public.hex" \
    -report "$handoff/signed-report-1.json" \
    -receipt "$handoff/signed-hub-receipt-1.json" >/dev/null 2>&1;then
  echo ROLLBACK_ACCEPTED_HOLD
  exit 3
fi
printf '%s\n' 'CROSS_HOST_WITNESS_2_OF_2_AND_ROLLBACK_PASS'
