import os
import stat
from pathlib import Path

__all__ = ['NotAFileError', 'SuffixError', 'prepare_input_dir', 'prepare_input_file', 'prepare_output_dir', 'prepare_output_file']


class NotAFileError(OSError):
    """Raised when expecting a file, but encountering a different type of path.

    This class serves as the logical counterpart of the built-in `NotADirectoryError`.
    """


class SuffixError(Exception):
    """Raised when the file suffix does not meet the expected criteria."""


def prepare_input_dir(p: str | Path) -> Path:
    """Prepare the target directory path for reading.

    Args:
        p (str | Path): The target directory path.

    Returns:
        Path: The verified directory path.

    Raises:
        FileNotFoundError: If the target path does not exist.
        NotADirectoryError: If the target path exists but is not a directory.
        PermissionError: If the current user cannot list or search the target directory; search
            permission is needed to open its entries.
    """
    if isinstance(p, str):
        p = Path(p)
    if not p.is_dir():
        if p.exists():
            raise NotADirectoryError(p)
        raise FileNotFoundError(p)
    if not os.access(p, os.R_OK | os.X_OK):
        raise PermissionError(p)
    return p


def prepare_input_file(p: str | Path, check_suffix: str | None = None, with_suffix: str | None = None) -> Path:
    """Prepare the target file path for reading.

    Args:
        p (str | Path): The target file path.
        check_suffix (Union[str, None], optional): Expected suffix for the file. Defaults to None.
        with_suffix (Union[str, None], optional): Suffix to add if missing. Defaults to None.

    Returns:
        Path: The verified file path.

    Raises:
        FileNotFoundError: If the target path does not exist.
        NotAFileError: If the target path exists but is not a file.
        SuffixError: If the file suffix does not meet the expected criteria.
        ValueError: If both `check_suffix` and `with_suffix` are specified.
        PermissionError: If the current user has no read permission to the target file.
    """
    if isinstance(p, str):
        p = Path(p)
    if check_suffix is not None:
        if with_suffix is not None:
            raise ValueError('At most one of check_suffix and with_suffix can be specified')
        if p.suffix != check_suffix:
            raise SuffixError(check_suffix, p)
    if with_suffix is not None:
        p = p.with_suffix(with_suffix)
    if not p.is_file():
        if p.exists():
            raise NotAFileError(p)
        raise FileNotFoundError(p)
    if not os.access(p, os.R_OK):
        raise PermissionError(p)
    return p


def prepare_output_dir(p: str | Path, create: bool = True) -> Path:
    """Prepare the target directory path for writing.

    Args:
        p (str | Path): The target directory path.
        create (bool, optional): Whether to create the directory and its missing parents if it
            doesn't exist. Defaults to True.

    Returns:
        Path: The verified or created directory path.

    Raises:
        FileNotFoundError: If the target path does not exist and `create` is False.
        NotADirectoryError: If the target path or one of its ancestors exists but is not a directory.
        PermissionError: If the current user cannot reach the target path, or cannot create entries in
            the target directory (which needs both write and search permission).
    """
    if isinstance(p, str):
        p = Path(p)
    # stat() rather than exists(): since Python 3.13, exists() reports False for an unsearchable
    # ancestor, which would misreport a permission problem as a missing directory.
    try:
        if not stat.S_ISDIR(p.stat().st_mode):
            raise NotADirectoryError(p)
    except FileNotFoundError:
        if not create:
            raise FileNotFoundError(p) from None
        p.mkdir(parents=True, exist_ok=True)
    if not os.access(p, os.W_OK | os.X_OK):
        raise PermissionError(p)
    return p


def prepare_output_file(p: str | Path, check_suffix: str | None = None, with_suffix: str | None = None, create: bool = True) -> Path:
    """Prepare the target file path for writing.

    Args:
        p (str | Path): The target file path.
        check_suffix (Union[str, None], optional): Expected suffix for the file. Defaults to None.
        with_suffix (Union[str, None], optional): Suffix to add if missing. Defaults to None.
        create (bool, optional): Whether to create the parent directory and its missing parents if the
            target file doesn't exist. Defaults to True.

    Returns:
        Path: The verified or updated file path.

    Raises:
        FileNotFoundError: If neither the target file nor its parent directory exists and `create` is
            False.
        NotAFileError: If the target path exists but is not a file.
        NotADirectoryError: If the target file does not exist and its parent path or one of its
            ancestors exists but is not a directory.
        ValueError: If both `check_suffix` and `with_suffix` are specified.
        SuffixError: If the file suffix does not meet the expected criteria.
        PermissionError: If the target file exists and the current user has no write permission to it,
            or if it does not exist and the user cannot create entries in its parent directory. An
            existing file is checked for in-place writing only: its directory may be read-only.
    """
    if isinstance(p, str):
        p = Path(p)
    if check_suffix is not None:
        if with_suffix is not None:
            raise ValueError('At most one of check_suffix and with_suffix can be specified')
        if p.suffix != check_suffix:
            raise SuffixError(check_suffix, p)
    if with_suffix is not None:
        p = p.with_suffix(with_suffix)
    if p.exists():
        if not p.is_file():
            raise NotAFileError(p)
        if not os.access(p, os.W_OK):
            raise PermissionError(p)
    else:
        prepare_output_dir(p.parent, create)
    return p
