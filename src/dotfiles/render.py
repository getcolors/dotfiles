"""Render one packaged dotfiles profile in memory.

Shared files under ``common/`` are templates. The template language is
deliberately restricted to profile conditionals::

    {% if profile = "ubuntu" %} ... {% else %} ... {% endif %}

Anything else that looks like template syntax (``{{ }}``, ``{# #}`` or another
``{% %}`` tag) fails closed. Profile-only files are copied verbatim. This
module has no third-party dependencies so other packages (Walter) can import it.
"""
from __future__ import annotations

from pathlib import Path
import re

PROFILES = ('macos', 'ubuntu')
RESOURCES = Path(__file__).resolve().parents[1] / 'resources/io/github/getcolors/dotfiles'

_TOKEN = re.compile(r'(\{%.*?%\}|\{\{.*?\}\}|\{#.*?#\})', re.DOTALL)
_CONDITION = re.compile(r'if\s+profile\s*=\s*[\'"](ubuntu|macos)[\'"]')


class TemplateError(ValueError):
    """A packaged template or resource tree is invalid."""


def render_template(text: str, profile: str) -> str:
    """Render the restricted profile-conditional syntax for ``profile``."""
    if profile not in PROFILES:
        raise TemplateError(f'unsupported dotfiles profile: {profile!r}')
    output, stack = [], []
    active = True
    for part in _TOKEN.split(text):
        if _TOKEN.fullmatch(part):
            tag = part[2:-2].strip()
            condition = _CONDITION.fullmatch(tag) if part.startswith('{%') else None
            if condition:
                selected = condition[1] == profile
                stack.append((active, selected, False))
                active = active and selected
            elif part.startswith('{%') and tag == 'else' and stack and not stack[-1][2]:
                parent, selected, _ = stack[-1]
                stack[-1] = (parent, selected, True)
                active = parent and not selected
            elif part.startswith('{%') and tag == 'endif' and stack:
                active = stack.pop()[0]
            else:
                raise TemplateError(f'unsupported dotfiles template syntax: {part[:40]!r}')
        elif active:
            output.append(part)
    if stack:
        raise TemplateError('unterminated dotfiles template conditional')
    rendered = ''.join(output)
    if any(token in rendered for token in ('{%', '{{', '{#')):
        raise TemplateError('unterminated dotfiles template tag')
    return rendered


def _files(directory: Path) -> dict[str, Path]:
    if directory.is_symlink():
        raise TemplateError(f'packaged dotfiles directory is a symlink: {directory.name}')
    if not directory.is_dir():
        return {}
    found = {}
    for source in directory.rglob('*'):
        if source.is_symlink():
            raise TemplateError('packaged dotfile is a symlink: '
                                + source.relative_to(directory).as_posix())
        if source.is_file():
            found[source.relative_to(directory).as_posix()] = source
    return found


def render_profile(profile: str) -> dict[str, bytes]:
    """Return ``{relative POSIX path: rendered bytes}`` sorted by path.

    Common files are rendered as UTF-8 templates; profile files are copied
    verbatim. A path present in both common and the profile is an error.
    """
    if profile not in PROFILES:
        raise TemplateError(f'unsupported dotfiles profile: {profile!r}')
    common = _files(RESOURCES / 'common')
    if not common:
        raise TemplateError('packaged dotfiles have no common files')
    specific = _files(RESOURCES / 'profiles' / profile)
    duplicates = sorted(common.keys() & specific.keys())
    if duplicates:
        raise TemplateError('duplicate common/profile dotfiles: ' + ', '.join(duplicates))
    rendered = {}
    for path, source in common.items():
        try:
            text = source.read_bytes().decode('utf-8')
            rendered[path] = render_template(text, profile).encode('utf-8')
        except (UnicodeDecodeError, TemplateError) as exc:
            raise TemplateError(f'{path}: {exc}') from None
    for path, source in specific.items():
        rendered[path] = source.read_bytes()
    return dict(sorted(rendered.items()))
