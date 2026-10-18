from enum import Enum
from pathlib import Path

__all__ = ['OverwriteMode', 'overwrite_existing_path', 'resolve_overwrite_mode', 'user_confirms_overwrite']


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
