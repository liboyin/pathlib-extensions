from pathlib import Path

from pathlib_extensions.overwrite import OverwriteMode, overwrite_existing_path


def test_overwrite_mode():
    assert OverwriteMode.values() == ('always', 'never', 'prompt')


def test_overwrite_existing_path_never():
    assert not overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.NEVER)


def test_overwrite_existing_path_prompt_yes(monkeypatch):
    def mock_input(prompt):
        return 'y'
    monkeypatch.setattr('builtins.input', mock_input)
    assert overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.PROMPT)


def test_overwrite_existing_path_prompt_no(monkeypatch):
    def mock_input(prompt):
        return 'n'
    monkeypatch.setattr('builtins.input', mock_input)
    assert not overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.PROMPT)


def test_overwrite_existing_path_always():
    assert overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.ALWAYS)
