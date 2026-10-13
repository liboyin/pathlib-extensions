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


def test_truncate_filename_keeps_name_at_exact_limit():
    """A name of exactly max_length bytes is returned unchanged."""
    path = Path("d") / ("a" * 251 + ".txt")
    assert truncate_filename(path) == path


def test_truncate_filename_treats_dotted_title_text_as_stem():
    """A dot inside a long title does not make the rest of the title a suffix."""
    path = Path("d") / ("Mr. Smith " + "x" * 300 + ".mp4")
    result = truncate_filename(path, max_length=220)
    assert result.parent == Path("d")
    assert result.name == ("Mr. Smith " + "x" * 300)[:216] + ".mp4"
    assert len(result.name.encode('utf-8')) == 220


def test_truncate_filename_keeps_only_trailing_extension_like_suffixes():
    """Suffix text with spaces ends the kept run, leaving only the final extension."""
    result = truncate_filename(Path("Version 2.0 Notes " + "n" * 300 + ".pdf"), max_length=100)
    assert result.suffix == ".pdf"
    assert result.name.startswith("Version 2.0 Notes ")
    assert len(result.name.encode('utf-8')) == 100


def test_truncate_filename_without_extension_like_suffix_truncates_whole_name():
    """A long dotted name without an extension-like suffix is truncated as stem text."""
    name = "Mr. Smith " + "x" * 300
    result = truncate_filename(Path("d") / name, max_length=220)
    assert result == Path("d") / name[:220]


def test_truncate_filename_without_suffix_returns_truncated_name_not_parent():
    """A long name without any suffix keeps its parent and a truncated name."""
    result = truncate_filename(Path("d") / ("a" * 300))
    assert result == Path("d") / ("a" * 255)


def test_truncate_filename_never_splits_multibyte_characters():
    """Truncation cuts at a UTF-8 character boundary below the byte limit."""
    result = truncate_filename(Path("v1.2 " + "é" * 200 + ".srt"), max_length=220)
    assert result.suffix == ".srt"
    assert result.name == "v1.2 " + "é" * 105 + ".srt"
    assert len(result.name.encode('utf-8')) == 219


def test_truncate_filename_rejects_suffix_leaving_no_whole_stem_character():
    """A kept suffix that leaves no room for one whole stem character raises ValueError."""
    with pytest.raises(ValueError, match="Not possible to truncate"):
        truncate_filename(Path("🌟🌟.txt"), max_length=7)


def test_truncate_filename_rejects_suffix_longer_than_limit_despite_long_stem():
    """A suffix over the limit raises instead of returning an over-limit name."""
    with pytest.raises(ValueError, match="Not possible to truncate"):
        truncate_filename(Path("x" * 300 + "." + "a" * 300))


@pytest.mark.parametrize('text', ['bar-baz', 'bar_baz', 'é'])
def test_truncate_filename_treats_non_alphanumeric_dotted_text_as_stem(text):
    """Dotted text with hyphens, underscores or non-ASCII letters is not an extension."""
    name = "Title." + text * 300
    result = truncate_filename(Path("d") / (name + ".mp4"), max_length=220)
    assert result.parent == Path("d")
    assert result.suffix == ".mp4"
    assert result.name.startswith("Title.")
    assert 219 <= len(result.name.encode('utf-8')) <= 220


def test_truncate_filename_keeps_uppercase_extension():
    """ASCII extensions are matched case-insensitively and kept as written."""
    result = truncate_filename(Path("d") / ("a" * 300 + ".TXT"))
    assert result == Path("d") / ("a" * 251 + ".TXT")


@pytest.mark.parametrize(('name', 'max_length'), [("." + "x" * 300, 1), (".." + "x" * 300, 2), (".🌟🌟", 3)])
def test_truncate_filename_rejects_dot_or_dot_dot_result(name, max_length):
    """A truncated name of '.' or '..' raises instead of returning a directory path."""
    with pytest.raises(ValueError, match="Not possible to truncate"):
        truncate_filename(Path("d") / name, max_length=max_length)
