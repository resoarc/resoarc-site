#!/bin/sh
set -eu
script=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/install_guardian.sh
scratch=$(mktemp -d "$HOME/.trapnet-install-trial-XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
root=$(CDPATH= cd -- "$(dirname -- "$script")/.." && pwd)
(cd "$root" && go build -trimpath -o "$scratch/source" ./cmd/guardian)
"$scratch/source" -h > "$scratch/help-output" 2>&1
digest=$(sha256sum "$scratch/source"|cut -d' ' -f1)
prefix="$scratch/owned"
sh "$script" install "$scratch/source" "$digest" "$prefix" >/dev/null
[ -f "$prefix/guardian" ] && [ -f "$prefix/guardian.install.sha256" ]
"$prefix/guardian" -h > "$scratch/installed-help-output" 2>&1
if sh "$script" install "$scratch/source" "$digest" "$prefix" >/dev/null 2>&1;then echo 'overwrite accepted' >&2;exit 1;fi
printf 'synthetic-antirollback' > "$prefix/guardian-state.json"
printf 'tamper' >> "$prefix/guardian"
if sh "$script" remove "$prefix" >/dev/null 2>&1;then echo 'tampered removal accepted' >&2;exit 1;fi
rm -f "$prefix/guardian" "$prefix/guardian.install.sha256"
sh "$script" install "$scratch/source" "$digest" "$prefix" >/dev/null
sh "$script" remove "$prefix" >/dev/null
[ ! -e "$prefix/guardian" ] && [ -e "$prefix/guardian-state.json" ]
if sh "$script" install "$scratch/source" "$digest" /tmp/outside-home >/dev/null 2>&1;then echo 'outside HOME accepted' >&2;exit 1;fi
if sh "$script" install "$scratch/source" aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa "$scratch/bad" >/dev/null 2>&1;then echo 'bad digest accepted' >&2;exit 1;fi
echo 'Linux REAL Guardian install/execute/uninstall/tamper/outside-home/state-retention PASS'
