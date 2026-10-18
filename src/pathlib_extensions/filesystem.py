from pathlib import Path
import re

__all__ = ['replace_os_reserved_chars', 'truncate_filename', 'build_filename']


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


def _extension_suffix(filename: str) -> str:
    """
    Return the trailing run of extension-like suffixes of a filename.

    A suffix is extension-like when it is a dot followed only by ASCII letters or digits,
    so `.tar.gz` is kept whole while text after a dot inside a title, such as `. Smith`,
    is not a suffix.

    Args:
        filename (str): A filename without directory components.

    Returns:
        str: The suffix run, such as '.tar.gz', or '' when the name has none.
    """
    suffix = ''
    for part in reversed(Path(filename).suffixes):
        if not _EXTENSION_SUFFIX.fullmatch(part):
            break
        suffix = part + suffix
    return suffix


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
    suffix = _extension_suffix(filename)
    stem_max_bytes_length = max_length - len(suffix.encode('utf-8'))
    stem = filename[:len(filename) - len(suffix)]
    # Cutting the encoded stem can split a multi-byte character; decoding with
    # errors='ignore' drops only that incomplete trailing character.
    stem = stem.encode('utf-8')[:max(stem_max_bytes_length, 0)].decode('utf-8', errors='ignore')
    name = stem + suffix
    # '.' and '..' would turn the result into a directory path.
    if not stem or name in ('.', '..'):
        raise ValueError(f'Not possible to truncate filename to fit in {max_length} bytes: {path}')
    result = path.parent / name
    print(f'Truncated path: {path} -> {result}')
    return result


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
    stem_max_bytes_length = max_length - len(kept.encode('utf-8'))
    full_name = stem + kept
    # Cutting the encoded stem can split a multi-byte character; decoding with
    # errors='ignore' drops only that incomplete trailing character.
    stem = stem.encode('utf-8')[:max(stem_max_bytes_length, 0)].decode('utf-8', errors='ignore')
    name = stem + kept
    if not stem or name in ('.', '..'):
        raise ValueError(f'Not possible to build a filename that fits in {max_length} bytes: {full_name}')
    if name != full_name:
        print(f'Truncated filename: {full_name} -> {name}')
    return name
