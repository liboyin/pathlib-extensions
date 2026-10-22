import errno
import os
from pathlib import Path

import pytest

import pathlib_extensions.publication as testee
from pathlib_extensions.overwrite import OverwritePolicy
from pathlib_extensions.prepare import NotAFileError

PUBLISHING = list(OverwritePolicy)
KEEPING = [OverwritePolicy.NEVER, OverwritePolicy.RENAME]


def make_stage(directory: Path, content: bytes = b'new', mode: int = 0o600) -> Path:
    """Create a completed stage file with known content and mode."""
    stage = directory / '.stage.tmp'
    stage.write_bytes(content)
    stage.chmod(mode)
    return stage


def test_resolve_publication_target_absent_file_creates_parent_and_has_no_mode(tmp_path):
    """A missing destination resolves to itself, gains its parent and has no mode."""
    path = tmp_path / 'new' / 'out.bin'
    assert testee.resolve_publication_target(path) == (path.resolve(), None)
    assert path.parent.is_dir()


def test_resolve_publication_target_captures_existing_permission_bits(tmp_path):
    """An existing file's permission bits, including special bits, are captured."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    path.chmod(0o2640)
    assert testee.resolve_publication_target(path) == (path, 0o2640)


def test_resolve_publication_target_follows_symlink_to_existing_file(tmp_path):
    """A symlink resolves to its file target and reports the target's mode."""
    real = tmp_path / 'real.bin'
    real.write_bytes(b'old')
    real.chmod(0o640)
    link = tmp_path / 'link.bin'
    link.symlink_to(real.name)
    assert testee.resolve_publication_target(link) == (real, 0o640)


def test_resolve_publication_target_prepares_dangling_symlink_target_parent(tmp_path):
    """A dangling symlink resolves to its missing target, whose parent is created."""
    link = tmp_path / 'link.bin'
    link.symlink_to(tmp_path / 'missing' / 'real.bin')
    assert testee.resolve_publication_target(link) == (tmp_path / 'missing' / 'real.bin', None)
    assert (tmp_path / 'missing').is_dir()


def test_resolve_publication_target_rejects_symlink_to_directory(tmp_path):
    """A destination resolving to a directory is rejected before any stage is written."""
    (tmp_path / 'dir').mkdir()
    link = tmp_path / 'link.bin'
    link.symlink_to('dir')
    with pytest.raises(NotAFileError):
        testee.resolve_publication_target(link)


@pytest.mark.parametrize('policy', KEEPING)
def test_resolve_publication_target_keeping_policies_capture_no_mode_from_existing_file(policy, tmp_path):
    """Under NEVER and RENAME an existing file is never written, so its permission bits are not captured."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    path.chmod(0o640)
    assert testee.resolve_publication_target(path, policy) == (path, None)


@pytest.mark.parametrize('policy', KEEPING)
def test_resolve_publication_target_keeping_policies_create_parent_of_absent_file(policy, tmp_path):
    """Under NEVER and RENAME a missing destination still gains its parent directory."""
    path = tmp_path / 'new' / 'out.bin'
    assert testee.resolve_publication_target(path, policy) == (path, None)
    assert path.parent.is_dir()


@pytest.mark.parametrize('policy', KEEPING)
def test_resolve_publication_target_keeping_policies_reject_directory(policy, tmp_path):
    """Under NEVER and RENAME a destination that is a directory is still rejected."""
    with pytest.raises(NotAFileError):
        testee.resolve_publication_target(tmp_path, policy)


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
@pytest.mark.parametrize(('policy', 'accepted'), [(OverwritePolicy.ALWAYS, False), (OverwritePolicy.NEVER, True), (OverwritePolicy.RENAME, True)])
def test_resolve_publication_target_requires_writable_existing_file_only_under_always(policy, accepted, tmp_path):
    """A read-only existing file is rejected under ALWAYS, and left untouched under NEVER and RENAME."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    path.chmod(0o400)
    if accepted:
        assert testee.resolve_publication_target(path, policy) == (path, None)
    else:
        with pytest.raises(PermissionError):
            testee.resolve_publication_target(path, policy)
    assert path.read_bytes() == b'old'
    assert path.stat().st_mode & 0o7777 == 0o400


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
@pytest.mark.parametrize('via_symlink', [False, True], ids=['direct', 'symlink'])
@pytest.mark.parametrize('policy', PUBLISHING)
def test_resolve_publication_target_rejects_writable_file_in_unwritable_directory(via_symlink, policy, tmp_path):
    """A writable target is rejected when its resolved directory cannot hold a stage."""
    directory = tmp_path / 'out'
    directory.mkdir()
    real = directory / 'out.bin'
    real.write_bytes(b'old')
    path = real
    if via_symlink:
        path = tmp_path / 'link.bin'
        path.symlink_to(real)
    directory.chmod(0o500)
    try:
        with pytest.raises(PermissionError):
            testee.resolve_publication_target(path, policy)
    finally:
        directory.chmod(0o700)
    assert real.read_bytes() == b'old'


def test_publish_staged_file_replaces_existing_file_and_retains_its_mode(tmp_path):
    """ALWAYS publishes new bytes with the previous permission bits."""
    target = tmp_path / 'out.bin'
    target.write_bytes(b'old')
    target.chmod(0o640)
    stage = make_stage(tmp_path)
    assert testee.publish_staged_file(stage, target, 0o640, OverwritePolicy.ALWAYS) == target
    assert target.read_bytes() == b'new'
    assert target.stat().st_mode & 0o7777 == 0o640
    assert not stage.exists()


def test_publish_staged_file_without_mode_keeps_stage_permissions(tmp_path):
    """Without a captured mode, the published file keeps the stage's own permissions."""
    target = tmp_path / 'out.bin'
    testee.publish_staged_file(make_stage(tmp_path, mode=0o604), target, None, OverwritePolicy.ALWAYS)
    assert target.stat().st_mode & 0o7777 == 0o604


def test_publish_staged_file_replacement_follows_symlink_and_keeps_hardlink_alias(tmp_path):
    """Replacement through a resolved symlink keeps the link and leaves hardlink aliases old."""
    real = tmp_path / 'real.bin'
    real.write_bytes(b'old')
    real.chmod(0o640)
    alias = tmp_path / 'alias.bin'
    os.link(real, alias)
    link = tmp_path / 'link.bin'
    link.symlink_to(real.name)
    target, mode = testee.resolve_publication_target(link)
    testee.publish_staged_file(make_stage(tmp_path), target, mode, OverwritePolicy.ALWAYS)
    assert link.is_symlink()
    assert link.read_bytes() == real.read_bytes() == b'new'
    assert real.stat().st_mode & 0o7777 == 0o640
    assert alias.read_bytes() == b'old'


@pytest.mark.parametrize('existing', [True, False])
@pytest.mark.parametrize('policy', PUBLISHING)
def test_publish_staged_file_mode_failure_publishes_nothing(policy, existing, mocker, tmp_path):
    """A failed mode restoration raises before publication, leaving target and stage intact."""
    target = tmp_path / 'out.bin'
    if existing:
        target.write_bytes(b'old')
    stage = make_stage(tmp_path)
    mocker.patch.object(Path, 'chmod', side_effect=PermissionError('chmod failed'))
    with pytest.raises(PermissionError, match='chmod failed'):
        testee.publish_staged_file(stage, target, 0o640, policy)
    assert (target.read_bytes() == b'old') if existing else not target.exists()
    assert stage.read_bytes() == b'new'


@pytest.mark.parametrize('policy', KEEPING)
def test_publish_staged_file_links_absent_target(policy, tmp_path, capsys):
    """NEVER and RENAME publish to an absent target by hard link, under its own name."""
    target = tmp_path / 'out.bin'
    stage = make_stage(tmp_path)
    assert testee.publish_staged_file(stage, target, None, policy) == target
    assert capsys.readouterr().out == ''
    assert target.read_bytes() == b'new'
    assert os.path.samefile(stage, target)


@pytest.mark.parametrize('competitor', ['file', 'file-symlink'])
def test_publish_staged_file_never_keeps_completed_competitor(competitor, tmp_path):
    """Under NEVER a file, or symlink to one, that appeared at the target is kept, and None is returned."""
    target = tmp_path / 'out.bin'
    other = tmp_path / 'other.bin'
    if competitor == 'file':
        target.write_bytes(b'competitor')
    else:
        other.write_bytes(b'competitor')
        target.symlink_to(other.name)
    stage = make_stage(tmp_path)
    assert testee.publish_staged_file(stage, target, None, OverwritePolicy.NEVER) is None
    assert target.read_bytes() == b'competitor'
    assert target.is_symlink() == (competitor == 'file-symlink')
    assert stage.read_bytes() == b'new'


@pytest.mark.parametrize('competitor', ['directory', 'dangling-symlink'])
def test_publish_staged_file_never_raises_for_non_file_competitor(competitor, tmp_path):
    """Under NEVER a directory or dangling symlink at the target raises FileExistsError untouched."""
    target = tmp_path / 'out.bin'
    if competitor == 'directory':
        target.mkdir()
    else:
        target.symlink_to('missing.bin')
    with pytest.raises(FileExistsError):
        testee.publish_staged_file(make_stage(tmp_path), target, None, OverwritePolicy.NEVER)
    assert target.is_dir() if competitor == 'directory' else target.is_symlink() and not target.exists()


@pytest.mark.parametrize('policy', KEEPING)
def test_publish_staged_file_unsupported_hard_link_propagates_without_fallback(policy, mocker, tmp_path):
    """An unsupported hard link raises instead of falling back to an overwriting move."""
    target = tmp_path / 'out.bin'
    mocker.patch.object(os, 'link', side_effect=OSError(errno.EOPNOTSUPP, 'unsupported link'))
    with pytest.raises(OSError, match='unsupported link'):
        testee.publish_staged_file(make_stage(tmp_path), target, None, policy)
    assert not target.exists()


def test_publish_staged_file_replacement_failure_preserves_previous_file(mocker, tmp_path):
    """A failed replacement propagates and leaves the previous file intact."""
    target = tmp_path / 'out.bin'
    target.write_bytes(b'old')
    mocker.patch.object(Path, 'replace', side_effect=PermissionError('replace failed'))
    with pytest.raises(PermissionError, match='replace failed'):
        testee.publish_staged_file(make_stage(tmp_path), target, None, OverwritePolicy.ALWAYS)
    assert target.read_bytes() == b'old'


def test_publish_staged_file_rename_publishes_beside_existing_file(tmp_path, capsys):
    """RENAME keeps an existing target and publishes the stage at the first numbered name."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    stage = make_stage(tmp_path)
    published = testee.publish_staged_file(stage, target, None, OverwritePolicy.RENAME)
    assert published is not None
    assert published == tmp_path / 'hello.1.mp4'
    assert published.read_bytes() == b'new'
    assert os.path.samefile(stage, published)
    assert target.read_bytes() == b'old'
    assert capsys.readouterr().out == f'Renamed path: {target} -> {published}\n'


def test_publish_staged_file_rename_skips_every_taken_name_untouched(tmp_path):
    """RENAME passes over a file, a directory and a dangling symlink, leaving each as it was."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    (tmp_path / 'hello.1.mp4').write_bytes(b'one')
    (tmp_path / 'hello.2.mp4').mkdir()
    (tmp_path / 'hello.3.mp4').symlink_to('missing.mp4')
    published = testee.publish_staged_file(make_stage(tmp_path), target, None, OverwritePolicy.RENAME)
    assert published is not None
    assert published == tmp_path / 'hello.4.mp4'
    assert published.read_bytes() == b'new'
    assert target.read_bytes() == b'old'
    assert (tmp_path / 'hello.1.mp4').read_bytes() == b'one'
    assert (tmp_path / 'hello.2.mp4').is_dir()
    assert (tmp_path / 'hello.3.mp4').is_symlink() and not (tmp_path / 'missing.mp4').exists()


def test_publish_staged_file_rename_raises_when_no_numbered_name_fits(tmp_path):
    """RENAME raises ValueError when the suffix run leaves no room, keeping target and stage."""
    target = tmp_path / ('a' + '.x' * 127)
    assert len(target.name.encode('utf-8')) == 255
    target.write_bytes(b'old')
    stage = make_stage(tmp_path)
    with pytest.raises(ValueError):
        testee.publish_staged_file(stage, target, None, OverwritePolicy.RENAME)
    assert target.read_bytes() == b'old'
    assert stage.read_bytes() == b'new'
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted([target.name, stage.name])



def test_publish_staged_file_rename_applies_mode_to_new_file_only(tmp_path):
    """A mode passed with RENAME goes to the numbered file; the kept file and its alias are unchanged."""
    target = tmp_path / 'hello.mp4'
    target.write_bytes(b'old')
    target.chmod(0o604)
    alias = tmp_path / 'alias.mp4'
    os.link(target, alias)
    before = target.stat()
    published = testee.publish_staged_file(make_stage(tmp_path, mode=0o600), target, 0o640, OverwritePolicy.RENAME)
    assert published is not None
    assert published.stat().st_mode & 0o7777 == 0o640
    after = target.stat()
    assert (after.st_ino, after.st_mode & 0o7777) == (before.st_ino, 0o604)
    assert target.read_bytes() == alias.read_bytes() == b'old'


def test_rename_flow_publishes_beside_existing_file(tmp_path, capsys):
    """Resolving, preparing and publishing under RENAME writes a numbered file and keeps the original."""
    path = tmp_path / 'movie.mp4'
    path.write_bytes(b'old')
    path.chmod(0o604)
    resolved = OverwritePolicy.RENAME.resolve(path)
    assert resolved is not None
    target, mode = testee.resolve_publication_target(resolved, OverwritePolicy.RENAME)
    published = testee.publish_staged_file(make_stage(tmp_path, mode=0o644), target, mode, OverwritePolicy.RENAME)
    assert published is not None
    assert published == tmp_path / 'movie.1.mp4'
    assert published.read_bytes() == b'new'
    assert published.stat().st_mode & 0o7777 == 0o644
    assert path.read_bytes() == b'old'
    assert path.stat().st_mode & 0o7777 == 0o604
    assert capsys.readouterr().out == f'Not overwriting path: {path}, writing to: {published}\n'


def test_rename_flow_numbers_from_resolved_name_when_it_is_taken_meanwhile(tmp_path, capsys):
    """If the resolved name is taken before publication, RENAME numbers from that name and keeps both files."""
    path = tmp_path / 'movie.mp4'
    path.write_bytes(b'old')
    resolved = OverwritePolicy.RENAME.resolve(path)
    assert resolved is not None
    assert resolved == tmp_path / 'movie.1.mp4'
    target, mode = testee.resolve_publication_target(resolved, OverwritePolicy.RENAME)
    target.write_bytes(b'competitor')
    capsys.readouterr()
    published = testee.publish_staged_file(make_stage(tmp_path), target, mode, OverwritePolicy.RENAME)
    assert published is not None
    assert published == tmp_path / 'movie.1.1.mp4'
    assert published.read_bytes() == b'new'
    assert target.read_bytes() == b'competitor'
    assert path.read_bytes() == b'old'
    assert capsys.readouterr().out == f'Renamed path: {target} -> {published}\n'


@pytest.mark.parametrize(('existing', 'expected'), [(False, b'new'), (True, b'old')])
def test_never_flow_writes_only_when_no_file_exists(existing, expected, tmp_path):
    """Under NEVER an existing file makes resolve return None, so nothing is staged or published."""
    path = tmp_path / 'movie.mp4'
    if existing:
        path.write_bytes(b'old')
    resolved = OverwritePolicy.NEVER.resolve(path)
    if resolved is not None:
        target, mode = testee.resolve_publication_target(resolved, OverwritePolicy.NEVER)
        assert testee.publish_staged_file(make_stage(tmp_path), target, mode, OverwritePolicy.NEVER) == path
    assert (resolved is None) == existing
    assert path.read_bytes() == expected
