import errno
import os
from pathlib import Path

import pytest

from pathlib_extensions.overwrite import OverwriteMode
from pathlib_extensions.prepare import NotAFileError
from pathlib_extensions.publication import publish_staged_file, resolve_publication_target

PRESERVING = [OverwriteMode.NEVER, OverwriteMode.RENAME]
REPLACING = [OverwriteMode.ALWAYS, OverwriteMode.PROMPT]


def make_stage(directory: Path, content: bytes = b'new', mode: int = 0o600) -> Path:
    """Create a completed stage file with known content and mode."""
    stage = directory / '.stage.tmp'
    stage.write_bytes(content)
    stage.chmod(mode)
    return stage


def test_resolve_publication_target_absent_file_creates_parent_and_has_no_mode(tmp_path):
    """A missing destination resolves to itself, gains its parent and has no mode."""
    path = tmp_path / 'new' / 'out.bin'
    assert resolve_publication_target(path) == (path.resolve(), None)
    assert path.parent.is_dir()


def test_resolve_publication_target_captures_existing_permission_bits(tmp_path):
    """An existing file's permission bits, including special bits, are captured."""
    path = tmp_path / 'out.bin'
    path.write_bytes(b'old')
    path.chmod(0o2640)
    assert resolve_publication_target(path) == (path, 0o2640)


def test_resolve_publication_target_follows_symlink_to_existing_file(tmp_path):
    """A symlink resolves to its file target and reports the target's mode."""
    real = tmp_path / 'real.bin'
    real.write_bytes(b'old')
    real.chmod(0o640)
    link = tmp_path / 'link.bin'
    link.symlink_to(real.name)
    assert resolve_publication_target(link) == (real, 0o640)


def test_resolve_publication_target_prepares_dangling_symlink_target_parent(tmp_path):
    """A dangling symlink resolves to its missing target, whose parent is created."""
    link = tmp_path / 'link.bin'
    link.symlink_to(tmp_path / 'missing' / 'real.bin')
    assert resolve_publication_target(link) == (tmp_path / 'missing' / 'real.bin', None)
    assert (tmp_path / 'missing').is_dir()


def test_resolve_publication_target_rejects_symlink_to_directory(tmp_path):
    """A destination resolving to a directory is rejected before any stage is written."""
    (tmp_path / 'dir').mkdir()
    link = tmp_path / 'link.bin'
    link.symlink_to('dir')
    with pytest.raises(NotAFileError):
        resolve_publication_target(link)


@pytest.mark.parametrize('policy', REPLACING)
def test_publish_staged_file_replaces_existing_file_and_retains_its_mode(policy, tmp_path):
    """Replacing modes publish new bytes with the previous permission bits."""
    target = tmp_path / 'out.bin'
    target.write_bytes(b'old')
    target.chmod(0o640)
    stage = make_stage(tmp_path)
    publish_staged_file(stage, target, 0o640, policy)
    assert target.read_bytes() == b'new'
    assert target.stat().st_mode & 0o7777 == 0o640
    assert not stage.exists()


def test_publish_staged_file_without_mode_keeps_stage_permissions(tmp_path):
    """Without a captured mode, the published file keeps the stage's own permissions."""
    target = tmp_path / 'out.bin'
    publish_staged_file(make_stage(tmp_path, mode=0o604), target, None, OverwriteMode.ALWAYS)
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
    target, mode = resolve_publication_target(link)
    publish_staged_file(make_stage(tmp_path), target, mode, OverwriteMode.ALWAYS)
    assert link.is_symlink()
    assert link.read_bytes() == real.read_bytes() == b'new'
    assert real.stat().st_mode & 0o7777 == 0o640
    assert alias.read_bytes() == b'old'



@pytest.mark.parametrize('existing', [True, False])
@pytest.mark.parametrize('policy', list(OverwriteMode))
def test_publish_staged_file_mode_failure_publishes_nothing(policy, existing, mocker, tmp_path):
    """A failed mode restoration raises before publication, leaving target and stage intact."""
    target = tmp_path / 'out.bin'
    if existing:
        target.write_bytes(b'old')
    stage = make_stage(tmp_path)
    mocker.patch.object(Path, 'chmod', side_effect=PermissionError('chmod failed'))
    with pytest.raises(PermissionError, match='chmod failed'):
        publish_staged_file(stage, target, 0o640, policy)
    assert (target.read_bytes() == b'old') if existing else not target.exists()
    assert stage.read_bytes() == b'new'


@pytest.mark.parametrize('policy', PRESERVING)
def test_publish_staged_file_creates_absent_target_under_preserving_policies(policy, tmp_path):
    """Preserving policies publish to an absent target by hard link."""
    target = tmp_path / 'out.bin'
    stage = make_stage(tmp_path)
    publish_staged_file(stage, target, None, policy)
    assert target.read_bytes() == b'new'
    assert os.path.samefile(stage, target)


@pytest.mark.parametrize('policy', PRESERVING)
@pytest.mark.parametrize('competitor', ['file', 'file-symlink'])
def test_publish_staged_file_keeps_completed_competitor_under_preserving_policies(policy, competitor, tmp_path):
    """A file, or symlink to one, that appeared at the target is kept and not replaced."""
    target = tmp_path / 'out.bin'
    other = tmp_path / 'other.bin'
    if competitor == 'file':
        target.write_bytes(b'competitor')
    else:
        other.write_bytes(b'competitor')
        target.symlink_to(other.name)
    stage = make_stage(tmp_path)
    publish_staged_file(stage, target, None, policy)
    assert target.read_bytes() == b'competitor'
    assert target.is_symlink() == (competitor == 'file-symlink')
    assert stage.read_bytes() == b'new'


@pytest.mark.parametrize('policy', PRESERVING)
@pytest.mark.parametrize('competitor', ['directory', 'dangling-symlink'])
def test_publish_staged_file_raises_for_non_file_competitor_under_preserving_policies(policy, competitor, tmp_path):
    """A directory or dangling symlink at the target raises FileExistsError untouched."""
    target = tmp_path / 'out.bin'
    if competitor == 'directory':
        target.mkdir()
    else:
        target.symlink_to('missing.bin')
    with pytest.raises(FileExistsError):
        publish_staged_file(make_stage(tmp_path), target, None, policy)
    assert target.is_dir() if competitor == 'directory' else target.is_symlink() and not target.exists()


@pytest.mark.parametrize('policy', PRESERVING)
def test_publish_staged_file_unsupported_hard_link_propagates_without_fallback(policy, mocker, tmp_path):
    """An unsupported hard link raises instead of falling back to an overwriting move."""
    target = tmp_path / 'out.bin'
    mocker.patch.object(os, 'link', side_effect=OSError(errno.EOPNOTSUPP, 'unsupported link'))
    with pytest.raises(OSError, match='unsupported link'):
        publish_staged_file(make_stage(tmp_path), target, None, policy)
    assert not target.exists()


def test_publish_staged_file_replacement_failure_preserves_previous_file(mocker, tmp_path):
    """A failed replacement propagates and leaves the previous file intact."""
    target = tmp_path / 'out.bin'
    target.write_bytes(b'old')
    # Path.replace binds os.replace at import time on Python 3.10, so patch the method.
    mocker.patch.object(Path, 'replace', side_effect=PermissionError('replace failed'))
    with pytest.raises(PermissionError, match='replace failed'):
        publish_staged_file(make_stage(tmp_path), target, None, OverwriteMode.ALWAYS)
    assert target.read_bytes() == b'old'
