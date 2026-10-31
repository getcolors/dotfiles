---
name: dotfiles
description: Plans and applies the getcolors Ubuntu or macOS dotfiles profile into a home directory with the portable Python dotfiles CLI. Use when initializing a dotfiles deployment, editing its colors.yml, reviewing drift with plan, or intentionally installing managed files with apply.
license: MIT
---

# Dotfiles

Use the bundled `dotfiles` launcher, which runs an immutable package commit
through `uv run --script`. Copy it beside the deployment's `colors.yml` and make
it executable, or run it by absolute path. It reads `colors.yml` only from the
current working directory; `-f PATH` selects another file. Read
[references/configuration.md](references/configuration.md) before editing
desired state.

## Safety

- `plan` and `apply --dry-run` never write. Use them first.
- A real `apply` against a live home directory requires explicit user
  authorization. It does not prompt.
- `apply` writes only missing or changed managed files and never deletes.
  Each changed file is first backed up to
  `<target>/.local/state/dotfiles/backups/<UTC timestamp>/`.
- Symlinks at or below the target on a managed path are refused.
- The package needs no credentials; credential-bearing files are not packaged.

## Commands

```sh
./dotfiles plan
./dotfiles apply --dry-run
./dotfiles apply
./dotfiles plan --json
```

`plan` prints a unified diff from the target to the rendered profile and exits
0 when files differ; configuration, rendering and I/O failures exit non-zero
(usage errors exit 2). `--json` emits one versioned result document on stdout.

## Initialize

1. Copy `dotfiles` beside this file to the project root and make it executable.
2. Create `colors.yml` from the configuration reference.
3. Run `./dotfiles plan` and review the diff.
4. Run `./dotfiles apply --dry-run`, then a real `apply` only when authorized.
