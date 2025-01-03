import re

__all__ = ['replace_os_reserved_chars']


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
