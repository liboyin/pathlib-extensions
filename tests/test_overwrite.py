from pathlib import Path

import pytest

from pathlib_extensions.overwrite import OverwriteMode, overwrite_existing_path


def test_overwrite_mode():
    assert OverwriteMode.values() == ('always', 'never', 'prompt')


def test_overwrite_existing_path_file_not_found(mocker):
    mocker.patch.object(Path, 'exists', return_value=False)
    with pytest.raises(FileNotFoundError):
        overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.ALWAYS)


def test_overwrite_existing_path_always(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    assert overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.ALWAYS)


def test_overwrite_existing_path_never(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    assert not overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.NEVER)


@pytest.mark.parametrize('user_input', ['y', 'Y'])
def test_overwrite_existing_path_prompt_positive(mocker, user_input):
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    mocker.patch.object(Path, 'exists', return_value=True)
    assert overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.PROMPT)
    mock_input.assert_called_once()


@pytest.mark.parametrize('user_input', ['n', 'N', ''])
def test_overwrite_existing_path_prompt_negative(mocker, user_input):
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    mocker.patch.object(Path, 'exists', return_value=True)
    assert not overwrite_existing_path(Path("/dummy/file.path"), OverwriteMode.PROMPT)
    mock_input.assert_called_once()
