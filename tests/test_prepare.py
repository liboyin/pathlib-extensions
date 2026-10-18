from pathlib import Path

import pytest

import pathlib_extensions.prepare as testee


def test_prepare_input_dir_valid():
    d = Path.cwd()
    assert testee.prepare_input_dir(d) is d


def test_prepare_input_dir_invalid():
    with pytest.raises(NotADirectoryError):
        testee.prepare_input_dir(__file__)


def test_prepare_input_dir_not_found():
    with pytest.raises(FileNotFoundError):
        testee.prepare_input_dir('path/that/does/not/exist')


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


def test_prepare_input_file_with_suffix():
    assert testee.prepare_input_file(__file__, with_suffix='.py') == Path(__file__)


def test_prepare_input_file_invalid_argument():
    with pytest.raises(ValueError):
        testee.prepare_input_file(__file__, check_suffix='.txt', with_suffix='.txt')


def test_prepare_output_dir_valid():
    d = Path.cwd()
    assert testee.prepare_output_dir(d) is d


def test_prepare_output_dir_invalid():
    with pytest.raises(NotADirectoryError):
        testee.prepare_output_dir(__file__)


def test_prepare_output_dir_create(tmp_path):
    d = tmp_path / "sub2"
    assert testee.prepare_output_dir(d, create=True) is d


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


def test_prepare_output_file_with_suffix(tmp_path):
    p = tmp_path / "testfile"
    p.touch()
    assert testee.prepare_output_file(p, with_suffix='.txt') == tmp_path / "testfile.txt"


def test_prepare_output_file_invalid_argument(tmp_path):
    p = tmp_path / "testfile"
    p.touch()
    with pytest.raises(ValueError):
        testee.prepare_output_file(p, check_suffix='.txt', with_suffix='.txt')
