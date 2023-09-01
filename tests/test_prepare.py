from pathlib import Path

import pytest

from pathlib_extensions.prepare import input_dir, input_file, output_dir, output_file, NotAFileError, SuffixError


def test_input_dir_valid():
    assert input_dir(Path.cwd()) == Path.cwd()


def test_input_dir_invalid():
    with pytest.raises(NotADirectoryError):
        input_dir(__file__)


def test_input_dir_not_found():
    with pytest.raises(FileNotFoundError):
        input_dir('path/that/does/not/exist')


def test_input_file_valid():
    assert input_file(__file__) == Path(__file__)


def test_input_file_invalid():
    with pytest.raises(NotAFileError):
        input_file(Path.cwd())


def test_input_file_not_found():
    with pytest.raises(FileNotFoundError):
        input_file('file/that/does/not/exist')


def test_input_file_check_suffix():
    with pytest.raises(SuffixError):
        input_file(__file__, check_suffix='.txt')


def test_input_file_with_suffix():
    assert input_file(__file__, with_suffix='.py') == Path(__file__)


def test_input_file_invalid_argument():
    with pytest.raises(ValueError):
        input_file(__file__, check_suffix='.txt', with_suffix='.txt')


def test_output_dir_valid(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    assert output_dir(d) == d


def test_output_dir_invalid():
    with pytest.raises(NotADirectoryError):
        output_dir(__file__)


def test_output_dir_create(tmp_path):
    d = tmp_path / "sub2"
    assert output_dir(d, create=True) == d


def test_output_file_valid(tmp_path):
    p = tmp_path / "testfile.txt"
    p.write_text("content")
    assert output_file(p) == p


def test_output_file_invalid(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    with pytest.raises(NotAFileError):
        output_file(d)


def test_output_file_check_suffix(tmp_path):
    p = tmp_path / "testfile.txt"
    p.write_text("content")
    with pytest.raises(SuffixError):
        output_file(p, check_suffix='.py')


def test_output_file_with_suffix(tmp_path):
    p = tmp_path / "testfile"
    p.write_text("content")
    assert output_file(p, with_suffix='.txt') == tmp_path / "testfile.txt"


def test_output_file_invalid_argument(tmp_path):
    p = tmp_path / "testfile"
    p.write_text("content")
    with pytest.raises(ValueError):
        output_file(p, check_suffix='.txt', with_suffix='.txt')
