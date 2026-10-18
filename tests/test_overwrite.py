from pathlib import Path

import pytest

import pathlib_extensions.overwrite as testee


def test_overwrite_mode():
    assert testee.OverwriteMode.values() == ('always', 'never', 'prompt', 'rename')


@pytest.mark.parametrize('user_input', ['y', 'Y'])
def test_user_confirms_overwrite_positive(mocker, user_input):
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    assert testee.user_confirms_overwrite(Path("/dummy/file.path"))
    mock_input.assert_called_once()


@pytest.mark.parametrize('user_input', ['n', 'N', ''])
def test_user_confirms_overwrite_negative(mocker, user_input):
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    assert not testee.user_confirms_overwrite(Path("/dummy/file.path"))
    mock_input.assert_called_once()


def test_overwrite_existing_path_path_does_not_exist(mocker):
    mocker.patch.object(Path, 'exists', return_value=False)
    with pytest.raises(FileNotFoundError):
        testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.ALWAYS)


def test_overwrite_existing_path_always(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    assert testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.ALWAYS)


def test_overwrite_existing_path_never(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    assert not testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.NEVER)


def test_overwrite_existing_path_prompt_positive(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    mocker.patch.object(testee, 'user_confirms_overwrite', return_value=True)
    assert testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.PROMPT)


def test_overwrite_existing_path_prompt_negative(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    mocker.patch.object(testee, 'user_confirms_overwrite', return_value=False)
    assert not testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.PROMPT)


def test_overwrite_existing_path_rename(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    assert not testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.RENAME)


@pytest.mark.parametrize('mode', list(testee.OverwriteMode))
def test_resolve_overwrite_mode_absent_file_keeps_mode_without_prompt(mode, mocker, tmp_path):
    """A missing destination keeps the requested mode and never prompts."""
    prompt = mocker.patch.object(testee, 'user_confirms_overwrite')
    assert testee.resolve_overwrite_mode(tmp_path / 'missing.bin', mode) is mode
    prompt.assert_not_called()


@pytest.mark.parametrize('mode', list(testee.OverwriteMode))
def test_resolve_overwrite_mode_directory_is_left_to_the_writer(mode, mocker, tmp_path):
    """A directory is not an existing file: the mode is returned unchanged without a prompt."""
    prompt = mocker.patch.object(testee, 'user_confirms_overwrite')
    assert testee.resolve_overwrite_mode(tmp_path, mode) is mode
    prompt.assert_not_called()


@pytest.mark.parametrize('mode', [testee.OverwriteMode.NEVER, testee.OverwriteMode.RENAME])
def test_resolve_overwrite_mode_keeps_existing_file_under_preserving_modes(mode, tmp_path):
    """NEVER and RENAME decline to write over an existing file."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    assert testee.resolve_overwrite_mode(path, mode) is None


def test_resolve_overwrite_mode_always_overwrites_existing_file(tmp_path):
    """ALWAYS approves writing over an existing file."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    assert testee.resolve_overwrite_mode(path, testee.OverwriteMode.ALWAYS) is testee.OverwriteMode.ALWAYS


@pytest.mark.parametrize(('consent', 'expected'), [(True, testee.OverwriteMode.ALWAYS), (False, None)])
def test_resolve_overwrite_mode_prompt_asks_once_and_carries_the_answer(consent, expected, mocker, tmp_path):
    """PROMPT asks about an existing file once; approval becomes ALWAYS, refusal keeps it."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    prompt = mocker.patch.object(testee, 'user_confirms_overwrite', return_value=consent)
    assert testee.resolve_overwrite_mode(path, testee.OverwriteMode.PROMPT) is expected
    prompt.assert_called_once_with(path)


def test_resolve_overwrite_mode_checks_file_behind_symlink(tmp_path):
    """A symlink to an existing file counts as an existing file."""
    real = tmp_path / 'real.bin'
    real.write_bytes(b'old')
    link = tmp_path / 'link.bin'
    link.symlink_to(real.name)
    assert testee.resolve_overwrite_mode(link, testee.OverwriteMode.NEVER) is None
