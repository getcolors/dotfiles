# dotfiles

Ubuntu and macOS home configuration as a portable Python CLI.

The package holds the non-secret managed files from `dotfiles-v3`, renders the
selected profile in memory, and installs only those files into a configured
local target. Credential-bearing AWS and DigitalOcean CLI files are excluded.

Shared files live under `src/dotfiles/files/common/`; files for one platform
live under `src/dotfiles/files/<profile>/` and ship as package data. Shared files keep their
final filename and may use only `{% if profile = "ubuntu" %}` /
`{% if profile = "macos" %}`, `{% else %}` and `{% endif %}`; any other template
syntax is an error. Profile files are copied verbatim. A path defined in both
common and a profile is an error.

```sh
dotfiles plan              # unified diff target -> rendered; never writes
dotfiles apply --dry-run   # list what would be written
dotfiles apply             # write missing/changed files, backing up changes
```

Options: `-f FILE` (default `./colors.yml` in the current directory only),
`--json`, `--quiet`, `--verbose`. Drift is informational: `plan` exits 0.
`apply` never prompts and never deletes; changed files are backed up to
`<target>/.local/state/dotfiles/backups/<UTC timestamp>/` first.
Configuration is documented in
[`skills/dotfiles/references/configuration.md`](skills/dotfiles/references/configuration.md).

Other packages can render a profile without the CLI:

```python
from dotfiles.render import render_profile
files = render_profile("ubuntu")  # {relative POSIX path: bytes}, sorted
```

## Development

```sh
uv sync --extra test
uv run pytest
uv run dotfiles plan
```
