# colors.yml for dotfiles

```yaml
dotfiles-profile: ubuntu # ubuntu or macos
dotfiles-target: "~"     # optional; default "~"
```

These are the only keys. Any other key is an error, and every configuration
error is reported at once. Keys from the retired Green package (`profile`,
`workdir`, `dotfiles-prevent-overwrite`) must be removed: rendering happens in
memory, and `apply` backs up changed files instead of requiring an overwrite
override. No `COLORS_PAR_*` variables are read.

`dotfiles-profile` selects the packaged profile. A real `apply` refuses
`ubuntu` unless running on Linux and `macos` unless running on macOS; `plan`
and `apply --dry-run` work anywhere.

`dotfiles-target` accepts `~`, a path beginning `~/`, or an absolute path, and
must be an existing directory. The filesystem root is always refused.

## Behaviour

- `plan` renders the profile and prints a target-to-rendered unified diff for
  each missing or changed file, coloured only on a terminal. It never writes.
- `apply` writes each missing or changed file atomically (temporary file and
  rename, mode 0644), verifies it byte-for-byte, and leaves unchanged and
  unmanaged files alone. It never deletes anything.
- Before replacing a changed file, `apply` copies it to
  `<target>/.local/state/dotfiles/backups/<UTC timestamp>/<relative path>`.
- A symlink on any managed destination path below the target, or a managed path
  that is not a regular file, stops the run before any write.
