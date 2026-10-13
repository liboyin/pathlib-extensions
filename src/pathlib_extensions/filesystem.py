from pathlib import Path
import re

__all__ = ['replace_os_reserved_chars', 'truncate_filename']


def replace_os_reserved_chars(text: str, replacement: str = '_') -> str:
    """
    Replace OS-reserved characters in a string with a specified replacement character.

    Should work on Windows, Linux, and macOS.

    Args:
        text (str): The input text.
        replacement (str, optional): The replacement character. Defaults to '_'.

    Returns:
        str: The modified text with reserved characters replaced by `replacement`.
    """
    return re.sub(r'[\\/*?:"<>|]', replacement, text)


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
