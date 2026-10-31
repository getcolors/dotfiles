"""colors.yml loading and validation; every error is reported at once."""
from __future__ import annotations

import os
from pathlib import Path

from blue.cli import load_yaml
import yaml

from .errors import DotfilesError
from .render import PROFILES

DEFAULTS = {'dotfiles-target': '~'}
KEYS = ('dotfiles-profile', 'dotfiles-target')
RETIRED = {
    'profile': 'remove it; dotfiles renders in memory and has no generated work tree',
    'workdir': 'remove it; dotfiles renders in memory and writes no .colors/ output',
    'dotfiles-prevent-overwrite': 'remove it; apply backs up every changed file under '
                                  '.local/state/dotfiles/backups/ before writing',
}


def load(path: str | os.PathLike) -> dict:
    """Read and validate ``path``; return ``{'dotfiles-profile', 'dotfiles-target'}``."""
    path = Path(path)
    try:
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        raise DotfilesError(f'Configuration file not found: {path}') from None
    except (OSError, UnicodeDecodeError) as exc:
        raise DotfilesError(f'Cannot read configuration file {path}: {type(exc).__name__}') from None
    try:
        raw = load_yaml(text)
    except yaml.YAMLError:
        raise DotfilesError(f'Configuration file {path} is not valid YAML.') from None
    return validate(raw)


def validate(raw) -> dict:
    if not isinstance(raw, dict):
        raise DotfilesError('Configuration must be a YAML mapping.', code='invalid_config')
    errors = []
    for key in raw:
        if key in RETIRED:
            errors.append(f'{key} is no longer supported: {RETIRED[key]}.')
        elif key not in KEYS:
            errors.append(f'Unknown configuration key: {key}.')
    config = {**DEFAULTS, **{k: raw[k] for k in KEYS if k in raw}}
    profile = config.get('dotfiles-profile')
    if profile is None:
        errors.append('dotfiles-profile is required (one of: ' + ', '.join(PROFILES) + ').')
    elif profile not in PROFILES:
        errors.append('dotfiles-profile must be one of: ' + ', '.join(PROFILES) + '.')
    target = config['dotfiles-target']
    if not isinstance(target, str) or not target.strip():
        errors.append('dotfiles-target must be a non-empty string.')
    elif not (target == '~' or target.startswith('~/') or target.startswith('/')):
        errors.append('dotfiles-target must be ~, begin with ~/, or be an absolute path.')
    elif os.path.realpath(expand(target)) == os.path.realpath('/'):
        errors.append('dotfiles-target must not be the filesystem root.')
    if errors:
        raise DotfilesError('Invalid configuration:\n  ' + '\n  '.join(errors), code='invalid_config')
    return config


def expand(target: str) -> str:
    """Expand an exact ``~`` or ``~/`` prefix without invoking a shell."""
    if target == '~':
        return str(Path.home())
    if target.startswith('~/'):
        return str(Path.home() / target[2:])
    return target
