import pytest

from dotfiles.config import expand, load, validate
from dotfiles.errors import DotfilesError


def test_minimal_configuration_defaults_target_to_home():
    assert validate({'dotfiles-profile': 'macos'}) == {'dotfiles-profile': 'macos', 'dotfiles-target': '~'}


def test_all_errors_are_reported_at_once():
    with pytest.raises(DotfilesError) as error:
        validate({'profile': 'x', 'workdir': '.colors', 'dotfiles-prevent-overwrite': True,
                  'surprise': 1, 'dotfiles-profile': 'windows', 'dotfiles-target': 'relative'})
    message = str(error.value)
    assert error.value.code == 'invalid_config'
    for text in ('profile is no longer supported', 'workdir is no longer supported',
                 'dotfiles-prevent-overwrite is no longer supported', 'backs up',
                 'Unknown configuration key: surprise', 'dotfiles-profile must be one of',
                 'dotfiles-target must be ~'):
        assert text in message


def test_profile_is_required():
    with pytest.raises(DotfilesError, match='dotfiles-profile is required'):
        validate({})


@pytest.mark.parametrize('target', ['/', '/..', '//', '~user', '', 3])
def test_invalid_targets(target):
    with pytest.raises(DotfilesError):
        validate({'dotfiles-profile': 'ubuntu', 'dotfiles-target': target})


def test_home_expansion(isolated_home):
    assert expand('~') == str(isolated_home)
    assert expand('~/x/y') == str(isolated_home / 'x/y')
    assert expand('/abs') == '/abs'


def test_non_mapping_and_invalid_yaml(tmp_path):
    (tmp_path / 'list.yml').write_text('- a\n')
    with pytest.raises(DotfilesError, match='mapping'):
        load(tmp_path / 'list.yml')
    (tmp_path / 'bad.yml').write_text('a: [\n')
    with pytest.raises(DotfilesError, match='not valid YAML'):
        load(tmp_path / 'bad.yml')
    with pytest.raises(DotfilesError, match='not found'):
        load(tmp_path / 'missing.yml')


def test_profile_environment_overrides_colors_yml(tmp_path):
    path = tmp_path / 'colors.yml'
    path.write_text('dotfiles-profile: ubuntu\n')
    assert load(path, {})['dotfiles-profile'] == 'ubuntu'
    assert load(path, {'DOTFILES_PROFILE': ''})['dotfiles-profile'] == 'ubuntu'
    assert load(path, {'DOTFILES_PROFILE': 'macos'})['dotfiles-profile'] == 'macos'


def test_profile_environment_supplies_a_missing_profile(tmp_path):
    path = tmp_path / 'colors.yml'
    path.write_text('dotfiles-target: "~"\n')
    assert load(path, {'DOTFILES_PROFILE': 'macos'})['dotfiles-profile'] == 'macos'


def test_invalid_profile_environment_is_rejected(tmp_path):
    path = tmp_path / 'colors.yml'
    path.write_text('dotfiles-profile: ubuntu\n')
    with pytest.raises(DotfilesError, match='dotfiles-profile must be one of'):
        load(path, {'DOTFILES_PROFILE': 'windows'})
