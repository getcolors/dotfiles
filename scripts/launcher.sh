#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
launcher="$root/skills/package-dotfiles-green/green"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

checks=0
fail() { echo "launcher: FAIL — $*" >&2; exit 1; }
ok() { checks=$((checks + 1)); echo "  ok — $*"; }

[ -f "$launcher" ] || fail "no launcher at $launcher"
grep -q 'io.github.getcolors.dotfiles.workflow/workflow' "$launcher" ||
  fail "launcher does not dispatch to the library workflow"
ok "dispatches to the tested workflow"

for forbidden in 'defn.*-step' 'fs/copy' 'io/copy'; do
  grep -qE "$forbidden" "$launcher" &&
    fail "launcher contains package logic: /$forbidden/"
done
ok "contains no render or install step"

copy="$tmp/bare"
mkdir -p "$copy"
cp "$launcher" "$copy/green"
chmod +x "$copy/green"
pin=$(grep -oE '\(def \^:private dotfiles-sha (nil|"[0-9a-f]{40}")\)' "$launcher" || true)
[ -n "$pin" ] || fail "could not read dotfiles-sha"
ok "declares a pin site"

if echo "$pin" | grep -q nil; then
  out=$( (cd "$copy" && ./green build 2>&1) || true )
  echo "$out" | grep -q DOTFILES_LIB_ROOT ||
    fail "unstamped launcher does not name DOTFILES_LIB_ROOT: $out"
  ok "unstamped launcher explains its working-tree override"
else
  ok "launcher is pinned to a real commit"
fi

cat >"$copy/colors.yml" <<'EOF'
profile: launcher-check
workdir: .colors
dotfiles-profile: ubuntu
dotfiles-target: /tmp/launcher-check
dotfiles-prevent-overwrite: true
EOF

out=$( (cd "$copy" && DOTFILES_LIB_ROOT="$root" ./green build 2>&1) ) ||
  fail "working-tree override failed: $out"
[ -f "$copy/.colors/launcher-check/dotfiles/.gitconfig" ] ||
  fail "working-tree override rendered nothing"
ok "DOTFILES_LIB_ROOT resolves a copied launcher"

mkdir -p "$copy/deep/nested"
out=$( (cd "$copy/deep/nested" && DOTFILES_LIB_ROOT="$root" ./../../green build 2>&1) ) ||
  fail "subdirectory invocation failed: $out"
[ -f "$copy/.colors/launcher-check/dotfiles/.gitconfig" ] ||
  fail "subdirectory invocation rendered in the wrong place"
ok "finds colors.yml by walking up"

grep -q launcher-contract "$launcher" || fail "contract handshake is missing"
grep -q 'def contract' "$root/src/clj/io/github/getcolors/dotfiles/utils.clj" ||
  fail "library contract is missing"
ok "launcher and library expose a contract handshake"

out=$( (cd "$copy" && DOTFILES_LIB_ROOT="$root" ./green delete 2>&1) || true )
echo "$out" | grep -q 'unsupported' || fail "delete should be unsupported: $out"
ok "delete is explicitly unsupported"

echo "launcher: $checks checks passed"
