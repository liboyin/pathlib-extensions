import errno
import logging
import os
from pathlib import Path

import pytest

import pathlib_extensions.staging as testee
from pathlib_extensions.overwrite import OverwritePolicy
from pathlib_extensions.prepare import NotAFileError


def entries(directory: Path) -> list[str]:
    """List a directory's entry names, sorted, to detect leftovers."""
    return sorted(p.name for p in directory.iterdir())


@pytest.mark.parametrize('name', ['', '.', '..', 'a/b', '/video.mp4', 'video/', 'video\0.mp4'])
def test_staged_file_rejects_name_that_is_not_one_path_component(name, tmp_path):
    """An empty, `.` or `..` name, or one with a separator or NUL, raises ValueError before anything is created."""
    target = tmp_path / 'out' / 'hello.mp4'
    with pytest.raises(ValueError, match='single path component'):
        testee.StagedFile(target, OverwritePolicy.ALWAYS, name=name)
    assert entries(tmp_path) == []


def test_staged_file_rejects_name_containing_alternative_separator(monkeypatch, tmp_path):
    """Where the platform has an alternative separator, a name containing it is rejected too."""
    monkeypatch.setattr(testee.os, 'altsep', '\\')
    with pytest.raises(ValueError, match='single path component'):
        testee.StagedFile(tmp_path / 'hello.mp4', OverwritePolicy.ALWAYS, name='a\\b')
    assert entries(tmp_path) == []


def test_staged_file_stages_a_fresh_path_named_like_the_target_beside_it(tmp_path):
    """The body gets a not-yet-existing path named like the target, in a hidden directory beside it."""
    target = tmp_path / 'hello.en.srt'
    with testee.StagedFile(target, OverwritePolicy.ALWAYS) as staged:
        assert staged.target == target
        assert staged.path.name == 'hello.en.srt'
        assert staged.path.parent.parent == tmp_path
        assert staged.path.parent.name.startswith('.staging-')
        assert not staged.path.exists()
        staged.path.write_text('new')
    assert target.read_text() == 'new'


@pytest.mark.parametrize('policy', list(OverwritePolicy))
def test_staged_file_with_name_stages_under_that_name_and_publishes_to_target(policy, tmp_path, package_logs):
    """A named stage file sits in the stage directory under that name, is published to the target and leaves no stage behind."""
    target = tmp_path / 'Title [abc].mp4'
    unrelated = tmp_path / 'video.mp4'
    unrelated.write_bytes(b'unrelated')
    with testee.StagedFile(target, policy, name='video.mp4') as staged:
        assert staged.target == target
        assert staged.path.name == 'video.mp4'
        assert staged.path.parent.parent == tmp_path
        assert staged.path.parent.name.startswith('.staging-')
        assert not staged.path.exists()
        staged.path.write_bytes(b'new')
        (staged.path.parent / 'video.mp4.part').write_bytes(b'tool temp file')
    assert staged.published == target
    assert target.read_bytes() == b'new'
    assert unrelated.read_bytes() == b'unrelated'
    assert entries(tmp_path) == ['Title [abc].mp4', 'video.mp4']
    assert package_logs.record_tuples == []


def test_staged_file_with_name_always_replaces_symlinked_file_with_another_suffix(tmp_path):
    """A name taken from a symlink whose target has another suffix still replaces the real file, keeping its mode and the link."""
    real_dir = tmp_path / 'real'
    real_dir.mkdir()
    real = real_dir / 'audio.data'
    real.write_bytes(b'old')
    real.chmod(0o640)
    link = tmp_path / 'audio.wav'
    link.symlink_to(real)
    with testee.StagedFile(link, OverwritePolicy.ALWAYS, name=link.name) as staged:
        assert staged.target == real
        assert staged.path.name == 'audio.wav'
        assert staged.path.parent.parent == real_dir
        staged.path.write_bytes(b'new')
        assert real.read_bytes() == b'old'
    assert staged.published == real
    assert link.is_symlink() and link.read_bytes() == b'new'
    assert real.stat().st_mode & 0o7777 == 0o640
    assert entries(real_dir) == ['audio.data']


def test_staged_file_with_name_never_keeps_file_that_appeared_at_target(tmp_path):
    """Under NEVER a named stage still checks the target, not its own name, and keeps a file that appeared there."""
    target = tmp_path / 'hello.mp4'
    with testee.StagedFile(target, OverwritePolicy.NEVER, name='video.mp4') as staged:
        staged.path.write_bytes(b'new')
        target.write_bytes(b'competitor')
    assert staged.published is None
    assert target.read_bytes() == b'competitor'
    assert entries(tmp_path) == ['hello.mp4']


@pytest.mark.parametrize('policy', list(OverwritePolicy))
def test_staged_file_publishes_to_absent_target_and_cleans_up(policy, tmp_path, package_logs):
    """Every policy publishes to a free target and leaves no stage behind."""
    target = tmp_path / 'hello.mp4'
    with testee.StagedFile(target, policy) as staged:
        staged.path.write_bytes(b'new')
        (staged.path.parent / 'hello.mp4.part').write_bytes(b'tool temp file')
    assert staged.published == target
    assert target.read_bytes() == b'new'
    assert entries(tmp_path) == ['hello.mp4']
    assert package_logs.record_tuples == []


def test_staged_file_always_replaces_existing_file_keeping_its_mode(tmp_path):
    """ALWAYS replaces an existing file atomically and keeps its permission bits."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    target.chmod(0o640)
    with testee.StagedFile(target, OverwritePolicy.ALWAYS) as staged:
        staged.path.write_bytes(b'new')
        assert target.read_bytes() == b'old'
    assert staged.published == target
    assert target.read_bytes() == b'new'
    assert target.stat().st_mode & 0o7777 == 0o640
    assert entries(tmp_path) == ['hello.mp4']


def test_staged_file_always_replaces_target_inode_leaving_hardlink_alias_old(tmp_path):
    """ALWAYS swaps in a new inode instead of writing the old one in place, so a hard-linked alias keeps the old bytes."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    alias = tmp_path / 'alias.mp4'
    os.link(target, alias)
    old_inode = target.stat().st_ino
    with testee.StagedFile(target, OverwritePolicy.ALWAYS) as staged:
        staged.path.write_bytes(b'new')
    assert staged.published == target
    assert target.read_bytes() == b'new'
    assert target.stat().st_ino != old_inode
    assert alias.read_bytes() == b'old'
    assert alias.stat().st_ino == old_inode
    assert entries(tmp_path) == ['alias.mp4', 'hello.mp4']


def test_staged_file_always_through_symlink_replaces_real_file_and_keeps_link(tmp_path):
    """A symlinked destination is resolved: the real file is replaced and the link kept."""
    real_dir = tmp_path / 'real'
    real_dir.mkdir()
    real = real_dir / 'hello.mp4'
    real.write_bytes(b'old')
    link = tmp_path / 'link.mp4'
    link.symlink_to(real)
    with testee.StagedFile(link, OverwritePolicy.ALWAYS) as staged:
        assert staged.target == real
        assert staged.path.parent.parent == real_dir
        staged.path.write_bytes(b'new')
    assert staged.published == real
    assert link.is_symlink() and link.read_bytes() == b'new'
    assert entries(real_dir) == ['hello.mp4']


def test_staged_file_never_keeps_file_that_appeared_meanwhile(tmp_path):
    """NEVER keeps a file that appeared during the body and reports nothing published."""
    target = tmp_path / 'hello.mp4'
    with testee.StagedFile(target, OverwritePolicy.NEVER) as staged:
        staged.path.write_bytes(b'new')
        target.write_bytes(b'competitor')
    assert staged.published is None
    assert target.read_bytes() == b'competitor'
    assert entries(tmp_path) == ['hello.mp4']


@pytest.mark.parametrize('competitor', ['directory', 'dangling-symlink'])
def test_staged_file_never_raises_for_non_file_that_appeared_at_target(competitor, tmp_path):
    """Under NEVER a directory or dangling symlink that appeared at the target is not a kept file: FileExistsError, untouched."""
    target = tmp_path / 'hello.mp4'
    with pytest.raises(FileExistsError), testee.StagedFile(target, OverwritePolicy.NEVER) as staged:
        staged.path.write_bytes(b'new')
        if competitor == 'directory':
            target.mkdir()
        else:
            target.symlink_to('missing.mp4')
    assert staged.published is None
    if competitor == 'directory':
        assert target.is_dir() and entries(target) == []
    else:
        assert target.is_symlink() and not (tmp_path / 'missing.mp4').exists()
    assert entries(tmp_path) == ['hello.mp4']


def test_staged_file_rename_publishes_beside_file_that_appeared_meanwhile(tmp_path, package_logs):
    """RENAME publishes under the next numbered name when the target was taken during the body."""
    target = tmp_path / 'hello.mp4'
    with testee.StagedFile(target, OverwritePolicy.RENAME) as staged:
        staged.path.write_bytes(b'new')
        target.write_bytes(b'competitor')
    assert staged.published == tmp_path / 'hello.1.mp4'
    assert staged.published is not None
    assert staged.published.read_bytes() == b'new'
    assert target.read_bytes() == b'competitor'
    assert entries(tmp_path) == ['hello.1.mp4', 'hello.mp4']
    assert package_logs.record_tuples == [(testee.__name__, logging.INFO, f'Renamed path: {target} -> {staged.published}')]



@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
@pytest.mark.parametrize(('policy', 'expected'), [(OverwritePolicy.NEVER, None), (OverwritePolicy.RENAME, 'hello.1.mp4')])
def test_staged_file_keeping_policies_accept_read_only_target_and_copy_no_mode(policy, expected, tmp_path):
    """Under NEVER and RENAME a read-only file at the target is kept as is, and its mode is not given to the new file."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    target.chmod(0o400)
    with testee.StagedFile(target, policy) as staged:
        staged.path.write_bytes(b'new')
        staged.path.chmod(0o604)
    if expected is None:
        assert staged.published is None
    else:
        assert staged.published == tmp_path / expected
        assert staged.published is not None
        assert staged.published.read_bytes() == b'new'
        assert staged.published.stat().st_mode & 0o7777 == 0o604
    assert target.read_bytes() == b'old'
    assert target.stat().st_mode & 0o7777 == 0o400

@pytest.mark.parametrize('error', [ValueError('download failed'), KeyboardInterrupt()])
@pytest.mark.parametrize('policy', list(OverwritePolicy))
def test_staged_file_body_failure_publishes_nothing_and_cleans_up(policy, error, tmp_path):
    """An exception, or an interrupt, in the body propagates, leaves the target as it was and removes the stage."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    with pytest.raises(type(error)), testee.StagedFile(target, policy) as staged:
        staged.path.write_bytes(b'partial')
        raise error
    assert staged.published is None
    assert target.read_bytes() == b'old'
    assert entries(tmp_path) == ['hello.mp4']


def make_unremovable(stage_dir: Path) -> Path:
    """Put a file in a read-only subdirectory of the stage directory so removing it fails; return the subdirectory."""
    locked = stage_dir / 'locked'
    locked.mkdir()
    (locked / 'tool.tmp').write_bytes(b'x')
    locked.chmod(0o500)
    return locked


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
def test_staged_file_body_failure_is_not_hidden_by_cleanup_failure(tmp_path):
    """If the stage cannot be removed after the body failed, the body's exception still propagates."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    locked = None
    try:
        with pytest.raises(ValueError, match='download failed'), testee.StagedFile(target, OverwritePolicy.ALWAYS) as staged:
            staged.path.write_bytes(b'partial')
            locked = make_unremovable(staged.path.parent)
            raise ValueError('download failed')
        assert staged.published is None
        assert target.read_bytes() == b'old'
    finally:
        if locked is not None:
            locked.chmod(0o700)


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
def test_staged_file_exit_failure_is_not_hidden_by_cleanup_failure(tmp_path):
    """If nothing was staged and the stage cannot be removed, FileNotFoundError still propagates."""
    target = tmp_path / 'hello.mp4'
    locked = None
    try:
        with pytest.raises(FileNotFoundError, match='Nothing was staged'), testee.StagedFile(target, OverwritePolicy.ALWAYS) as staged:
            locked = make_unremovable(staged.path.parent)
        assert not target.exists()
    finally:
        if locked is not None:
            locked.chmod(0o700)


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
def test_staged_file_cleanup_failure_after_publication_is_raised(tmp_path):
    """After a clean exit, a failure to remove the stage is raised, although the file is already published."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    locked = None
    try:
        with pytest.raises(PermissionError), testee.StagedFile(target, OverwritePolicy.ALWAYS) as staged:
            staged.path.write_bytes(b'new')
            locked = make_unremovable(staged.path.parent)
        assert staged.published == target
        assert target.read_bytes() == b'new'
    finally:
        if locked is not None:
            locked.chmod(0o700)


@pytest.mark.parametrize('policy', list(OverwritePolicy))
def test_staged_file_raises_when_body_staged_nothing(policy, tmp_path):
    """A clean exit without a staged file raises FileNotFoundError and publishes nothing."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    with pytest.raises(FileNotFoundError, match='Nothing was staged'), testee.StagedFile(target, policy) as staged:
        pass
    assert staged.published is None
    assert target.read_bytes() == b'old'
    assert entries(tmp_path) == ['hello.mp4']


@pytest.mark.parametrize('entry', ['directory', 'file-symlink', 'dangling-symlink'])
@pytest.mark.parametrize('policy', list(OverwritePolicy))
def test_staged_file_rejects_staged_entry_that_is_not_a_regular_file(policy, entry, tmp_path):
    """A staged directory or symlink raises NotAFileError; nothing is published and the link target is untouched."""
    target = tmp_path / 'hello.mp4'
    outside = tmp_path / 'outside.mp4'
    outside.write_bytes(b'outside')
    with pytest.raises(NotAFileError), testee.StagedFile(target, policy) as staged:
        if entry == 'directory':
            staged.path.mkdir()
        elif entry == 'file-symlink':
            staged.path.symlink_to(outside)
        else:
            staged.path.symlink_to(tmp_path / 'missing.mp4')
    assert staged.published is None
    assert not target.exists() and not target.is_symlink()
    assert outside.read_bytes() == b'outside'
    assert entries(tmp_path) == ['outside.mp4']


def test_staged_file_mode_restoration_failure_publishes_nothing_and_cleans_up(mocker, tmp_path):
    """Under ALWAYS, failing to give the staged file the target's mode propagates, leaves the target as it was and removes the stage."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    target.chmod(0o640)
    with pytest.raises(PermissionError, match='chmod failed'), testee.StagedFile(target, OverwritePolicy.ALWAYS) as staged:
        staged.path.write_bytes(b'new')
        mocker.patch.object(Path, 'chmod', side_effect=PermissionError('chmod failed'))
    assert staged.published is None
    assert target.read_bytes() == b'old'
    assert target.stat().st_mode & 0o7777 == 0o640
    assert entries(tmp_path) == ['hello.mp4']


def test_staged_file_publication_failure_propagates_and_cleans_up(mocker, tmp_path):
    """A failed publication propagates, leaves the target absent and removes the stage."""
    target = tmp_path / 'hello.mp4'
    mocker.patch.object(os, 'link', side_effect=OSError(errno.EOPNOTSUPP, 'unsupported link'))
    with pytest.raises(OSError, match='unsupported link'), testee.StagedFile(target, OverwritePolicy.NEVER) as staged:
        staged.path.write_bytes(b'new')
    assert staged.published is None
    assert entries(tmp_path) == []


def test_staged_file_rejects_directory_target_before_staging(tmp_path):
    """A destination that is a directory raises on entry, before any stage exists."""
    target = tmp_path / 'hello.mp4'
    target.mkdir()
    with pytest.raises(NotAFileError), testee.StagedFile(target, OverwritePolicy.ALWAYS):
        pytest.fail('the body must not run')
    assert entries(tmp_path) == ['hello.mp4']


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
def test_staged_file_always_rejects_read_only_target_before_staging(tmp_path):
    """ALWAYS raises PermissionError on entry for a read-only existing file, which is left as it was."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    target.chmod(0o400)
    with pytest.raises(PermissionError), testee.StagedFile(target, OverwritePolicy.ALWAYS):
        pytest.fail('the body must not run')
    assert target.read_bytes() == b'old'
    assert target.stat().st_mode & 0o7777 == 0o400
    assert entries(tmp_path) == ['hello.mp4']


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
@pytest.mark.parametrize('via_symlink', [False, True], ids=['direct', 'symlink'])
@pytest.mark.parametrize('policy', list(OverwritePolicy))
def test_staged_file_rejects_target_directory_that_cannot_hold_a_stage(policy, via_symlink, tmp_path):
    """A writable target in a directory that cannot take new entries is rejected on entry with PermissionError naming that directory."""
    directory = tmp_path / 'out'
    directory.mkdir()
    real = directory / 'hello.mp4'
    real.write_bytes(b'old')
    path = real
    if via_symlink:
        path = tmp_path / 'link.mp4'
        path.symlink_to(real)
    directory.chmod(0o500)
    try:
        with pytest.raises(PermissionError) as excinfo, testee.StagedFile(path, policy):
            pytest.fail('the body must not run')
    finally:
        directory.chmod(0o700)
    # The directory check names the directory; failing later, when creating the stage, would name the stage instead.
    assert excinfo.value.args == (directory,)
    assert real.read_bytes() == b'old'
    assert entries(directory) == ['hello.mp4']


def test_staged_file_creates_missing_parent_directories(tmp_path):
    """Missing parents of the destination are created on entry."""
    target = tmp_path / 'a' / 'b' / 'hello.mp4'
    with testee.StagedFile(target, OverwritePolicy.ALWAYS) as staged:
        staged.path.write_bytes(b'new')
    assert target.read_bytes() == b'new'
    assert entries(target.parent) == ['hello.mp4']


def test_staged_file_can_be_entered_only_once(tmp_path):
    """Entering the same instance again raises RuntimeError without touching the published file."""
    target = tmp_path / 'hello.mp4'
    staged = testee.StagedFile(target, OverwritePolicy.ALWAYS)
    with staged:
        staged.path.write_bytes(b'new')
    with pytest.raises(RuntimeError), staged:
        pytest.fail('the body must not run')
    assert target.read_bytes() == b'new'
    assert entries(tmp_path) == ['hello.mp4']


@pytest.mark.filterwarnings('error')
@pytest.mark.parametrize('existing', [False, True])
@pytest.mark.parametrize('policy', list(OverwritePolicy))
def test_staged_file_emits_no_warning(policy, existing, tmp_path):
    """StagedFile does not go through the deprecated publication functions, so it emits no warning."""
    target = tmp_path / 'hello.mp4'
    if existing:
        target.write_bytes(b'old')
    with testee.StagedFile(target, policy) as staged:
        staged.path.write_bytes(b'new')
    published = {OverwritePolicy.ALWAYS: target, OverwritePolicy.NEVER: None, OverwritePolicy.RENAME: tmp_path / 'hello.1.mp4'}
    assert staged.published == (published[policy] if existing else target)


def test_staged_file_is_exported_from_package():
    """StagedFile is part of the package's public API."""
    import pathlib_extensions
    assert pathlib_extensions.StagedFile is testee.StagedFile
    assert testee.__all__ == ['StagedFile']
