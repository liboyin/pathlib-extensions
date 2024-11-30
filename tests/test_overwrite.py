from pathlib import Path

import pytest

from pathlib_extensions.overwrite import OverwriteMode, get_safe_output_path, get_output_path_by_overwrite_mode, overwrite_existing_path, user_confirms_overwrite


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


def test_get_safe_output_path_nonexistent(mocker):
    mocker.patch.object(Path, 'exists', return_value=False)
    test_path = Path('test_file.txt')
    result = get_safe_output_path(test_path)
    assert result is test_path


def test_get_safe_output_path_one_increment(mocker):
    mock_exists = mocker.patch.object(Path, 'exists')
    mock_exists.side_effect = [True, False]
    test_path = Path('test_file.txt')
    result = get_safe_output_path(test_path)
    assert result == Path('test_file.1.txt')


def test_get_safe_output_path_multiple_increments(mocker):
    mock_exists = mocker.patch.object(Path, 'exists')
    mock_exists.side_effect = [True, True, True, False]
    test_path = Path('test_file.txt')
    result = get_safe_output_path(test_path)
    assert result == Path('test_file.3.txt')


def test_get_safe_output_path_directory(mocker):
    mock_exists = mocker.patch.object(Path, 'exists')
    mock_exists.side_effect = [True, False]
    test_path = Path('test_dir')
    result = get_safe_output_path(test_path)
    assert result == Path('test_dir.1')


def test_get_output_path_by_overwrite_mode_path_does_not_exist(mocker):
    mocker.patch.object(Path, 'exists', return_value=False)
    with pytest.raises(FileNotFoundError):
        get_output_path_by_overwrite_mode(Path("/dummy/file.path"), OverwriteMode.NEVER)


def test_get_output_path_by_overwrite_mode_always(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    test_path = Path("/dummy/file.path")
    result = get_output_path_by_overwrite_mode(test_path, OverwriteMode.ALWAYS)
    assert result is test_path


def test_get_output_path_by_overwrite_mode_never(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    test_path = Path("/dummy/file.path")
    result = get_output_path_by_overwrite_mode(test_path, OverwriteMode.NEVER)
    assert result is None


def test_get_output_path_by_overwrite_mode_prompt_positive(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    test_path = Path("/dummy/file.path")
    mocker.patch('pathlib_extensions.overwrite.user_confirms_overwrite', return_value=True)
    result = get_output_path_by_overwrite_mode(test_path, OverwriteMode.PROMPT)
    assert result is test_path


def test_get_output_path_by_overwrite_mode_prompt_negative(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    test_path = Path("/dummy/file.path")
    mocker.patch('pathlib_extensions.overwrite.user_confirms_overwrite', return_value=False)
    result = get_output_path_by_overwrite_mode(test_path, OverwriteMode.PROMPT)
    assert result is None


def test_get_output_path_by_overwrite_mode_rename(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    test_path = Path("/dummy/file.path")
    safe_path = Path('/dummy/file.1.path')
    mocker.patch('pathlib_extensions.overwrite.get_safe_output_path', return_value=safe_path)
    result = get_output_path_by_overwrite_mode(test_path, OverwriteMode.RENAME)
    assert result is safe_path
