#!/usr/bin/env python3
"""Exercise the portable launcher outside this checkout, against temporary homes only.

By default the launcher resolves its pinned commit from GitHub, so the pin must
be pushed. --local substitutes this working tree for the pinned dependency.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r'"dotfiles @ git\+https://github\.com/getcolors/dotfiles\.git@([0-9a-f]{40})"')


def main():
    options = argparse.ArgumentParser(description=__doc__)
    options.add_argument('--local', action='store_true', help='Use this working tree instead of the pinned commit')
    local = options.parse_args().local
    source = ROOT / 'skills/dotfiles/dotfiles'
    text = source.read_text()
    assert PIN.search(text), 'Launcher does not pin a full commit SHA.'
    assert 'from dotfiles.cli import main' in text and 'def ' not in text, 'Launcher must hold no logic.'
    assert os.access(source, os.X_OK), 'Launcher is not executable.'
    assert (ROOT / 'dotfiles').resolve() == source.resolve(), 'Root ./dotfiles must link to the launcher.'
    if shutil.which('uv') is None:
        raise AssertionError('Install uv before running launcher checks.')
    profile = 'macos' if sys.platform == 'darwin' else 'ubuntu'
    with tempfile.TemporaryDirectory(prefix='dotfiles-launcher-') as temporary:
        root = Path(temporary)
        home = root / 'home'
        home.mkdir()
        launcher = root / 'bin/dotfiles'
        launcher.parent.mkdir()
        if local:
            text = PIN.sub(f'"dotfiles @ {ROOT.as_uri()}"', text)
        launcher.write_text(text)
        launcher.chmod(0o700)
        environment = {key: value for key, value in os.environ.items() if key not in {
            'VIRTUAL_ENV', 'PYTHONPATH', 'PYTHONHOME', 'UV_PROJECT', 'UV_PROJECT_ENVIRONMENT'}}
        # Every apply below targets "~", so HOME must point at the temporary home;
        # keep uv's cache and managed Pythons where they were.
        for variable, command in (('UV_CACHE_DIR', ['cache', 'dir']), ('UV_PYTHON_INSTALL_DIR', ['python', 'dir'])):
            environment.setdefault(variable, subprocess.run(['uv', *command], capture_output=True, text=True,
                                                            check=True).stdout.strip())
        environment['HOME'] = str(home)

        def invoke(directory, *arguments, code=0):
            result = subprocess.run([str(launcher), *arguments], cwd=directory, env=environment,
                                    capture_output=True, text=True, timeout=600)
            assert result.returncode == code, (arguments, result.returncode, result.stdout, result.stderr)
            return result

        empty = root / 'empty'
        empty.mkdir()
        # A standalone script must ignore the caller's project.
        (empty / 'pyproject.toml').write_text('[project]\nname = "unrelated"\nversion = "0"\n'
                                              'dependencies = ["deliberately invalid !!!"]\n')
        bare = invoke(empty)
        assert 'usage: dotfiles' in bare.stdout and bare.stdout == invoke(empty, '--help').stdout
        removed = invoke(empty, 'create', '--json', code=2)
        assert json.loads(removed.stdout)['error']['code'] == 'invalid_usage'
        missing = invoke(empty, 'plan', code=1)
        assert 'No colors.yml found in the current directory' in missing.stderr

        deployment = root / 'deployment'
        nested = deployment / 'nested'
        nested.mkdir(parents=True)
        (deployment / 'colors.yml').write_text(f'dotfiles-profile: {profile}\ndotfiles-target: "~"\n')
        invoke(nested, 'plan', code=1)
        plan = invoke(nested, 'plan', '-f', '../colors.yml', '--json')
        files = json.loads(plan.stdout)['result']['files']
        assert files and all(item['action'] == 'create' for item in files)
        invoke(deployment, 'apply', '--dry-run')
        assert not list(home.iterdir()), 'Dry run wrote files.'
        invoke(deployment, 'apply')
        assert (home / '.gitconfig').is_file()
        again = json.loads(invoke(deployment, 'plan', '--json').stdout)['result']['files']
        assert all(item['action'] == 'unchanged' for item in again)
        (deployment / 'colors.yml').write_text('profile: old\ndotfiles-profile: ubuntu\n')
        invalid = invoke(deployment, 'plan', code=1)
        assert 'profile is no longer supported' in invalid.stderr
    print('launcher: checks passed' + (' (local working tree)' if local else ''))


if __name__ == '__main__':
    main()
