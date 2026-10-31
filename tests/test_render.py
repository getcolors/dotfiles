from pathlib import Path

import pytest

from dotfiles import render
from dotfiles.render import TemplateError, render_profile, render_template
from conftest import GOLDEN


def golden(profile):
    root = GOLDEN / profile
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob('*')) if p.is_file()}


@pytest.mark.parametrize('profile', ['ubuntu', 'macos'])
def test_render_matches_committed_golden_byte_for_byte(profile):
    rendered = render_profile(profile)
    expected = golden(profile)
    assert list(rendered) == sorted(expected)
    for path, content in expected.items():
        assert rendered[path] == content, path


def test_profiles_cover_expected_files_and_no_credentials():
    ubuntu, macos = render_profile('ubuntu'), render_profile('macos')
    assert len(ubuntu) == 17 and len(macos) == 23
    assert '.gitconfig' in ubuntu and '.doom.d/snippets/.keep' in ubuntu
    assert '.aerospace.toml' in macos and '.aerospace.toml' not in ubuntu
    for files in (ubuntu, macos):
        assert '.aws/credentials' not in files
        assert not any('doctl' in path for path in files)
        for content in files.values():
            assert b'{%' not in content and b'{{' not in content


def test_render_returns_sorted_bytes():
    files = render_profile('ubuntu')
    assert list(files) == sorted(files)
    assert all(isinstance(v, bytes) for v in files.values())


def test_conditionals_select_the_profile():
    text = 'a{% if profile = "macos" %}M{% else %}U{% endif %}b{% if profile = \'ubuntu\' %}!{% endif %}'
    assert render_template(text, 'macos') == 'aMb'
    assert render_template(text, 'ubuntu') == 'aUb!'


def test_nested_conditionals():
    text = '{% if profile = "macos" %}{% if profile = "ubuntu" %}x{% else %}y{% endif %}{% endif %}'
    assert render_template(text, 'macos') == 'y'
    assert render_template(text, 'ubuntu') == ''


@pytest.mark.parametrize('text', [
    '{{ profile }}', '{# comment #}', '{% for x in y %}{% endfor %}', '{% if profile = "windows" %}{% endif %}',
    '{% if profile = "macos" %}', '{% endif %}', '{% else %}',
    '{% if profile = "macos" %}{% else %}{% else %}{% endif %}', 'open {% tag',
])
def test_unsupported_syntax_fails_closed(text):
    with pytest.raises(TemplateError):
        render_template(text, 'ubuntu')


def test_unknown_profile_is_refused():
    with pytest.raises(TemplateError):
        render_profile('windows')


def tree(root, files):
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)


def test_duplicate_common_and_profile_path_is_an_error(tmp_path, monkeypatch):
    tree(tmp_path, {'common/.a': 'a', 'ubuntu/.a': 'b'})
    monkeypatch.setattr(render, 'RESOURCES', tmp_path)
    with pytest.raises(TemplateError, match='duplicate'):
        render_profile('ubuntu')


def test_profile_files_are_copied_verbatim(tmp_path, monkeypatch):
    tree(tmp_path, {'common/.a': '{% if profile = "ubuntu" %}u{% endif %}',
                    'macos/.b': '{{ untouched }}'})
    monkeypatch.setattr(render, 'RESOURCES', tmp_path)
    assert render_profile('macos') == {'.a': b'', '.b': b'{{ untouched }}'}
    assert render_profile('ubuntu') == {'.a': b'u'}


def test_render_module_has_no_third_party_imports():
    source = Path(render.__file__).read_text()
    assert 'import blue' not in source and 'from blue' not in source and 'yaml' not in source
