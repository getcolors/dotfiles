---
name: package-dotfiles-green
description: Renders and installs the getcolors Ubuntu or macOS dotfiles profile with Green. Use when initializing a dotfiles deployment, editing colors.yml, building or dry-running a profile, or intentionally converging managed files into a local home directory.
license: MIT
---

# Local dotfiles

Use this skill to render or install one packaged dotfiles profile. Read
[references/configuration.md](references/configuration.md) before changing
state or performing a real create.

## Safety

- `colors.yml` contains non-secret desired state only.
- Never export `COLORS_PAR_PROFILE`.
- Never edit or commit `.colors/`.
- Build and `create --dry-run` are safe defaults.
- Keep `dotfiles-prevent-overwrite: true`. Lift it for one authorized create
  with `COLORS_PAR_DOTFILES_PREVENT_OVERWRITE=false`.
- `delete` is unsupported: the package never removes files from a home directory.
- Credential-bearing source files are intentionally not packaged.

## Commands

```sh
./green build
./green create --dry-run
COLORS_PAR_DOTFILES_PREVENT_OVERWRITE=false ./green create
```

## Initialize

1. Copy `green` beside this file to the project root and make it executable.
2. Create `colors.yml` from the configuration reference.
3. Ignore `.colors/` and `.envrc.private`.
4. Build and inspect the generated profile.
5. Dry-run before an explicitly authorized create.
