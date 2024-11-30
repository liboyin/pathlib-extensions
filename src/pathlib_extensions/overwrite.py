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
            user_input = input(f"Path '{path}' already exists. Overwrite? (y/N): ").strip().lower()
            if user_input != 'y':
                print(not_overwrite_message)
                return False
            print(overwrite_message)
            return True
        case OverwriteMode.RENAME:
            return False
