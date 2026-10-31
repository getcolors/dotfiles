"""Stdout results and stderr progress for the dotfiles CLI."""
from __future__ import annotations

from contextlib import contextmanager
import json
import sys

SCHEMA_VERSION = 1
_ANSI = {'reset': '\033[0m', 'bold': '\033[1m', 'cyan': '\033[36m', 'red': '\033[31m', 'green': '\033[32m'}


def colour_diff(text: str) -> str:
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith(('--- ', '+++ ')):
            colour = 'bold'
        elif line.startswith('@@'):
            colour = 'cyan'
        elif line.startswith('-'):
            colour = 'red'
        elif line.startswith('+'):
            colour = 'green'
        else:
            lines.append(line)
            continue
        body = line.rstrip('\n')
        lines.append(_ANSI[colour] + body + _ANSI['reset'] + line[len(body):])
    return ''.join(lines)


def _counts(files):
    counts = {'create': 0, 'update': 0, 'unchanged': 0}
    for item in files:
        counts[item['action']] += 1
    return counts


def text_result(command, result, verbose=False):
    counts = _counts(result['files'])
    summary = (f"{counts['create']} to create, {counts['update']} to update, "
               f"{counts['unchanged']} unchanged")
    head = f"{result['profile']} profile -> {result['target']}"
    lines = []
    if command == 'plan' or result.get('dry_run'):
        title = 'Plan' if command == 'plan' else 'Dry run'
        lines.append(f'{title} for {head}: {summary}.')
        verb = {'create': 'would create', 'update': 'would update'} if command == 'apply' else {
            'create': 'create', 'update': 'update'}
    else:
        lines.append(f"Applied {head}: {counts['create']} created, {counts['update']} updated, "
                     f"{counts['unchanged']} unchanged.")
        verb = {'create': 'created', 'update': 'updated'}
    for item in result['files']:
        if item['action'] != 'unchanged':
            lines.append(f"  {verb[item['action']]}: {item['path']}")
        elif verbose:
            lines.append(f"  unchanged: {item['path']}")
    if result.get('backup'):
        lines.append(f"Backups: {result['backup']}")
    if not counts['create'] and not counts['update']:
        lines.append('No changes.')
    return lines


class Reporter:
    def __init__(self, json_mode=False, quiet=False, verbose=False, command=None, colour=None):
        self.json_mode = json_mode
        self.quiet = quiet
        self.verbose = verbose
        self.command = command
        self.colour = sys.stdout.isatty() if colour is None else colour
        self.failed_stage = None

    def progress(self, message):
        if self.verbose and not self.quiet:
            print(message, file=sys.stderr, flush=True)

    @contextmanager
    def stage(self, name):
        self.progress(f'{name}: started')
        try:
            yield
        except BaseException:
            if self.failed_stage is None:
                self.failed_stage = name
            raise
        self.progress(f'{name}: completed')

    def diff(self, text):
        if self.json_mode:
            return
        sys.stdout.write(colour_diff(text) if self.colour else text)
        sys.stdout.flush()

    def success(self, result):
        if self.json_mode:
            print(json.dumps({'schema_version': SCHEMA_VERSION, 'command': self.command,
                              'ok': True, 'result': result}, sort_keys=True), flush=True)
        else:
            print('\n'.join(text_result(self.command, result, self.verbose)), flush=True)

    def failure(self, message, code='operation_failed', stage=None):
        if self.json_mode:
            error = {'code': code, 'message': message}
            if stage:
                error['stage'] = stage
            print(json.dumps({'schema_version': SCHEMA_VERSION, 'command': self.command,
                              'ok': False, 'error': error}, sort_keys=True), flush=True)
        else:
            print('dotfiles: ' + (f'{stage}: ' if stage else '') + message, file=sys.stderr, flush=True)
