import os
from pathlib import Path

import pytest

import pathlib_extensions.naming as testee


def test_remove_os_reserved_chars():
    assert testee.replace_os_reserved_chars("file?name") == "file_name"
    assert testee.replace_os_reserved_chars("file*name") == "file_name"
    assert testee.replace_os_reserved_chars("file:name") == "file_name"
    assert testee.replace_os_reserved_chars("file<name") == "file_name"
    assert testee.replace_os_reserved_chars("file>name") == "file_name"
    assert testee.replace_os_reserved_chars("file|name") == "file_name"
    assert testee.replace_os_reserved_chars("file/name") == "file_name"
    assert testee.replace_os_reserved_chars("file\\name") == "file_name"
    assert testee.replace_os_reserved_chars('file"name') == "file_name"


@pytest.mark.parametrize('invalid_char', ['?', ':', '<', '>', '|', '/', '\\', '"', '*'])
def test_replace_os_reserved_chars_with_invalid_replacement(invalid_char):
    with pytest.raises(ValueError, match='contains an OS-reserved character'):
        testee.replace_os_reserved_chars("filename", replacement=invalid_char)


def test_replace_os_reserved_chars_with_multi_char_invalid_replacement():
    with pytest.raises(ValueError, match='contains an OS-reserved character'):
        testee.replace_os_reserved_chars("filename", replacement='a/b')


@pytest.mark.parametrize('replacement, expected', [('', 'ab'), ('-', 'a-b'), ('__', 'a__b')])
def test_replace_os_reserved_chars_with_valid_replacement(replacement, expected):
    assert testee.replace_os_reserved_chars('a:b', replacement=replacement) == expected


@pytest.mark.parametrize(('name', 'expected'), [
    ('archive.tar.gz', '.tar.gz'),
    ('movie.MP4', '.MP4'),
    ('Mr. Smith.mp4', '.mp4'),
    ('Version 2.0 Notes.pdf', '.pdf'),
    ('notes.v2.txt', '.v2.txt'),
    ('backup.tar.old-copy.gz', '.gz'),
    ('Title.bar-baz', ''),
    ('Title.é', ''),
    ('README', ''),
    ('.bashrc', ''),
    ('.bashrc.bak', '.bak'),
    ('a..gz', '.gz'),
    ('', ''),
])
def test_get_extension_suffix_returns_trailing_extension_like_run(name, expected):
    """Only the trailing run of dot-plus-ASCII-alphanumeric suffixes is returned, as written."""
    assert testee.get_extension_suffix(name) == expected


@pytest.mark.parametrize('name', ['name.', 'archive.tar.', 'archive.tar.gz.', 'name..', '.bashrc.', 'Mr. Smith.mp4.'])
def test_get_extension_suffix_returns_empty_for_trailing_dot(name):
    """A name ending in a dot has no extension, although Path.suffixes differs across Python versions here."""
    assert testee.get_extension_suffix(name) == ''


@pytest.mark.parametrize('path', ['dir.d/file', Path('dir.d') / 'file', Path('dir.d/..')])
def test_get_extension_suffix_ignores_directory_components(path):
    """Dots in parent directories never contribute a suffix, for str and Path input."""
    assert testee.get_extension_suffix(path) == ''


def test_get_extension_suffix_inspects_final_component_of_path():
    """A str or Path with directories yields the final component's suffix run."""
    assert testee.get_extension_suffix('a.b/c.tar.gz') == '.tar.gz'
    assert testee.get_extension_suffix(Path('a.b') / 'c.tar.gz') == '.tar.gz'


def test_get_extension_suffix_is_exported_from_package():
    """The function is part of the package's public API."""
    import pathlib_extensions
    assert pathlib_extensions.get_extension_suffix is testee.get_extension_suffix
    assert 'get_extension_suffix' in testee.__all__


def test_truncate_filename_no_change():
    path = Path("short_filename.txt")
    result = testee.truncate_filename(path)
    assert result == path


def test_truncate_filename_with_extensions():
    suffixes = ".tar.gz"
    result = testee.truncate_filename("a" * 260 + suffixes)
    assert result == Path("a" * (255 - len(suffixes)) + suffixes), len(str(result))


def test_truncate_filename_extension_too_long():
    path = Path("file." + "a" * 254)
    with pytest.raises(ValueError, match="Not possible to truncate"):
        testee.truncate_filename(path)


def test_truncate_filename_with_long_directory():
    dir_path = Path("/" + "a" * 200) / ("b" * 200)
    result = testee.truncate_filename(dir_path / ("c" * 260 + ".txt"))
    assert result == dir_path / ("c" * 251 + ".txt"), len(str(result))


def test_truncate_filename_with_unicode():
    result = testee.truncate_filename(Path("🌟" * 100 + ".txt"))
    assert result.suffixes == [".txt"]
    result_bytes_length = len(str(result).encode('utf-8'))
    assert 250 <= result_bytes_length <= 255, result_bytes_length


def test_truncate_filename_keeps_name_at_exact_limit():
    """A name of exactly max_length bytes is returned unchanged."""
    path = Path("d") / ("a" * 251 + ".txt")
    assert testee.truncate_filename(path) == path


def test_truncate_filename_treats_dotted_title_text_as_stem():
    """A dot inside a long title does not make the rest of the title a suffix."""
    path = Path("d") / ("Mr. Smith " + "x" * 300 + ".mp4")
    result = testee.truncate_filename(path, max_length=220)
    assert result.parent == Path("d")
    assert result.name == ("Mr. Smith " + "x" * 300)[:216] + ".mp4"
    assert len(result.name.encode('utf-8')) == 220


def test_truncate_filename_keeps_only_trailing_extension_like_suffixes():
    """Suffix text with spaces ends the kept run, leaving only the final extension."""
    result = testee.truncate_filename(Path("Version 2.0 Notes " + "n" * 300 + ".pdf"), max_length=100)
    assert result.suffix == ".pdf"
    assert result.name.startswith("Version 2.0 Notes ")
    assert len(result.name.encode('utf-8')) == 100


def test_truncate_filename_without_extension_like_suffix_truncates_whole_name():
    """A long dotted name without an extension-like suffix is truncated as stem text."""
    name = "Mr. Smith " + "x" * 300
    result = testee.truncate_filename(Path("d") / name, max_length=220)
    assert result == Path("d") / name[:220]


def test_truncate_filename_without_suffix_returns_truncated_name_not_parent():
    """A long name without any suffix keeps its parent and a truncated name."""
    result = testee.truncate_filename(Path("d") / ("a" * 300))
    assert result == Path("d") / ("a" * 255)


def test_truncate_filename_never_splits_multibyte_characters():
    """Truncation cuts at a UTF-8 character boundary below the byte limit."""
    result = testee.truncate_filename(Path("v1.2 " + "é" * 200 + ".srt"), max_length=220)
    assert result.suffix == ".srt"
    assert result.name == "v1.2 " + "é" * 105 + ".srt"
    assert len(result.name.encode('utf-8')) == 219


def test_truncate_filename_rejects_suffix_leaving_no_whole_stem_character():
    """A kept suffix that leaves no room for one whole stem character raises ValueError."""
    with pytest.raises(ValueError, match="Not possible to truncate"):
        testee.truncate_filename(Path("🌟🌟.txt"), max_length=7)


def test_truncate_filename_rejects_suffix_longer_than_limit_despite_long_stem():
    """A suffix over the limit raises instead of returning an over-limit name."""
    with pytest.raises(ValueError, match="Not possible to truncate"):
        testee.truncate_filename(Path("x" * 300 + "." + "a" * 300))


@pytest.mark.parametrize('text', ['bar-baz', 'bar_baz', 'é'])
def test_truncate_filename_treats_non_alphanumeric_dotted_text_as_stem(text):
    """Dotted text with hyphens, underscores or non-ASCII letters is not an extension."""
    name = "Title." + text * 300
    result = testee.truncate_filename(Path("d") / (name + ".mp4"), max_length=220)
    assert result.parent == Path("d")
    assert result.suffix == ".mp4"
    assert result.name.startswith("Title.")
    assert 219 <= len(result.name.encode('utf-8')) <= 220


def test_truncate_filename_keeps_no_suffix_for_trailing_dot_name():
    """A long name ending in a dot is truncated as stem text without keeping an extension."""
    result = testee.truncate_filename(Path("d") / ("a" * 300 + ".txt."), max_length=10)
    assert result == Path("d") / ("a" * 10)


def test_truncate_filename_keeps_uppercase_extension():
    """ASCII extensions are matched case-insensitively and kept as written."""
    result = testee.truncate_filename(Path("d") / ("a" * 300 + ".TXT"))
    assert result == Path("d") / ("a" * 251 + ".TXT")


@pytest.mark.parametrize(('name', 'max_length'), [("." + "x" * 300, 1), (".." + "x" * 300, 2), (".🌟🌟", 3)])
def test_truncate_filename_rejects_dot_or_dot_dot_result(name, max_length):
    """A truncated name of '.' or '..' raises instead of returning a directory path."""
    with pytest.raises(ValueError, match="Not possible to truncate"):
        testee.truncate_filename(Path("d") / name, max_length=max_length)


@pytest.mark.parametrize(('name', 'number', 'expected'), [
    ('hello.mp4', 1, 'hello.1.mp4'),
    ('hello.mp4', 12, 'hello.12.mp4'),
    ('video.en.srt', 1, 'video.1.en.srt'),
    ('archive.tar.gz', 2, 'archive.2.tar.gz'),
    ('notes', 1, 'notes.1'),
    ('.bashrc', 1, '.bashrc.1'),
    ('My talk. Part 2.mp4', 1, 'My talk. Part 2.1.mp4'),
])
def test_get_numbered_path_inserts_number_before_extension_like_suffixes(name, number, expected, capsys):
    """The number goes before the whole trailing run of extension-like suffixes, silently."""
    assert testee.get_numbered_path(Path('d') / name, number) == Path('d') / expected
    assert capsys.readouterr().out == ''


def test_get_numbered_path_accepts_str_and_keeps_directory_components():
    """A str path is accepted and dotted directory components are left alone."""
    assert testee.get_numbered_path('dir.d/sub.v2/hello.mp4', 1) == Path('dir.d/sub.v2/hello.1.mp4')


def test_get_numbered_path_shortens_stem_of_a_maximal_name(capsys):
    """A numbered name over the limit loses trailing stem text at a character boundary but keeps the number."""
    path = Path('d') / ('é' * 125 + 'x.mp4')
    assert len(path.name.encode('utf-8')) == 255
    result = testee.get_numbered_path(path, 1)
    assert result == Path('d') / ('é' * 124 + '.1.mp4')
    assert len(result.name.encode('utf-8')) == 254
    assert 'Truncated path' in capsys.readouterr().out


def test_get_numbered_path_honours_custom_max_length():
    """max_length bounds the numbered name in bytes."""
    assert testee.get_numbered_path(Path('d/abcdef.mp4'), 1, max_length=10) == Path('d/abcd.1.mp4')


def test_get_numbered_path_rejects_suffix_leaving_no_stem():
    """A suffix run that leaves no room for a stem character raises ValueError."""
    with pytest.raises(ValueError):
        testee.get_numbered_path(Path('d') / ('a' + '.x' * 127), 1)


@pytest.mark.parametrize('number', [0, -1])
def test_get_numbered_path_rejects_non_positive_number(number):
    """Zero and negative numbers raise ValueError."""
    with pytest.raises(ValueError, match='positive'):
        testee.get_numbered_path(Path('d/hello.mp4'), number)


def test_get_numbered_path_is_exported_from_package():
    """The function is part of the package's public API."""
    import pathlib_extensions
    assert pathlib_extensions.get_numbered_path is testee.get_numbered_path
    assert 'get_numbered_path' in testee.__all__


def test_get_first_available_path_returns_free_path_itself(tmp_path):
    """A path with nothing at it is returned unnumbered, and nothing is created."""
    assert testee.get_first_available_path(tmp_path / 'hello.mp4') == tmp_path / 'hello.mp4'
    assert list(tmp_path.iterdir()) == []


def test_get_first_available_path_numbers_taken_path_from_one(tmp_path):
    """A taken path yields the first numbered variant, leaving the existing file alone."""
    (tmp_path / 'video.en.srt').write_text('old')
    assert testee.get_first_available_path(tmp_path / 'video.en.srt') == tmp_path / 'video.1.en.srt'
    assert [p.name for p in tmp_path.iterdir()] == ['video.en.srt']


def test_get_first_available_path_reuses_lowest_free_number(tmp_path):
    """A gap in the numbering is filled before higher numbers."""
    for name in ['hello.mp4', 'hello.2.mp4', 'hello.3.mp4']:
        (tmp_path / name).write_text('x')
    assert testee.get_first_available_path(tmp_path / 'hello.mp4') == tmp_path / 'hello.1.mp4'


def test_get_first_available_path_counts_directories_and_dangling_symlinks_as_taken(tmp_path):
    """A file, a directory and a dangling symlink each take a name."""
    (tmp_path / 'hello.mp4').write_text('x')
    (tmp_path / 'hello.1.mp4').mkdir()
    (tmp_path / 'hello.2.mp4').symlink_to('missing.mp4')
    assert testee.get_first_available_path(str(tmp_path / 'hello.mp4')) == tmp_path / 'hello.3.mp4'


def test_get_first_available_path_fits_numbered_names_in_max_length(tmp_path):
    """Numbered candidates are fitted to max_length bytes."""
    (tmp_path / 'abcdef.mp4').write_text('x')
    assert testee.get_first_available_path(tmp_path / 'abcdef.mp4', max_length=10) == tmp_path / 'abcd.1.mp4'


@pytest.mark.skipif(os.name != 'posix' or os.geteuid() == 0, reason='POSIX permission bits are only enforced for non-root users')
def test_get_first_available_path_raises_when_names_cannot_be_checked(tmp_path):
    """An unsearchable directory raises PermissionError instead of reporting a name as free."""
    directory = tmp_path / 'locked'
    directory.mkdir()
    directory.chmod(0o600)
    try:
        with pytest.raises(PermissionError):
            testee.get_first_available_path(directory / 'hello.mp4')
    finally:
        directory.chmod(0o700)


def test_get_first_available_path_defaults_to_ten_attempts(tmp_path):
    """By default ten names are checked: the path itself, then numbers 1 to 9."""
    for name in ['hello.mp4'] + [f'hello.{n}.mp4' for n in range(1, 9)]:
        (tmp_path / name).write_text('x')
    assert testee.get_first_available_path(tmp_path / 'hello.mp4') == tmp_path / 'hello.9.mp4'
    (tmp_path / 'hello.9.mp4').write_text('x')
    with pytest.raises(FileExistsError, match='10 attempts'):
        testee.get_first_available_path(tmp_path / 'hello.mp4')


@pytest.mark.parametrize(('taken', 'max_attempts', 'expected'), [(0, 1, 'hello.mp4'), (2, 3, 'hello.2.mp4'), (1, 1, None), (3, 3, None)])
def test_get_first_available_path_checks_max_attempts_names(taken, max_attempts, expected, tmp_path):
    """Exactly max_attempts names are checked, the path included; exhausting them raises FileExistsError."""
    names = ['hello.mp4'] + [f'hello.{n}.mp4' for n in range(1, 10)]
    for name in names[:taken]:
        (tmp_path / name).write_text('x')
    if expected is None:
        with pytest.raises(FileExistsError):
            testee.get_first_available_path(tmp_path / 'hello.mp4', max_attempts=max_attempts)
    else:
        assert testee.get_first_available_path(tmp_path / 'hello.mp4', max_attempts=max_attempts) == tmp_path / expected
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(names[:taken])


@pytest.mark.parametrize('max_attempts', [0, -1])
def test_get_first_available_path_rejects_max_attempts_below_one(max_attempts, tmp_path):
    """max_attempts below 1 raises ValueError."""
    with pytest.raises(ValueError, match='max_attempts'):
        testee.get_first_available_path(tmp_path / 'hello.mp4', max_attempts=max_attempts)


def test_get_first_available_path_is_exported_from_package():
    """The function is part of the package's public API."""
    import pathlib_extensions
    assert pathlib_extensions.get_first_available_path is testee.get_first_available_path
    assert 'get_first_available_path' in testee.__all__


def test_build_filename_replaces_reserved_characters_without_truncating(capsys):
    """A short name keeps all text with reserved characters replaced, and prints nothing."""
    assert testee.build_filename('a/b: c?', '.mp4', tag=' [id1]') == 'a_b_ c_ [id1].mp4'
    assert capsys.readouterr().out == ''


def test_build_filename_uses_custom_replacement_for_reserved_characters():
    """A non-default replacement is used for every reserved character."""
    assert testee.build_filename('a/b:c?', '.txt', replacement='-') == 'a-b-c-.txt'


def test_build_filename_keeps_name_at_exact_limit():
    """A name of exactly max_length bytes is kept whole."""
    assert testee.build_filename('a' * 10, '.mp4', tag=' [x]', max_length=18) == 'a' * 10 + ' [x].mp4'


def test_build_filename_truncates_only_text_and_keeps_tag_and_suffix(capsys):
    """A long title is cut so the tag and suffix survive within the byte limit."""
    title = 'Mr. Smith Goes to Washington ' + 'x' * 300
    name = testee.build_filename(title, '.mp4', tag=' [n9xhJrPXop4]', max_length=220)
    assert name == title[:220 - 18] + ' [n9xhJrPXop4].mp4'
    assert len(name.encode('utf-8')) == 220
    assert 'Truncated filename:' in capsys.readouterr().out


def test_build_filename_infers_no_suffix_from_dots_in_text():
    """An extension-like ending in the text is truncated as text; only the given tag and suffix are kept."""
    assert testee.build_filename('x' * 30 + '.tar.gz', max_length=10) == 'x' * 10
    assert testee.build_filename('x' * 30 + '.tar.gz', '.mp4', tag=' [id]', max_length=20) == 'x' * 11 + ' [id].mp4'


@pytest.mark.parametrize(('suffix', 'tag', 'expected'), [
    ('.txt', ' [🌟]', 'aaa [🌟].txt'),
    ('.é', '', 'aaaaaaaaaaa.é'),
    ('.é', ' [🌟]', 'aaaa [🌟].é'),
])
def test_build_filename_budgets_kept_components_in_utf8_bytes(suffix, tag, expected):
    """Multi-byte tags and suffixes are kept verbatim and counted in bytes, not characters."""
    name = testee.build_filename('a' * 20, suffix, tag=tag, max_length=14)
    assert name == expected
    assert len(name.encode('utf-8')) == 14


def test_build_filename_never_splits_multibyte_characters():
    """Truncation cuts the text at a UTF-8 character boundary below the limit."""
    name = testee.build_filename('é' * 100, '.srt', max_length=11)
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
        testee.build_filename(text, suffix, tag=tag, max_length=max_length)
