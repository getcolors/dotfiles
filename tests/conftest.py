from pathlib import Path

import pytest

GOLDEN = Path(__file__).resolve().parent / 'fixtures/golden'


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never let a test resolve the real home directory."""
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    return home
