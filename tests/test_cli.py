import json
import os
from pathlib import Path

import pytest

from dotfiles import cli
from dotfiles.render import render_profile


def configure(directory, profile='ubuntu', target='~'):
    path = Path(directory) / 'colors.yml'
    path.write_text(f'dotfiles-profile: {profile}\ndotfiles-target: "{target}"\n')
    return path


def run(capsys, *argv, platform='linux'):
    code = cli.main(list(argv), platform=platform)
    out, err = capsys.readouterr()
    return code, out, err


def files_under(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_no_arguments_prints_help(capsys):
    code, out, err = run(capsys)
    assert code == 0 and 'usage: dotfiles' in out and 'plan' in out and 'apply' in out and err == ''


@pytest.mark.parametrize('argv', [['create'], ['delete'], ['plan', '--yes'], ['plan', '--dry-run'],
                                  ['plan', '--quiet', '--verbose']])
def test_usage_errors(capsys, argv):
    code, out, err = run(capsys, *argv, '--json')
    assert code == 2
    assert json.loads(out)['error']['code'] == 'invalid_usage'


def test_colors_yml_is_only_read_from_the_current_directory(capsys, tmp_path, monkeypatch):
    configure(tmp_path)
    nested = tmp_path / 'nested'
    nested.mkdir()
    monkeypatch.chdir(nested)
    code, out, err = run(capsys, 'plan')
    assert code == 1 and 'No colors.yml found in the current directory' in err
    code, out, err = run(capsys, 'plan', '-f', '../colors.yml', '--quiet')
    assert code == 0


def test_plan_reports_missing_and_changed_files_and_never_writes(capsys, tmp_path, isolated_home):
    config = configure(tmp_path)
    (isolated_home / '.gitconfig').write_text('changed\n')
    before = files_under(isolated_home)
    code, out, err = run(capsys, 'plan', '-f', str(config))
    assert code == 0
    assert files_under(isolated_home) == before
    assert f'--- {isolated_home}/.gitconfig' in out
    assert '-changed' in out and '@@' in out
    assert '--- /dev/null' in out and '.doom.d/packages.el (rendered)' in out
    assert '\033[' not in out  # not a TTY
    assert 'Plan for ubuntu profile' in out and '16 to create, 1 to update, 0 unchanged' in out


def test_plan_json_is_one_versioned_document(capsys, tmp_path):
    config = configure(tmp_path)
    code, out, err = run(capsys, 'plan', '-f', str(config), '--json')
    document = json.loads(out)
    assert code == 0 and document['schema_version'] == 1 and document['ok'] is True
    assert document['command'] == 'plan'
    files = document['result']['files']
    assert len(files) == 17 and all(f['action'] == 'create' and '+++ ' in f['diff'] for f in files)


def test_apply_installs_then_is_idempotent(capsys, tmp_path, isolated_home):
    config = configure(tmp_path)
    code, out, err = run(capsys, 'apply', '-f', str(config))
    assert code == 0 and '17 created' in out
    assert files_under(isolated_home) == render_profile('ubuntu')
    assert all(os.stat(isolated_home / p).st_mode & 0o777 == 0o644 for p in render_profile('ubuntu'))
    code, out, err = run(capsys, 'apply', '-f', str(config))
    assert code == 0 and 'No changes.' in out
    assert not (isolated_home / '.local').exists()
    code, out, err = run(capsys, 'plan', '-f', str(config))
    assert code == 0 and '---' not in out and '17 unchanged' in out


def test_apply_backs_up_changed_files_and_keeps_unmanaged_files(capsys, tmp_path, isolated_home):
    config = configure(tmp_path)
    (isolated_home / '.gitconfig').write_text('mine\n')
    (isolated_home / 'unmanaged').write_text('keep\n')
    code, out, err = run(capsys, 'apply', '-f', str(config), '--json')
    result = json.loads(out)['result']
    backup = Path(result['backup'])
    assert backup.parent == isolated_home / '.local/state/dotfiles/backups'
    assert backup.name.endswith('Z')
    assert (backup / '.gitconfig').read_text() == 'mine\n'
    assert list(p.name for p in backup.rglob('*') if p.is_file()) == ['.gitconfig']
    assert (isolated_home / '.gitconfig').read_bytes() == render_profile('ubuntu')['.gitconfig']
    assert (isolated_home / 'unmanaged').read_text() == 'keep\n'
    (isolated_home / '.gitconfig').write_text('again\n')
    second = json.loads(run(capsys, 'apply', '-f', str(config), '--json')[1])['result']['backup']
    assert second != result['backup'] and (Path(second) / '.gitconfig').read_text() == 'again\n'


def test_apply_dry_run_writes_nothing(capsys, tmp_path, isolated_home):
    config = configure(tmp_path)
    (isolated_home / '.gitconfig').write_text('mine\n')
    code, out, err = run(capsys, 'apply', '--dry-run', '-f', str(config), platform='darwin')
    assert code == 0 and 'Dry run' in out and 'would update: .gitconfig' in out
    assert files_under(isolated_home) == {'.gitconfig': b'mine\n'}


@pytest.mark.parametrize('profile,platform', [('ubuntu', 'darwin'), ('macos', 'linux')])
def test_apply_refuses_the_wrong_operating_system(capsys, tmp_path, isolated_home, profile, platform):
    config = configure(tmp_path, profile)
    code, out, err = run(capsys, 'apply', '-f', str(config), platform=platform)
    assert code == 1 and 'can only be applied on' in err
    assert files_under(isolated_home) == {}


def test_macos_profile_applies_on_darwin(capsys, tmp_path, isolated_home):
    config = configure(tmp_path, 'macos')
    assert run(capsys, 'apply', '-f', str(config), platform='darwin')[0] == 0
    assert files_under(isolated_home) == render_profile('macos')


def test_absolute_target(capsys, tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    config = configure(tmp_path, target=str(target))
    assert run(capsys, 'apply', '-f', str(config))[0] == 0
    assert files_under(target) == render_profile('ubuntu')


def test_root_and_missing_targets_are_refused(capsys, tmp_path):
    code, out, err = run(capsys, 'plan', '-f', str(configure(tmp_path, target='/')))
    assert code == 1 and 'filesystem root' in err
    code, out, err = run(capsys, 'plan', '-f', str(configure(tmp_path, target=str(tmp_path / 'absent'))))
    assert code == 1 and 'not an existing directory' in err


@pytest.mark.parametrize('link', ['.gitconfig', '.config'])
def test_symlinked_destinations_are_refused(capsys, tmp_path, isolated_home, link):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'file').write_text('x\n')
    (isolated_home / link).symlink_to(outside / 'file' if link == '.gitconfig' else outside)
    config = configure(tmp_path)
    for command in ('plan', 'apply'):
        code, out, err = run(capsys, command, '-f', str(config))
        assert code == 1 and 'symlinked destination' in err
    assert files_under(outside) == {'file': b'x\n'}
    assert not (isolated_home / '.doom.d').exists()


def test_symlinked_backup_directory_is_refused(capsys, tmp_path, isolated_home):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (isolated_home / '.local').symlink_to(outside)
    (isolated_home / '.gitconfig').write_text('mine\n')
    code, out, err = run(capsys, 'apply', '-f', str(configure(tmp_path)))
    assert code == 1 and 'symlinked destination' in err
    assert list(outside.iterdir()) == []
    assert (isolated_home / '.gitconfig').read_text() == 'mine\n'


def test_non_regular_destination_is_refused(capsys, tmp_path, isolated_home):
    (isolated_home / '.gitconfig').mkdir()
    code, out, err = run(capsys, 'plan', '-f', str(configure(tmp_path)))
    assert code == 1 and 'not a regular file' in err


def test_invalid_configuration_fails_with_all_errors(capsys, tmp_path):
    path = tmp_path / 'colors.yml'
    path.write_text('profile: old\nworkdir: .colors\ndotfiles-profile: ubuntu\n')
    code, out, err = run(capsys, 'plan', '-f', str(path), '--json')
    error = json.loads(out)['error']
    assert code == 1 and error['code'] == 'invalid_config' and error['stage'] == 'validate'
    assert 'profile is no longer supported' in error['message'] and 'workdir' in error['message']


def test_verbose_reports_steps(capsys, tmp_path):
    code, out, err = run(capsys, 'plan', '-f', str(configure(tmp_path)), '--verbose')
    assert code == 0
    for step in ('validate', 'render', 'plan'):
        assert f'{step}: completed' in err


def test_colour_only_on_a_tty():
    from dotfiles.output import colour_diff
    coloured = colour_diff('--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y\n z\n')
    assert '\033[31m-x\033[0m\n' in coloured and '\033[32m+y\033[0m\n' in coloured and ' z\n' in coloured
