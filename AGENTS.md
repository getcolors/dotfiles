# AGENTS.md

## What this is

`dotfiles` is a Python package and Agent Skill that renders the getcolors
Ubuntu or macOS home configuration and installs it into a local directory. The
CLI (`dotfiles plan|apply`) runs a small Blue DAG: validate -> render ->
plan | apply. Credential-bearing AWS and DigitalOcean files are intentionally
excluded; the package reads no credentials and no `COLORS_PAR_*` variables.

## Commands

```sh
uv sync --extra test
uv run pytest
uv run dotfiles plan
uv run dotfiles apply --dry-run
```

**A real `apply` against a live home directory requires explicit user
authorization.** It writes without prompting. Tests must use temporary
directories; a read-only `plan` against `~` is fine.

## Safety and architecture

- `colors.yml` holds only `dotfiles-profile` and `dotfiles-target`; unknown
  keys are errors. Rendering is in memory; there is no `.colors/` output.
- `apply` writes only missing or changed managed files, atomically, verifies
  them, refuses symlinked destination paths, backs up changed files under
  `<target>/.local/state/dotfiles/backups/<UTC timestamp>/`, and never deletes.
- `src/dotfiles/render.py` is the dependency-free public render API
  (`render_profile(profile) -> dict[str, bytes]`). Keep Blue and YAML out of it.
- Templates support only profile `if`/`else`/`endif`; anything else fails
  closed. The golden test pins render output byte-for-byte; review any golden
  change deliberately.
- **getcolors/walter reads these files.** A change to the template syntax or the
  file layout affects Walter; coordinate it there.
- Keep behaviour in the package, not the launcher. The launcher pins an
  immutable commit: after package changes are pushed, update its SHA to the
  pushed commit in a follow-up commit. Never invent a SHA.
