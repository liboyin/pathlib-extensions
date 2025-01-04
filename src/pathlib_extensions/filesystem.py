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


def truncate_filename(path: str | Path, max_length: int = 255) -> Path:
    """
    Truncate the filename such that it fits in `max_length` bytes.

    Args:
        path (str | Path): The path to process.
        max_length (int, optional): The maximum number of bytes. Defaults to 255 for ext4.

    Returns:
        Path: The processed path.
    """
    if isinstance(path, str):
        path = Path(path)
    filename = path.name
    if len(filename.encode('utf-8')) <= max_length:
        return path
    suffixes = ''.join(path.suffixes)
    suffixes_bytes_length = len(suffixes.encode('utf-8'))
    if suffixes_bytes_length >= max_length:
        raise ValueError(f'Not possible to truncate filename to fit in {max_length} bytes: {path}')
    stem_max_bytes_length = max_length - suffixes_bytes_length
    stem = filename[:-len(suffixes)]
    while len(stem.encode('utf-8')) > stem_max_bytes_length:
        stem = stem[:-1]
    result = path.parent / (stem + suffixes)
    print(f'Truncated path: {path} -> {result}')
    return result
