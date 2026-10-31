"""Compare rendered files with a target directory and install changes safely.

Only managed files are ever written; nothing is deleted. A changed file is
backed up before it is replaced. Symlinks at or below the target are refused.
"""
from __future__ import annotations

from datetime import datetime, timezone
import difflib
import os
from pathlib import Path
import shutil
import stat
import tempfile

from .errors import DotfilesError

BACKUPS = '.local/state/dotfiles/backups'
MODE = 0o644
DIRECTORY_MODE = 0o700


def _refuse_symlinks(root: Path, relative: str) -> Path:
    """Return ``root / relative`` after refusing any symlink below ``root``."""
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise DotfilesError(f'Refusing symlinked destination path: {path}')
    return path


def target_root(target: str) -> Path:
    root = Path(target)
    if not root.is_absolute():
        raise DotfilesError('dotfiles-target must be absolute after expansion.')
    if not root.is_dir():
        raise DotfilesError(f'dotfiles-target is not an existing directory: {root}')
    if os.path.realpath(root) == os.path.realpath('/'):
        raise DotfilesError('dotfiles-target must not be the filesystem root.')
    return root


def compare(root: Path, files: dict[str, bytes]) -> list[dict]:
    """Return ``[{'path', 'action'}]`` with action create, update or unchanged."""
    changes = []
    for relative, content in files.items():
        path = _refuse_symlinks(root, relative)
        if not path.exists():
            action = 'create'
        else:
            if not stat.S_ISREG(path.stat().st_mode):
                raise DotfilesError(f'Destination is not a regular file: {path}')
            action = 'unchanged' if path.read_bytes() == content else 'update'
        changes.append({'path': relative, 'action': action})
    return changes


def unified_diff(root: Path, relative: str, content: bytes) -> str:
    """Target-to-rendered unified diff text for one managed file."""
    path = root / relative
    before = path.read_bytes() if path.exists() else b''
    try:
        old, new = before.decode('utf-8'), content.decode('utf-8')
    except UnicodeDecodeError:
        return f'Binary file {path} differs\n'
    fromfile = str(path) if path.exists() else '/dev/null'
    lines = difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                 fromfile=fromfile, tofile=f'{path} (rendered)')
    out = []
    lines = list(lines) or [f'--- {fromfile}\n', f'+++ {path} (rendered)\n']  # new empty file
    for line in lines:
        out.append(line)
        if not line.endswith('\n'):
            out.append('\n\\ No newline at end of file\n')
    return ''.join(out)


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=DIRECTORY_MODE)
    fd, temporary = tempfile.mkstemp(prefix='.dotfiles-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), MODE)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        if os.path.lexists(temporary):
            os.unlink(temporary)
        raise
    if path.is_symlink() or path.read_bytes() != content:
        raise DotfilesError(f'Installed file verification failed: {path}')


def _backup_dir(root: Path, now: datetime) -> Path:
    base = _refuse_symlinks(root, BACKUPS)
    stamp = now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    for suffix in [''] + [f'-{n}' for n in range(1, 100)]:
        candidate = base / (stamp + suffix)
        if not candidate.exists():
            return candidate
    raise DotfilesError('Could not allocate a backup directory.')


def apply(root: Path, files: dict[str, bytes], changes: list[dict], now: datetime | None = None) -> str | None:
    """Back up updated files, then write every create/update. Return the backup dir."""
    pending = [c for c in changes if c['action'] != 'unchanged']
    updates = [c['path'] for c in pending if c['action'] == 'update']
    backup = None
    if updates:
        backup = _backup_dir(root, now or datetime.now(timezone.utc))
        for relative in updates:
            source = _refuse_symlinks(root, relative)
            destination = _refuse_symlinks(root, Path(backup.relative_to(root), relative).as_posix())
            destination.parent.mkdir(parents=True, exist_ok=True, mode=DIRECTORY_MODE)
            shutil.copy2(source, destination)
            if destination.read_bytes() != source.read_bytes():
                raise DotfilesError(f'Backup verification failed: {destination}')
    for change in pending:
        relative = change['path']
        _write(_refuse_symlinks(root, relative), files[relative])
    return str(backup) if backup else None
