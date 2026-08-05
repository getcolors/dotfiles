# CLAUDE.md

## What this is

`dotfiles` is a green-only Package Skill that deterministically renders and
installs Ubuntu or macOS home configuration. It ships
`package-dotfiles-green`; root `./green` symlinks to its launcher payload.
Credential-bearing AWS and DigitalOcean files from the source configuration are
intentionally excluded.

## Commands

```sh
bb test
bb golden
./scripts/launcher.sh
./green build
./green diff
./green create --dry-run
```

Never run a real create without explicit authorization. A create writes managed
files into the configured local target. `delete` is unsupported.

## Safety and architecture

- `colors.yml` is non-secret desired state; keys are kebab-case.
- Never export `COLORS_PAR_PROFILE`.
- Never edit or commit `.colors/`.
- Keep `dotfiles-prevent-overwrite: true`; lift it only for one intentional run
  through `COLORS_PAR_DOTFILES_PREVENT_OVERWRITE=false`.
- Build replaces `.colors/<profile>/dotfiles`; create copies those managed files
  to `dotfiles-target` and verifies them byte-for-byte.
- Diff renders first, then prints target-to-rendered unified differences. Drift
  and missing targets are informational; operational failures remain errors.
  Target-only line content is redacted because local files may contain secrets.
- Keep behaviour in library namespaces, not the copied launcher.
- After pushing package code, run `bb pin`, commit, and push. Consumers must
  synchronize their installed launcher copy after every update.
