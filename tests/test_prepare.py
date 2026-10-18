import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

import pathlib_extensions.prepare as testee

requires_permission_enforcement = pytest.mark.skipif(
    os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users'
)


@pytest.fixture
def restrict() -> Iterator[Callable[[Path, int], None]]:
    """Change path modes for a test and restore owner access before temporary-path cleanup."""
    changed: list[Path] = []

    def apply(path: Path, mode: int) -> None:
        path.chmod(mode)
        changed.append(path)

    yield apply
    for path in reversed(changed):
        path.chmod(0o700)


def test_prepare_input_dir_valid():
    d = Path.cwd()
    assert testee.prepare_input_dir(d) is d


def test_prepare_input_dir_invalid():
    with pytest.raises(NotADirectoryError):
        testee.prepare_input_dir(__file__)


def test_prepare_input_dir_not_found():
    with pytest.raises(FileNotFoundError):
        testee.prepare_input_dir('path/that/does/not/exist')


@requires_permission_enforcement
@pytest.mark.parametrize('mode', [0o100, 0o400], ids=['search-only', 'list-only'])
def test_prepare_input_dir_requires_read_and_search_permission(mode, tmp_path, restrict):
    """A directory that cannot be both listed and searched is rejected."""
    d = tmp_path / 'in'
    d.mkdir()
    restrict(d, mode)
    with pytest.raises(PermissionError):
        testee.prepare_input_dir(d)


@requires_permission_enforcement
def test_prepare_input_dir_accepts_unwritable_directory(tmp_path, restrict):
    """Reading a directory does not require write permission to it."""
    d = tmp_path / 'in'
    d.mkdir()
    restrict(d, 0o500)
    assert testee.prepare_input_dir(d) is d


def test_prepare_input_file_valid():
    assert testee.prepare_input_file(__file__) == Path(__file__)


def test_prepare_input_file_invalid():
    with pytest.raises(testee.NotAFileError):
        testee.prepare_input_file(Path.cwd())


def test_prepare_input_file_not_found():
    with pytest.raises(FileNotFoundError):
        testee.prepare_input_file('file/that/does/not/exist')


def test_prepare_input_file_check_suffix():
    with pytest.raises(testee.SuffixError):
        testee.prepare_input_file(__file__, check_suffix='.txt')


def test_prepare_input_file_matching_check_suffix_is_accepted():
    """A file whose suffix matches the expected suffix is returned unchanged."""
    assert testee.prepare_input_file(__file__, check_suffix='.py') == Path(__file__)


def test_prepare_input_file_with_suffix():
    assert testee.prepare_input_file(__file__, with_suffix='.py') == Path(__file__)


def test_prepare_input_file_invalid_argument():
    with pytest.raises(ValueError):
        testee.prepare_input_file(__file__, check_suffix='.txt', with_suffix='.txt')


@requires_permission_enforcement
def test_prepare_input_file_unreadable_raises_permission_error(tmp_path, restrict):
    """An existing file without read permission is rejected."""
    p = tmp_path / 'in.txt'
    p.touch()
    restrict(p, 0o200)
    with pytest.raises(PermissionError):
        testee.prepare_input_file(p)


def test_prepare_output_dir_valid():
    d = Path.cwd()
    assert testee.prepare_output_dir(d) is d


def test_prepare_output_dir_invalid():
    with pytest.raises(NotADirectoryError):
        testee.prepare_output_dir(__file__)


def test_prepare_output_dir_create(tmp_path):
    """A missing directory is created together with its missing parents."""
    d = tmp_path / "sub1" / "sub2"
    assert testee.prepare_output_dir(d, create=True) is d
    assert d.is_dir()


def test_prepare_output_dir_missing_without_create_raises_file_not_found(tmp_path):
    """A missing directory is reported as missing, not created, when creation is disabled."""
    d = tmp_path / 'missing'
    with pytest.raises(FileNotFoundError):
        testee.prepare_output_dir(d, create=False)
    assert not d.exists()


@pytest.mark.parametrize('create', [True, False])
def test_prepare_output_dir_file_ancestor_raises_not_a_directory(create, tmp_path):
    """A regular file in the ancestry is reported as such and left unchanged."""
    blocker = tmp_path / 'blocker'
    blocker.write_bytes(b'keep')
    with pytest.raises(NotADirectoryError):
        testee.prepare_output_dir(blocker / 'sub', create=create)
    assert blocker.read_bytes() == b'keep'


@requires_permission_enforcement
@pytest.mark.parametrize('mode', [0o500, 0o600], ids=['no-write', 'no-search'])
def test_prepare_output_dir_requires_write_and_search_permission(mode, tmp_path, restrict):
    """An existing directory that cannot accept new entries is rejected."""
    d = tmp_path / 'out'
    d.mkdir()
    restrict(d, mode)
    with pytest.raises(PermissionError):
        testee.prepare_output_dir(d)


@requires_permission_enforcement
@pytest.mark.parametrize('create', [True, False])
def test_prepare_output_dir_unsearchable_ancestor_raises_permission_error(create, tmp_path, restrict):
    """A directory behind an unsearchable ancestor is a permission problem, not a missing path."""
    parent = tmp_path / 'parent'
    parent.mkdir()
    restrict(parent, 0o600)
    with pytest.raises(PermissionError):
        testee.prepare_output_dir(parent / 'sub', create=create)
    parent.chmod(0o700)
    assert not (parent / 'sub').exists()


def test_prepare_output_file_valid(tmp_path):
    assert testee.prepare_output_file(__file__) == Path(__file__)


def test_prepare_output_file_invalid(tmp_path):
    with pytest.raises(testee.NotAFileError):
        testee.prepare_output_file(tmp_path)


def test_prepare_output_file_check_suffix(tmp_path):
    p = tmp_path / "testfile.txt"
    p.touch()
    with pytest.raises(testee.SuffixError):
        testee.prepare_output_file(p, check_suffix='.py')


def test_prepare_output_file_matching_check_suffix_is_accepted(tmp_path):
    """An output file whose suffix matches the expected suffix is returned unchanged."""
    p = tmp_path / "testfile.txt"
    assert testee.prepare_output_file(p, check_suffix='.txt') == p


def test_prepare_output_file_with_suffix(tmp_path):
    p = tmp_path / "testfile"
    p.touch()
    assert testee.prepare_output_file(p, with_suffix='.txt') == tmp_path / "testfile.txt"


def test_prepare_output_file_invalid_argument(tmp_path):
    p = tmp_path / "testfile"
    p.touch()
    with pytest.raises(ValueError):
        testee.prepare_output_file(p, check_suffix='.txt', with_suffix='.txt')


@requires_permission_enforcement
def test_prepare_output_file_existing_unwritable_file_raises_permission_error(tmp_path, restrict):
    """An existing file without write permission is rejected."""
    p = tmp_path / 'out.txt'
    p.touch()
    restrict(p, 0o400)
    with pytest.raises(PermissionError):
        testee.prepare_output_file(p)


@requires_permission_enforcement
def test_prepare_output_file_existing_file_in_unwritable_directory_is_accepted(tmp_path, restrict):
    """A writable existing file only needs in-place write access, not a writable directory."""
    p = tmp_path / 'out.txt'
    p.touch()
    restrict(tmp_path, 0o500)
    assert testee.prepare_output_file(p) == p


@requires_permission_enforcement
@pytest.mark.parametrize('mode', [0o500, 0o600], ids=['no-write', 'no-search'])
def test_prepare_output_file_new_file_requires_parent_write_and_search_permission(mode, tmp_path, restrict):
    """A new file is rejected when its parent directory cannot accept new entries."""
    d = tmp_path / 'out'
    d.mkdir()
    restrict(d, mode)
    with pytest.raises(PermissionError):
        testee.prepare_output_file(d / 'new.txt')


def test_prepare_output_file_creates_missing_parents_but_not_file(tmp_path):
    """Missing parents of a new file are created, while the file itself is not."""
    p = tmp_path / 'a' / 'b' / 'new.txt'
    assert testee.prepare_output_file(p) == p
    assert p.parent.is_dir()
    assert not p.exists()


def test_prepare_output_file_missing_parent_without_create_raises_file_not_found(tmp_path):
    """A new file under a missing parent is rejected, without creating it, when creation is disabled."""
    p = tmp_path / 'missing' / 'new.txt'
    with pytest.raises(FileNotFoundError):
        testee.prepare_output_file(p, create=False)
    assert not p.parent.exists()


@pytest.mark.parametrize('create', [True, False])
def test_prepare_output_file_parent_is_file_raises_not_a_directory(create, tmp_path):
    """A new file whose parent path is a regular file is rejected and the file left unchanged."""
    blocker = tmp_path / 'blocker'
    blocker.write_bytes(b'keep')
    with pytest.raises(NotADirectoryError):
        testee.prepare_output_file(blocker / 'new.txt', create=create)
    assert blocker.read_bytes() == b'keep'
