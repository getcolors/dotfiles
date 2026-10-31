"""The dotfiles CLI: a small Blue DAG, validate -> render -> plan | apply."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from blue.workflow import workflow, run as run_workflow

from . import install
from .config import expand, load
from .errors import DotfilesError
from .output import Reporter
from .render import TemplateError, render_profile

COMMANDS = ('plan', 'apply')
PLATFORMS = {'ubuntu': ('linux', 'Linux'), 'macos': ('darwin', 'macOS')}


class UsageError(DotfilesError):
    def __init__(self, message='Invalid command arguments; run dotfiles --help.'):
        super().__init__(message, code='invalid_usage')


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError()


def parser():
    p = ArgumentParser(
        prog='dotfiles', allow_abbrev=False, formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Render the getcolors Ubuntu or macOS dotfiles profile and install it into a home directory.',
        epilog='''Commands:
  plan      Print a unified diff from the target to the rendered profile; never writes
  apply     Write missing or changed managed files, backing up changed files first

Examples:
  dotfiles plan
  dotfiles apply --dry-run
  dotfiles apply
  dotfiles plan -f deployments/laptop.yml --json

apply never prompts and never deletes files. Changed files are backed up to
<target>/.local/state/dotfiles/backups/<UTC timestamp>/ before being replaced.
Configuration defaults to colors.yml in the current working directory.
Run without arguments to show this help.''')
    p.add_argument('command', metavar='COMMAND', choices=COMMANDS, help='plan or apply (listed below)')
    p.add_argument('-f', '--file', help='Configuration file (default: ./colors.yml in the current working directory)')
    p.add_argument('--dry-run', action='store_true', help='With apply: report what would be written without writing')
    p.add_argument('--json', action='store_true', help='Emit one versioned JSON result on stdout')
    p.add_argument('--quiet', action='store_true', help='Suppress progress on stderr')
    p.add_argument('--verbose', action='store_true', help='Show step progress on stderr and unchanged files')
    return p


def validate_step(opts):
    config = load(opts['dotfiles/file'])
    target = expand(config['dotfiles-target'])
    if opts['dotfiles/command'] == 'apply' and not opts['dotfiles/dry-run']:
        platform, name = PLATFORMS[config['dotfiles-profile']]
        if not opts['dotfiles/platform'].startswith(platform):
            raise DotfilesError(f"The {config['dotfiles-profile']} profile can only be applied on {name}.",
                                code='invalid_config')
    root = install.target_root(target)
    return {**opts, 'dotfiles/profile': config['dotfiles-profile'], 'dotfiles/target': str(root)}


def render_step(opts):
    try:
        files = render_profile(opts['dotfiles/profile'])
    except TemplateError as exc:
        raise DotfilesError(f'Rendering failed: {exc}') from None
    return {**opts, 'dotfiles/files': files}


def _changes(opts):
    root = Path(opts['dotfiles/target'])
    files = dict(opts['dotfiles/files'])
    return root, files, install.compare(root, files)


def plan_step(opts, reporter):
    root, files, changes = _changes(opts)
    diffs = {}
    for change in changes:
        if change['action'] != 'unchanged':
            diffs[change['path']] = install.unified_diff(root, change['path'], files[change['path']])
            reporter.diff(diffs[change['path']])
    if reporter.json_mode:
        changes = [{**c, 'diff': diffs[c['path']]} if c['path'] in diffs else c for c in changes]
    return {**opts, 'dotfiles/result': {'profile': opts['dotfiles/profile'], 'target': str(root),
                                        'files': changes}}


def apply_step(opts):
    root, files, changes = _changes(opts)
    dry_run = opts['dotfiles/dry-run']
    backup = None if dry_run else install.apply(root, files, changes)
    return {**opts, 'dotfiles/result': {'profile': opts['dotfiles/profile'], 'target': str(root),
                                        'dry_run': dry_run, 'files': changes, 'backup': backup}}


def execute(args, reporter, platform=None):
    """Run the DAG; return the result dict or raise DotfilesError."""
    if args.dry_run and args.command != 'apply':
        raise UsageError('--dry-run is supported only for apply.')
    if args.file is None and not Path('colors.yml').is_file():
        raise DotfilesError('No colors.yml found in the current directory; use -f to select a configuration.')
    steps = {'validate': [validate_step, 'render'],
             'render': [render_step, args.command],
             'plan': [lambda opts: plan_step(opts, reporter)],
             'apply': [apply_step]}
    failure = None

    # Failures are caught at the step boundary so Blue never records a traceback.
    def wire(name, _run_opts):
        fn, *successors = steps[name]

        def safe(opts):
            nonlocal failure
            try:
                with reporter.stage(name):
                    return fn(opts)
            except DotfilesError as exc:
                exc.stage = exc.stage or name
                failure = exc
            except OSError as exc:
                failure = DotfilesError(f'{type(exc).__name__}: {exc.strerror or exc}'
                                        + (f' ({exc.filename})' if exc.filename else ''), stage=name)
            return {**opts, 'blue/exit': 1, 'blue/err': str(failure)}
        return [safe, *successors]

    result = asyncio.run(run_workflow(workflow(start='validate', wire_fn=wire), {
        'dotfiles/command': args.command, 'dotfiles/file': args.file or 'colors.yml',
        'dotfiles/dry-run': args.dry_run, 'dotfiles/platform': platform or sys.platform}))
    if result.get('blue/exit'):
        raise failure or DotfilesError(result.get('blue/err') or 'Workflow failed.')
    return result['dotfiles/result']


def main(argv=None, platform=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv:
        parser().print_help()
        return 0
    reporter = Reporter(json_mode='--json' in argv, quiet='--quiet' in argv)
    try:
        args = parser().parse_args(argv)
        reporter.command = args.command
        reporter.verbose = args.verbose
        if args.verbose and args.quiet:
            raise UsageError('--verbose and --quiet cannot be combined.')
        reporter.success(execute(args, reporter, platform))
    except DotfilesError as exc:
        reporter.failure(str(exc), code=exc.code, stage=exc.stage)
        return 2 if exc.code == 'invalid_usage' else 1
    except KeyboardInterrupt:
        reporter.failure('Interrupted.', code='interrupted')
        return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
