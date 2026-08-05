# colors.yml for dotfiles

```yaml
profile: dotfiles-colors
workdir: .colors

dotfiles-profile: ubuntu # ubuntu or macos
dotfiles-target: "~"
dotfiles-prevent-overwrite: true
```

`profile` names the generated tree at
`.colors/<profile>/dotfiles/`. `dotfiles-profile` selects the packaged OS
profile. A real create checks that Ubuntu is applied on Linux and macOS on
macOS. `dotfiles-target` accepts `~`, a path below `~/`, or an absolute path;
the filesystem root is always refused.

A build replaces only the generated profile tree. A create copies every managed
file into the target and verifies the result byte-for-byte. It never removes
unrelated files. Credential-bearing `.aws/credentials` and DigitalOcean CLI
configuration from the source project are deliberately excluded.

The overwrite guard stays committed as `true`. After inspection and dry-run,
lift it for one authorized invocation:

```sh
COLORS_PAR_DOTFILES_PREVENT_OVERWRITE=false ./green create
```

Never set `COLORS_PAR_PROFILE`. Delete is unsupported.
