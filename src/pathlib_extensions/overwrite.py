from enum import Enum
from pathlib import Path


class OverwriteMode(Enum):
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


def get_safe_output_path(path: Path) -> Path:
    """
    Returns a safe output path by incrementing a counter in the file/directory name if the path already exists.

    Args:
        path (Path): The file/directory path being considered.

    Returns:
        Path: A safe file/directory path to write to.
    """
    if not path.exists():
        return path
    counter = 1
    while True:
        new = path.with_suffix(f".{counter}{path.suffix}")
        if not new.exists():
            print(f'Returning safe output path {new} for input {path}')
            return new
        counter += 1


def get_output_path_by_overwrite_mode(path: Path, overwrite_mode: OverwriteMode) -> Path | None:
    """
    Returns the output path for an existing file/directory path based on the specified overwrite mode.

    Args:
        path (Path): An existing file/directory path.
        overwrite_mode (OverwriteMode): Always, never, prompt user, or rename.

    Returns:
        Path | None: A safe file/directory path to write to, or None if nothing should be written.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    overwrite_message = f'Overwriting path: {path}'
    not_overwrite_message = f'Not overwriting path: {path}'
    match overwrite_mode:
        case OverwriteMode.ALWAYS:
            print(overwrite_message)
            return path
        case OverwriteMode.NEVER:
            print(not_overwrite_message)
            return None
        case OverwriteMode.PROMPT:
            if user_confirms_overwrite(path):
                print(overwrite_message)
                return path
            print(not_overwrite_message)
            return None
        case OverwriteMode.RENAME:
            return get_safe_output_path(path)
