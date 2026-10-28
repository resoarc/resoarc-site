#!/bin/sh
# Guardian NONPUBLIC test installer. Digest alone is not publisher authenticity.
set -eu
umask 077
usage(){ echo 'usage: install_guardian.sh install BINARY VERIFIED_SHA256 PREFIX | remove PREFIX' >&2;exit 2; }
[ "$#" -ge 2 ] || usage
mode=$1
case "$mode" in
 install) [ "$#" -eq 4 ] || usage; source=$2; expected=$3; raw_dir=$4;;
 remove) [ "$#" -eq 2 ] || usage; raw_dir=$2;;
 *) usage;;
esac
home=$(realpath -m "$HOME")
prefix=$(realpath -m "$raw_dir")
case "$prefix" in "$home"/*) :;; *) echo 'refused: outside user home' >&2;exit 1;;esac
walk=$home
relative=${prefix#"$home"/}
oldIFS=$IFS; IFS='/'; set -- $relative; IFS=$oldIFS
for part do
 [ -n "$part" ] || continue
 walk=$walk/$part
 if [ -L "$walk" ];then echo 'refused: symlink ancestor' >&2;exit 1;fi
done
bin="$prefix/guardian"
receipt="$prefix/guardian.install.sha256"
if [ "$mode" = install ];then
 case "$expected" in *[!0-9a-fA-F]*|'') echo 'bad sha256' >&2;exit 1;;esac
 [ "${#expected}" -eq 64 ] || { echo 'sha256 length' >&2;exit 1; }
 [ -f "$source" ] && [ ! -L "$source" ] || { echo 'source missing or symlink' >&2;exit 1; }
 actual=$(sha256sum "$source" | cut -d' ' -f1)
 [ "$actual" = "$(printf '%s' "$expected"|tr A-F a-f)" ] || { echo 'sha mismatch' >&2;exit 1; }
 [ ! -e "$bin" ] && [ ! -e "$receipt" ] && [ ! -L "$bin" ] && [ ! -L "$receipt" ] || { echo 'existing install' >&2;exit 1; }
 mkdir -p "$prefix";chmod 700 "$prefix"
 temp=$(mktemp "$prefix/.guardian.XXXXXXXX")
 trap 'rm -f "$temp"' EXIT HUP INT TERM
 cp "$source" "$temp";chmod 700 "$temp"
 [ "$(sha256sum "$temp"|cut -d' ' -f1)" = "$actual" ] || { echo 'copy changed' >&2;exit 1; }
 ln "$temp" "$bin";rm -f "$temp";trap - EXIT HUP INT TERM
 printf '%s\n' "$actual" > "$receipt";chmod 600 "$receipt"
 echo 'Test Guardian installed. SHA-256 is NOT release authentication.'
else
 [ -f "$bin" ] && [ ! -L "$bin" ] && [ -f "$receipt" ] && [ ! -L "$receipt" ] || { echo 'missing or altered install' >&2;exit 1; }
 recorded=$(cat "$receipt")
 [ "$(sha256sum "$bin"|cut -d' ' -f1)" = "$recorded" ] || { echo 'changed binary; manual review required' >&2;exit 1; }
 rm -- "$bin" "$receipt"
 echo 'Guardian removed. State/trust files intentionally retained.'
fi
