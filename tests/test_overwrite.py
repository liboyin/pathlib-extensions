from pathlib import Path

import pytest

from pathlib_extensions.overwrite import OverwriteMode, overwrite_existing_path, user_confirms_overwrite


def test_overwrite_mode():
    assert OverwriteMode.values() == ('always', 'never', 'prompt', 'rename')


@pytest.mark.parametrize('user_input', ['y', 'Y'])
def test_user_confirms_overwrite_positive(mocker, user_input):
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    assert user_confirms_overwrite(Path("/dummy/file.path"))
    mock_input.assert_called_once()


@pytest.mark.parametrize('user_input', ['n', 'N', ''])
def test_user_confirms_overwrite_negative(mocker, user_input):
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    assert not user_confirms_overwrite(Path("/dummy/file.path"))
    mock_input.assert_called_once()


def test_overwrite_existing_path_path_does_not_exist(mocker):
    mocker.patch.object(Path, 'exists', return_value=False)
    with pytest.raises(FileNotFoundError):
        overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.ALWAYS)


def test_overwrite_existing_path_always(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    assert overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.ALWAYS)


def test_overwrite_existing_path_never(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    assert not overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.NEVER)


def test_overwrite_existing_path_prompt_positive(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    mocker.patch('pathlib_extensions.overwrite.user_confirms_overwrite', return_value=True)
    assert overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.PROMPT)


def test_overwrite_existing_path_prompt_negative(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    mocker.patch('pathlib_extensions.overwrite.user_confirms_overwrite', return_value=False)
    assert not overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.PROMPT)


def test_overwrite_existing_path_rename(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    assert not overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.RENAME)
