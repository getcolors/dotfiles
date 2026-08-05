#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
expected="$root/test/resources/golden"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

for profile in ubuntu macos; do
  DOTFILES_LIB_ROOT="$root" "$root/green" build \
    -f "$root/test/fixtures/${profile}.yml" >/dev/null
  cp -a "$root/test/fixtures/.colors/dotfiles-${profile}-fixture/dotfiles" "$tmp/$profile"
done
rm -rf "$root/test/fixtures/.colors"

if [[ ${1:-} == --accept ]]; then
  rm -rf "$expected"
  mkdir -p "$(dirname "$expected")"
  cp -a "$tmp" "$expected"
  echo "golden: accepted"
else
  diff -ruN "$expected" "$tmp"
  echo "golden: matches"
fi
