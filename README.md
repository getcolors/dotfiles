# dotfiles

Ubuntu and macOS home configuration as a green Package Skill.

The package preserves the non-secret managed files from `dotfiles-v3`, renders
a selected profile reproducibly under `.colors/`, and installs only those files
into an explicitly configured local target. Credential-bearing AWS and
DigitalOcean CLI files are excluded.

Shared files live under `src/resources/io/github/getcolors/dotfiles/common/`.
Files used by only one platform live under `profiles/<profile>/`. Common files
are Selmer templates with the final output filename and can use
`{% if profile = "macos" %}` conditionals. The renderer discovers and sorts
resources at runtime; defining the same path in common and a profile is an
error.

```sh
./green build
./green diff
./green create --dry-run
COLORS_PAR_DOTFILES_PREVENT_OVERWRITE=false ./green create
```

`diff` renders first and prints color unified differences against the target.
Ordinary drift and missing target files are informational and exit successfully.
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
