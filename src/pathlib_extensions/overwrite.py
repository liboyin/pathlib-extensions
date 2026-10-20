import stat
from enum import Enum
from pathlib import Path

from pathlib_extensions.naming import get_first_available_path
from pathlib_extensions.prepare import NotAFileError

__all__ = ['OverwriteMode', 'OverwritePolicy', 'overwrite_existing_path', 'resolve_overwrite_mode', 'user_confirms_overwrite']


class OverwriteMode(str, Enum):
    ALWAYS = "always"
    NEVER = "never"
    PROMPT = "prompt"
    RENAME = "rename"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(mode.value for mode in cls)


def user_confirms_overwrite(path: Path) -> bool:
    """
    Prompts the user to confirm overwriting an existing file/directory path.
    """
    user_input = input(f"Path '{path}' already exists. Overwrite? (y/N): ").strip().lower()
    return user_input == 'y'


def overwrite_existing_path(path: Path, overwrite_mode: OverwriteMode) -> bool:
    """
    Returns whether to overwrite an existing file/directory path based on the specified overwrite mode.

    Args:
        path (Path): An existing file/directory path.
        overwrite_mode (OverwriteMode): Always, never, prompt user, or rename.

    Returns:
        bool: True if the path should be overwritten, False otherwise.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    overwrite_message = f'Overwriting path: {path}'
    not_overwrite_message = f'Not overwriting path: {path}'
    match overwrite_mode:
        case OverwriteMode.ALWAYS:
            print(overwrite_message)
            return True
        case OverwriteMode.NEVER:
            print(not_overwrite_message)
            return False
        case OverwriteMode.PROMPT:
            if not user_confirms_overwrite(path):
                print(not_overwrite_message)
                return False
            print(overwrite_message)
            return True
        case OverwriteMode.RENAME:
            return False


def resolve_overwrite_mode(path: Path, overwrite_mode: OverwriteMode) -> OverwriteMode | None:
    """
    Decide before any expensive work whether a file may be written at `path`.

    Only an existing file, or a symlink to one, is checked with `overwrite_existing_path`;
    for any other path `overwrite_mode` is returned unchanged and the writer itself rejects
    a destination it cannot use, such as a directory.

    Args:
        path (Path): Destination of the planned write.
        overwrite_mode (OverwriteMode): Always, never, prompt user, or rename.

    Returns:
        OverwriteMode | None: None when an existing file must be kept. Otherwise the mode
        to carry into the write, with an approved PROMPT turned into ALWAYS so that later
        checks do not ask again.
    """
    if not path.is_file():
        return overwrite_mode
    if not overwrite_existing_path(path, overwrite_mode):
        return None
    return OverwriteMode.ALWAYS if overwrite_mode == OverwriteMode.PROMPT else overwrite_mode


class OverwritePolicy(str, Enum):
    """
    How to treat an existing file at a destination, as selected by a user.

    Members are strings so that `values()` can serve as command-line choices. This supersedes
    `OverwriteMode`; its PROMPT has no counterpart here.

    Destinations are files: see `resolve` for symlinks and other kinds of existing entry.

    Attributes:
        ALWAYS: Always overwrite an existing file.
        NEVER: Never overwrite an existing file.
        RENAME: Never overwrite an existing file, but instead rename the new file.
    """

    ALWAYS = "always"
    NEVER = "never"
    RENAME = "rename"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return every policy's string value in declaration order."""
        return tuple(policy.value for policy in cls)

    def resolve(self, path: Path, max_length: int = 255, max_attempts: int = 10) -> Path | None:
        """
        Decide before any expensive work where, if anywhere, the file for `path` may be written.

        ALWAYS returns `path`. NEVER returns None when a file, or a symlink to one, exists at
        `path`, and `path` otherwise. Under both, a dangling symlink counts as no file, since
        the writer creates its target, while anything else that is not a file, such as a
        directory, raises before work is wasted on an output that cannot be written. RENAME
        returns `get_first_available_path(path, max_length, max_attempts)`: `path` itself when
        nothing at all exists there, otherwise its lowest free numbered variant, such as
        `hello.1.mp4`; any entry counts as taken. A message is printed whenever an existing
        entry changes or confirms the answer.

        The answer is only a snapshot. Under NEVER and RENAME the writer should still create
        the file exclusively, in case a file appears at the returned path meanwhile.

        Args:
            path (Path): Destination of the planned write.
            max_length (int, optional): Under RENAME, the maximum number of bytes for a
                numbered name. Defaults to 255 for ext4.
            max_attempts (int, optional): Under RENAME, how many names to check in total,
                `path` included. Defaults to 10.

        Returns:
            Path | None: Where to write, or None when an existing file must be kept.

        Raises:
            NotAFileError: Under ALWAYS and NEVER, if something other than a file exists at
                `path`, following symlinks.
            FileExistsError: Under RENAME, if all `max_attempts` names are taken.
            ValueError: Under RENAME, if `max_attempts` is less than 1, or `path` is taken and
                no stem character fits beside a numbered suffix within `max_length` bytes.
            OSError: If `path`, or under RENAME a candidate, cannot be checked.
        """
        if self is OverwritePolicy.RENAME:
            available = get_first_available_path(path, max_length, max_attempts)
            if available != path:
                print(f'Not overwriting path: {path}, writing to: {available}')
            return available
        try:
            mode = path.stat().st_mode
        except FileNotFoundError:
            return path
        if not stat.S_ISREG(mode):
            raise NotAFileError(path)
        if self is OverwritePolicy.ALWAYS:
            print(f'Overwriting path: {path}')
            return path
        print(f'Not overwriting path: {path}')
        return None
