from pathlib import Path

import pytest

from pathlib_extensions.filesystem import replace_os_reserved_chars, truncate_filename


def test_remove_os_reserved_chars():
    assert replace_os_reserved_chars("file?name") == "file_name"
    assert replace_os_reserved_chars("file*name") == "file_name"
    assert replace_os_reserved_chars("file:name") == "file_name"
    assert replace_os_reserved_chars("file<name") == "file_name"
    assert replace_os_reserved_chars("file>name") == "file_name"
    assert replace_os_reserved_chars("file|name") == "file_name"
    assert replace_os_reserved_chars("file/name") == "file_name"
    assert replace_os_reserved_chars("file\\name") == "file_name"
    assert replace_os_reserved_chars('file"name') == "file_name"


def test_truncate_filename_no_change():
    path = Path("short_filename.txt")
    result = truncate_filename(path)
    assert result == path


def test_truncate_filename_with_extensions():
    suffixes = ".tar.gz"
    result = truncate_filename("a" * 260 + suffixes)
    assert result == Path("a" * (255 - len(suffixes)) + suffixes), len(str(result))


def test_truncate_filename_extension_too_long():
    path = Path("file." + "a" * 254)
    with pytest.raises(ValueError, match="Not possible to truncate"):
        truncate_filename(path)


def test_truncate_filename_with_long_directory():
    dir_path = Path("/" + "a" * 200) / ("b" * 200)
    result = truncate_filename(dir_path / ("c" * 260 + ".txt"))
    assert result == dir_path / ("c" * 251 + ".txt"), len(str(result))


def test_truncate_filename_with_unicode():
    result = truncate_filename(Path("🌟" * 100 + ".txt"))
    assert result.suffixes == [".txt"]
    result_bytes_length = len(str(result).encode('utf-8'))
    assert 250 <= result_bytes_length <= 255, result_bytes_length
