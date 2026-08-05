# dotfiles

Ubuntu and macOS home configuration as a green Package Skill.

The package preserves the non-secret managed files from `dotfiles-v3`, renders
a selected profile reproducibly under `.colors/`, and installs only those files
into an explicitly configured local target. Credential-bearing AWS and
DigitalOcean CLI files are excluded.

```sh
./green build
./green diff
./green create --dry-run
COLORS_PAR_DOTFILES_PREVENT_OVERWRITE=false ./green create
```

`diff` renders first and prints color unified differences against the target.
Ordinary drift and missing target files are informational and exit successfully.
Target-only line contents are redacted so local credentials cannot leak.
`delete` is intentionally unsupported.

## Install into a project

```sh
npx skills add getcolors/dotfiles
cp .agents/skills/package-dotfiles-green/green green
chmod +x green
```

The root launcher is an installed copy. Re-copy it after every skill update.
Desired state is documented in
`skills/package-dotfiles-green/references/configuration.md`.

## Development

```sh
bb test
bb golden
./scripts/launcher.sh
```
