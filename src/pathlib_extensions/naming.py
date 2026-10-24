import logging
import re
from pathlib import Path

__all__ = ['build_filename', 'get_extension_suffix', 'get_first_available_path', 'get_numbered_path', 'replace_os_reserved_chars', 'truncate_filename']

logger = logging.getLogger(__name__)


_RESERVED_CHARS = re.compile(r'[\\/*?:"<>|]')


def replace_os_reserved_chars(text: str, replacement: str = '_') -> str:
    """
    Replace OS-reserved characters in a string with a specified replacement.

    Should work on Windows, Linux, and macOS.

    Args:
        text (str): The input text.
        replacement (str, optional): The replacement string, which may be empty. Defaults to '_'.

    Returns:
        str: The modified text with reserved characters replaced by `replacement`.

    Raises:
        ValueError: If `replacement` itself contains an OS-reserved character.
    """
    if _RESERVED_CHARS.search(replacement):
        raise ValueError(f'Replacement {replacement!r} contains an OS-reserved character.')
    # A callable keeps `replacement` literal instead of being parsed as a regex template.
    return _RESERVED_CHARS.sub(lambda _: replacement, text)


_EXTENSION_SUFFIX = re.compile(r'\.[A-Za-z0-9]+')


def get_extension_suffix(path: str | Path) -> str:
    """
    Return the trailing run of extension-like suffixes of the final path component.

    A suffix is extension-like when it is a dot followed only by ASCII letters or digits,
    so `.tar.gz` is kept whole while text after a dot inside a title, such as `. Smith`,
    is not a suffix. The run stops at the first suffix, scanning from the end, that is
    not extension-like. A leading dot, as in `.bashrc`, does not start a suffix, and
    directory components are ignored.

    Args:
        path (str | Path): The path whose final component is inspected.

    Returns:
        str: The suffix run as written, such as '.tar.gz', or '' when the name has none.
    """
    suffix = ''
    for part in reversed(Path(path).suffixes):
        if not _EXTENSION_SUFFIX.fullmatch(part):
            break
        suffix = part + suffix
    return suffix


def _fit_stem(stem: str, kept: str, max_length: int) -> str | None:
    """
    Join `stem` and `kept`, truncating only `stem` so the name fits in `max_length` bytes.

    The stem is cut at a UTF-8 character boundary; `kept` is always kept whole.

    Args:
        stem (str): Text that may be truncated.
        kept (str): Text appended after the stem and never truncated.
        max_length (int): The maximum number of bytes.

    Returns:
        str | None: The joined name, or None if no whole stem character fits or the name
            would be '.' or '..'.
    """
    stem_max_bytes_length = max_length - len(kept.encode('utf-8'))
    # Cutting the encoded stem can split a multi-byte character.
    # Decoding with errors='ignore' drops only that incomplete trailing character.
    stem = stem.encode('utf-8')[:max(stem_max_bytes_length, 0)].decode('utf-8', errors='ignore')
    name = stem + kept
    # '.' and '..' would turn the result into a directory path.
    if not stem or name in ('.', '..'):
        return None
    return name


def truncate_filename(path: str | Path, max_length: int = 255) -> Path:
    """
    Truncate the filename such that it fits in `max_length` bytes.

    The trailing run of extension-like suffixes (a dot followed by ASCII letters or digits,
    such as `.mp4` or `.tar.gz`) is kept; the rest of the name is truncated as stem text at
    a UTF-8 character boundary. Directory components are never changed.

    Args:
        path (str | Path): The path to process.
        max_length (int, optional): The maximum number of bytes. Defaults to 255 for ext4.

    Returns:
        Path: The processed path.

    Raises:
        ValueError: If the kept suffix leaves no room for at least one stem character, or
            the truncated name would be '.' or '..'.
    """
    if isinstance(path, str):
        path = Path(path)
    filename = path.name
    if len(filename.encode('utf-8')) <= max_length:
        return path
    suffix = get_extension_suffix(filename)
    name = _fit_stem(filename[:len(filename) - len(suffix)], suffix, max_length)
    if name is None:
        raise ValueError(f'Not possible to truncate filename to fit in {max_length} bytes: {path}')
    result = path.parent / name
    logger.info('Truncated path: %s -> %s', path, result)
    return result


def get_numbered_path(path: str | Path, number: int, max_length: int = 255) -> Path:
    """
    Number a path by inserting `.{number}` before its trailing run of extension-like suffixes.

    For example `hello.mp4` becomes `hello.1.mp4`, `video.en.srt` becomes `video.1.en.srt`
    and `notes` becomes `notes.1`. The result is fitted in `max_length` bytes by
    `truncate_filename`, which shortens only the stem and keeps the number, because `.1` is
    itself extension-like. Directory components are never changed and the filesystem is not
    consulted, so the result may already exist.

    Args:
        path (str | Path): The path to number.
        number (int): A positive number to insert.
        max_length (int, optional): The maximum number of bytes. Defaults to 255 for ext4.

    Returns:
        Path: The numbered path.

    Raises:
        ValueError: If `number` is not positive, or no stem character fits beside the
            numbered suffix.
    """
    if number < 1:
        raise ValueError(f'Number must be positive: {number}')
    path = Path(path)
    name = path.name
    suffix = get_extension_suffix(name)
    return truncate_filename(path.with_name(f'{name[:len(name) - len(suffix)]}.{number}{suffix}'), max_length)


def get_first_available_path(path: str | Path, max_length: int = 255, max_attempts: int = 10) -> Path:
    """
    Return `path` if nothing exists there, otherwise its lowest-numbered free variant.

    Numbered variants come from `get_numbered_path`, tried from 1 upwards after `path`, so a
    gap such as a free `hello.1.mp4` beside a taken `hello.2.mp4` is reused. Any entry counts as taken,
    including a directory or a dangling symlink. The answer is only a snapshot: the name may
    be taken before the caller writes to it, so a writer that must not overwrite should still
    create the file exclusively.

    Args:
        path (str | Path): The preferred path.
        max_length (int, optional): The maximum number of bytes for a numbered name.
            Defaults to 255 for ext4. `path` itself is returned unchanged when free.
        max_attempts (int, optional): How many names to check in total, `path` included, so
            numbers 1 to `max_attempts - 1` are tried; 1 checks only `path`. Defaults to 10.

    Returns:
        Path: The first path, in that order, at which nothing exists.

    Raises:
        ValueError: If `max_attempts` is less than 1, or no stem character fits beside a
            numbered suffix.
        FileExistsError: If all `max_attempts` names are taken.
        OSError: If a candidate cannot be checked, for example because its directory is
            not searchable; such a name is not reported as available.
    """
    if max_attempts < 1:
        raise ValueError(f'max_attempts must be at least 1: {max_attempts}')
    path = Path(path)
    for number in range(max_attempts):
        candidate = get_numbered_path(path, number, max_length) if number else path
        try:
            candidate.lstat()
        except FileNotFoundError:
            return candidate
    raise FileExistsError(f'No available path within {max_attempts} attempts: {path}')


def build_filename(text: str, suffix: str = '', *, tag: str = '', max_length: int = 255, replacement: str = '_') -> str:
    """
    Build a filename from free text, such as a title, that fits in `max_length` bytes.

    OS-reserved characters in `text` are replaced with `replacement`. If the name is too long,
    only the text is truncated, at a UTF-8 character boundary; `tag` and `suffix` are always
    kept whole, so an identifier such as ' [abc123]' survives truncation. Unlike
    `truncate_filename`, no suffix is inferred from dots in `text`. `tag` and `suffix` are
    used verbatim, so callers must pass text that is already safe in a filename.

    Args:
        text (str): Free text forming the start of the name.
        suffix (str, optional): Extension appended last, such as '.mp4'. Defaults to ''.
        tag (str, optional): Text kept between the text and the suffix. Defaults to ''.
        max_length (int, optional): The maximum number of bytes. Defaults to 255 for ext4.
        replacement (str, optional): Replacement for OS-reserved characters. Defaults to '_'.

    Returns:
        str: The filename, without any directory component.

    Raises:
        ValueError: If the name would keep no character of `text`, or would be '.' or '..'.
    """
    stem = replace_os_reserved_chars(text, replacement)
    kept = tag + suffix
    full_name = stem + kept
    name = _fit_stem(stem, kept, max_length)
    if name is None:
        raise ValueError(f'Not possible to build a filename that fits in {max_length} bytes: {full_name}')
    if name != full_name:
        logger.info('Truncated filename: %s -> %s', full_name, name)
    return name
