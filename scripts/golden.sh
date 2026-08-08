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

# No rendered artefact may carry a real secret into a committed golden. Checked
# before --accept copies anything. POSIX grep on purpose: a missing binary
# inside `if` is simply false, so the guard must not depend on one that may be
# absent.
if grep -rEq 'client-key-data|client-certificate-data|BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY|github_pat_|ghp_|gho_|ghu_|ghs_|ghr_' "$tmp"; then
  echo 'golden: a credential-shaped value was rendered' >&2; exit 1
fi

if [[ ${1:-} == --accept ]]; then
  rm -rf "$expected"
  mkdir -p "$(dirname "$expected")"
  cp -a "$tmp" "$expected"
  echo "golden: accepted"
else
  diff -ruN "$expected" "$tmp"
  echo "golden: matches"
fi
