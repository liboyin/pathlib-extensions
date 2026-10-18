from pathlib import Path

import pytest

from pathlib_extensions.filesystem import build_filename, replace_os_reserved_chars, truncate_filename


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


@pytest.mark.parametrize('invalid_char', ['?', ':', '<', '>', '|', '/', '\\', '"', '*'])
def test_replace_os_reserved_chars_with_invalid_replacement(invalid_char):
    with pytest.raises(ValueError, match='contains an OS-reserved character'):
        replace_os_reserved_chars("filename", replacement=invalid_char)


def test_replace_os_reserved_chars_with_multi_char_invalid_replacement():
    with pytest.raises(ValueError, match='contains an OS-reserved character'):
        replace_os_reserved_chars("filename", replacement='a/b')


@pytest.mark.parametrize('replacement, expected', [('', 'ab'), ('-', 'a-b'), ('__', 'a__b')])
def test_replace_os_reserved_chars_with_valid_replacement(replacement, expected):
    assert replace_os_reserved_chars('a:b', replacement=replacement) == expected


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


def test_build_filename_replaces_reserved_characters_without_truncating(capsys):
    """A short name keeps all text with reserved characters replaced, and prints nothing."""
    assert build_filename('a/b: c?', '.mp4', tag=' [id1]') == 'a_b_ c_ [id1].mp4'
    assert capsys.readouterr().out == ''


def test_build_filename_uses_custom_replacement_for_reserved_characters():
    """A non-default replacement is used for every reserved character."""
    assert build_filename('a/b:c?', '.txt', replacement='-') == 'a-b-c-.txt'


def test_build_filename_keeps_name_at_exact_limit():
    """A name of exactly max_length bytes is kept whole."""
    assert build_filename('a' * 10, '.mp4', tag=' [x]', max_length=18) == 'a' * 10 + ' [x].mp4'


def test_build_filename_truncates_only_text_and_keeps_tag_and_suffix(capsys):
    """A long title is cut so the tag and suffix survive within the byte limit."""
    title = 'Mr. Smith Goes to Washington ' + 'x' * 300
    name = build_filename(title, '.mp4', tag=' [n9xhJrPXop4]', max_length=220)
    assert name == title[:220 - 18] + ' [n9xhJrPXop4].mp4'
    assert len(name.encode('utf-8')) == 220
    assert 'Truncated filename:' in capsys.readouterr().out


def test_build_filename_infers_no_suffix_from_dots_in_text():
    """An extension-like ending in the text is truncated as text; only the given tag and suffix are kept."""
    assert build_filename('x' * 30 + '.tar.gz', max_length=10) == 'x' * 10
    assert build_filename('x' * 30 + '.tar.gz', '.mp4', tag=' [id]', max_length=20) == 'x' * 11 + ' [id].mp4'


@pytest.mark.parametrize(('suffix', 'tag', 'expected'), [
    ('.txt', ' [🌟]', 'aaa [🌟].txt'),
    ('.é', '', 'aaaaaaaaaaa.é'),
    ('.é', ' [🌟]', 'aaaa [🌟].é'),
])
def test_build_filename_budgets_kept_components_in_utf8_bytes(suffix, tag, expected):
    """Multi-byte tags and suffixes are kept verbatim and counted in bytes, not characters."""
    name = build_filename('a' * 20, suffix, tag=tag, max_length=14)
    assert name == expected
    assert len(name.encode('utf-8')) == 14


def test_build_filename_never_splits_multibyte_characters():
    """Truncation cuts the text at a UTF-8 character boundary below the limit."""
    name = build_filename('é' * 100, '.srt', max_length=11)
    assert name == 'ééé.srt'
    assert len(name.encode('utf-8')) == 10


@pytest.mark.parametrize(('text', 'suffix', 'tag', 'max_length'), [
    ('', '.mp4', ' [id]', 255),
    ('title', '.mp4', ' [id]', 9),
    ('🌟title', '.mp4', '', 7),
    ('x' * 300, '.' + 'a' * 300, '', 255),
    ('.', '', '', 255),
    ('..xxx', '', '', 2),
])
def test_build_filename_rejects_names_without_text_or_naming_a_directory(text, suffix, tag, max_length):
    """No room for text, empty text, or a '.'/'..' result raises ValueError."""
    with pytest.raises(ValueError, match="Not possible to build a filename"):
        build_filename(text, suffix, tag=tag, max_length=max_length)
