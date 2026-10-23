import importlib
import os
import sys
from pathlib import Path

import pytest

import pathlib_extensions.overwrite as testee
from pathlib_extensions.prepare import NotAFileError


def deprecated(replacement: str = 'OverwritePolicy.resolve'):
    """Expect a DeprecationWarning that names the replacement of a deprecated entry point."""
    return pytest.warns(DeprecationWarning, match=replacement)


def assert_single_deprecation(record: pytest.WarningsRecorder, replacement: str) -> None:
    """Check that exactly one warning was emitted, a DeprecationWarning naming `replacement` and attributed to the caller."""
    assert len(record) == 1
    assert record[0].category is DeprecationWarning
    assert replacement in str(record[0].message)
    assert record[0].filename == __file__


def test_overwrite_mode():
    with deprecated('OverwritePolicy'):
        assert testee.OverwriteMode.values() == ('always', 'never', 'prompt', 'rename')


def test_overwrite_mode_values_warns_once_naming_overwrite_policy():
    """OverwriteMode.values() emits one DeprecationWarning that points to OverwritePolicy."""
    with pytest.warns(DeprecationWarning) as record:
        testee.OverwriteMode.values()
    assert_single_deprecation(record, 'OverwritePolicy')


@pytest.mark.filterwarnings('error')
def test_overwrite_mode_members_and_fresh_package_import_do_not_warn(monkeypatch):
    """A fresh import of the package, whose star imports read every export, and OverwriteMode's members emit no warning."""
    for name in [name for name in sys.modules if name.partition('.')[0] == 'pathlib_extensions']:
        monkeypatch.delitem(sys.modules, name)
    fresh = importlib.import_module('pathlib_extensions')
    assert fresh.OverwriteMode is not testee.OverwriteMode
    assert fresh.OverwriteMode('never') is fresh.OverwriteMode.NEVER
    assert [mode.value for mode in fresh.OverwriteMode] == ['always', 'never', 'prompt', 'rename']


@pytest.mark.parametrize('user_input', ['y', 'Y'])
def test_user_confirms_overwrite_positive(mocker, user_input):
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    with deprecated():
        assert testee.user_confirms_overwrite(Path("/dummy/file.path"))
    mock_input.assert_called_once()


@pytest.mark.parametrize('user_input', ['n', 'N', ''])
def test_user_confirms_overwrite_negative(mocker, user_input):
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    with deprecated():
        assert not testee.user_confirms_overwrite(Path("/dummy/file.path"))
    mock_input.assert_called_once()


def test_user_confirms_overwrite_warns_once_naming_overwrite_policy(mocker):
    """user_confirms_overwrite emits one DeprecationWarning that points to OverwritePolicy.resolve."""
    mocker.patch('builtins.input', return_value='y')
    with pytest.warns(DeprecationWarning) as record:
        testee.user_confirms_overwrite(Path("/dummy/file.path"))
    assert_single_deprecation(record, 'OverwritePolicy.resolve')


def test_overwrite_existing_path_path_does_not_exist(mocker):
    mocker.patch.object(Path, 'exists', return_value=False)
    with pytest.raises(FileNotFoundError), deprecated():
        testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.ALWAYS)


def test_overwrite_existing_path_always(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    with deprecated():
        assert testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.ALWAYS)


def test_overwrite_existing_path_never(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    with deprecated():
        assert not testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.NEVER)


def test_overwrite_existing_path_prompt_positive(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    mocker.patch.object(testee, '_user_confirms_overwrite', return_value=True)
    with deprecated():
        assert testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.PROMPT)


def test_overwrite_existing_path_prompt_negative(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    mocker.patch.object(testee, '_user_confirms_overwrite', return_value=False)
    with deprecated():
        assert not testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.PROMPT)


def test_overwrite_existing_path_rename(mocker):
    mocker.patch.object(Path, 'exists', return_value=True)
    with deprecated():
        assert not testee.overwrite_existing_path(Path("/dummy/file.path"), testee.OverwriteMode.RENAME)


@pytest.mark.parametrize('user_input', ['y', 'n'])
def test_overwrite_existing_path_prompt_warns_once_naming_overwrite_policy(user_input, mocker, tmp_path):
    """A prompting overwrite_existing_path call emits one DeprecationWarning, not a second one for its prompt."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    with pytest.warns(DeprecationWarning) as record:
        assert testee.overwrite_existing_path(path, testee.OverwriteMode.PROMPT) == (user_input == 'y')
    mock_input.assert_called_once()
    assert_single_deprecation(record, 'OverwritePolicy.resolve')


@pytest.mark.parametrize('mode', list(testee.OverwriteMode))
def test_resolve_overwrite_mode_absent_file_keeps_mode_without_prompt(mode, mocker, tmp_path):
    """A missing destination keeps the requested mode and never prompts."""
    prompt = mocker.patch.object(testee, '_user_confirms_overwrite')
    with deprecated():
        assert testee.resolve_overwrite_mode(tmp_path / 'missing.bin', mode) is mode
    prompt.assert_not_called()


@pytest.mark.parametrize('mode', list(testee.OverwriteMode))
def test_resolve_overwrite_mode_directory_is_left_to_the_writer(mode, mocker, tmp_path):
    """A directory is not an existing file: the mode is returned unchanged without a prompt."""
    prompt = mocker.patch.object(testee, '_user_confirms_overwrite')
    with deprecated():
        assert testee.resolve_overwrite_mode(tmp_path, mode) is mode
    prompt.assert_not_called()


@pytest.mark.parametrize('mode', [testee.OverwriteMode.NEVER, testee.OverwriteMode.RENAME])
def test_resolve_overwrite_mode_keeps_existing_file_under_preserving_modes(mode, tmp_path):
    """NEVER and RENAME decline to write over an existing file."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    with deprecated():
        assert testee.resolve_overwrite_mode(path, mode) is None


def test_resolve_overwrite_mode_always_overwrites_existing_file(tmp_path):
    """ALWAYS approves writing over an existing file."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    with deprecated():
        assert testee.resolve_overwrite_mode(path, testee.OverwriteMode.ALWAYS) is testee.OverwriteMode.ALWAYS


@pytest.mark.parametrize(('consent', 'expected'), [(True, testee.OverwriteMode.ALWAYS), (False, None)])
def test_resolve_overwrite_mode_prompt_asks_once_and_carries_the_answer(consent, expected, mocker, tmp_path):
    """PROMPT asks about an existing file once; approval becomes ALWAYS, refusal keeps it."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    prompt = mocker.patch.object(testee, '_user_confirms_overwrite', return_value=consent)
    with deprecated():
        assert testee.resolve_overwrite_mode(path, testee.OverwriteMode.PROMPT) is expected
    prompt.assert_called_once_with(path)


def test_resolve_overwrite_mode_checks_file_behind_symlink(tmp_path):
    """A symlink to an existing file counts as an existing file."""
    real = tmp_path / 'real.bin'
    real.write_bytes(b'old')
    link = tmp_path / 'link.bin'
    link.symlink_to(real.name)
    with deprecated():
        assert testee.resolve_overwrite_mode(link, testee.OverwriteMode.NEVER) is None


@pytest.mark.parametrize('user_input', ['y', 'n'])
def test_resolve_overwrite_mode_prompt_warns_once_naming_overwrite_policy(user_input, mocker, tmp_path):
    """A prompting resolve_overwrite_mode call emits one DeprecationWarning, not more for the helpers it uses."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    mock_input = mocker.patch('builtins.input', return_value=user_input)
    with pytest.warns(DeprecationWarning) as record:
        testee.resolve_overwrite_mode(path, testee.OverwriteMode.PROMPT)
    mock_input.assert_called_once()
    assert_single_deprecation(record, 'OverwritePolicy.resolve')


def test_overwrite_policy_values_are_the_choices_in_declaration_order():
    """values() lists every policy's string value in declaration order."""
    assert testee.OverwritePolicy.values() == ('always', 'never', 'rename')


def test_overwrite_policy_is_exported_alongside_overwrite_mode():
    """OverwritePolicy is public and separate from the unchanged OverwriteMode."""
    import pathlib_extensions
    assert pathlib_extensions.OverwritePolicy is testee.OverwritePolicy
    assert testee.OverwritePolicy is not testee.OverwriteMode
    with deprecated('OverwritePolicy'):
        assert testee.OverwriteMode.values() == ('always', 'never', 'prompt', 'rename')


@pytest.mark.parametrize('policy', list(testee.OverwritePolicy))
def test_overwrite_policy_resolve_returns_absent_path_silently(policy, tmp_path, capsys):
    """Every policy writes to a path with nothing at it, without a message or any filesystem change."""
    path = tmp_path / 'hello.mp4'
    assert policy.resolve(path) == path
    assert capsys.readouterr().out == ''
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('via_symlink', [False, True], ids=['file', 'symlink'])
def test_overwrite_policy_resolve_always_overwrites_existing_file(via_symlink, tmp_path, capsys):
    """ALWAYS returns the path of a file, or a symlink to one, and says it will overwrite it."""
    real = tmp_path / 'hello.mp4'
    real.write_bytes(b'old')
    path = real
    if via_symlink:
        path = tmp_path / 'link.mp4'
        path.symlink_to(real.name)
    assert testee.OverwritePolicy.ALWAYS.resolve(path) == path
    assert capsys.readouterr().out == f'Overwriting path: {path}\n'
    assert real.read_bytes() == b'old'


@pytest.mark.parametrize('via_symlink', [False, True], ids=['file', 'symlink'])
def test_overwrite_policy_resolve_never_keeps_existing_file(via_symlink, tmp_path, capsys):
    """NEVER returns None for a file, or a symlink to one, and says it will not overwrite."""
    real = tmp_path / 'hello.mp4'
    real.write_bytes(b'old')
    path = real
    if via_symlink:
        path = tmp_path / 'link.mp4'
        path.symlink_to(real.name)
    assert testee.OverwritePolicy.NEVER.resolve(path) is None
    assert capsys.readouterr().out == f'Not overwriting path: {path}\n'
    assert real.read_bytes() == b'old'


@pytest.mark.parametrize('policy', [testee.OverwritePolicy.ALWAYS, testee.OverwritePolicy.NEVER])
def test_overwrite_policy_resolve_writes_through_dangling_symlink(policy, tmp_path, capsys):
    """Under ALWAYS and NEVER a dangling symlink holds no file, so its path is returned silently."""
    path = tmp_path / 'hello.mp4'
    path.symlink_to('missing.mp4')
    assert policy.resolve(path) == path
    assert capsys.readouterr().out == ''
    assert path.is_symlink() and not (tmp_path / 'missing.mp4').exists()


@pytest.mark.parametrize('policy', [testee.OverwritePolicy.ALWAYS, testee.OverwritePolicy.NEVER])
@pytest.mark.parametrize('entry', ['directory', 'directory-symlink', 'fifo'])
def test_overwrite_policy_resolve_rejects_existing_non_file(policy, entry, tmp_path, capsys):
    """Under ALWAYS and NEVER a directory, symlink to one, or FIFO raises NotAFileError, untouched."""
    path = tmp_path / 'hello.mp4'
    if entry == 'directory':
        path.mkdir()
    elif entry == 'directory-symlink':
        (tmp_path / 'dir').mkdir()
        path.symlink_to('dir')
    else:
        if not hasattr(os, 'mkfifo'):
            pytest.skip('FIFOs need os.mkfifo')
        os.mkfifo(path)
    before = sorted(p.name for p in tmp_path.iterdir())
    with pytest.raises(NotAFileError):
        policy.resolve(path)
    assert capsys.readouterr().out == ''
    assert sorted(p.name for p in tmp_path.iterdir()) == before


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
@pytest.mark.parametrize('policy', [testee.OverwritePolicy.ALWAYS, testee.OverwritePolicy.NEVER])
def test_overwrite_policy_resolve_raises_when_path_cannot_be_checked(policy, tmp_path):
    """An unsearchable directory raises PermissionError instead of being treated as no file."""
    directory = tmp_path / 'locked'
    directory.mkdir()
    directory.chmod(0o600)
    try:
        with pytest.raises(PermissionError):
            policy.resolve(directory / 'hello.mp4')
    finally:
        directory.chmod(0o700)


@pytest.mark.parametrize('entry', ['file', 'directory', 'dangling-symlink'])
def test_overwrite_policy_resolve_rename_numbers_beside_any_existing_entry(entry, tmp_path, capsys):
    """RENAME treats any entry as taken and returns the first free numbered path, saying so."""
    path = tmp_path / 'hello.mp4'
    if entry == 'file':
        path.write_bytes(b'old')
    elif entry == 'directory':
        path.mkdir()
    else:
        path.symlink_to('missing.mp4')
    (tmp_path / 'hello.1.mp4').write_bytes(b'one')
    before = sorted(p.name for p in tmp_path.iterdir())
    assert testee.OverwritePolicy.RENAME.resolve(path) == tmp_path / 'hello.2.mp4'
    assert capsys.readouterr().out == f'Not overwriting path: {path}, writing to: {tmp_path / "hello.2.mp4"}\n'
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_overwrite_policy_resolve_rename_raises_when_every_attempt_is_taken(tmp_path):
    """RENAME raises FileExistsError when the path and its numbered variants are all taken."""
    for name in ['hello.mp4'] + [f'hello.{n}.mp4' for n in range(1, 10)]:
        (tmp_path / name).write_bytes(b'x')
    with pytest.raises(FileExistsError):
        testee.OverwritePolicy.RENAME.resolve(tmp_path / 'hello.mp4')


def test_overwrite_policy_resolve_rename_honours_max_length(tmp_path):
    """Under RENAME, max_length bounds the numbered name in bytes."""
    path = tmp_path / 'abcdef.mp4'
    path.write_bytes(b'old')
    assert testee.OverwritePolicy.RENAME.resolve(path, max_length=10) == tmp_path / 'abcd.1.mp4'


@pytest.mark.parametrize(('max_attempts', 'expected'), [(1, None), (2, 'hello.1.mp4')])
def test_overwrite_policy_resolve_rename_honours_max_attempts(max_attempts, expected, tmp_path):
    """Under RENAME, max_attempts bounds how many names are checked."""
    path = tmp_path / 'hello.mp4'
    path.write_bytes(b'old')
    if expected is None:
        with pytest.raises(FileExistsError):
            testee.OverwritePolicy.RENAME.resolve(path, max_attempts=max_attempts)
    else:
        assert testee.OverwritePolicy.RENAME.resolve(path, max_attempts=max_attempts) == tmp_path / expected


@pytest.mark.parametrize('policy', [testee.OverwritePolicy.ALWAYS, testee.OverwritePolicy.NEVER])
def test_overwrite_policy_resolve_ignores_rename_limits_for_other_policies(policy, tmp_path):
    """max_length and max_attempts only matter under RENAME."""
    path = tmp_path / 'hello.mp4'
    assert policy.resolve(path, max_length=1, max_attempts=1) == path


@pytest.mark.filterwarnings('error')
@pytest.mark.parametrize('existing', [False, True])
@pytest.mark.parametrize('policy', list(testee.OverwritePolicy))
def test_overwrite_policy_values_and_resolve_emit_no_warning(policy, existing, tmp_path):
    """OverwritePolicy, unlike the deprecated OverwriteMode helpers, emits no warning."""
    path = tmp_path / 'hello.mp4'
    if existing:
        path.write_bytes(b'old')
    assert testee.OverwritePolicy.values() == ('always', 'never', 'rename')
    policy.resolve(path)
