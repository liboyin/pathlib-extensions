from enum import Enum
from pathlib import Path


class OverwriteMode(Enum):
    ALWAYS = "always"
    NEVER = "never"
    PROMPT = "prompt"

OverwriteMode.values = tuple(mode.value for mode in OverwriteMode)


def overwrite_existing_path(path: Path, overwrite_mode: OverwriteMode) -> bool:
    """
    Returns whether to overwrite an existing path based on the specified overwrite mode.

    Args:
        path (Path): The path being considered.
        overwrite_mode (OverwriteMode): Always, never, or prompt user.

    Returns:
        bool: True if the path should be overwritten, False otherwise.
    """
    message = f"Not overwriting existing path: {path}"
    if overwrite_mode == OverwriteMode.NEVER:
        print(message)
        return False
    elif overwrite_mode == OverwriteMode.PROMPT:
        user_input = input(f"Path '{path}' already exists. Overwrite? (y/N): ").strip().lower()
        if user_input != 'y':
            print(message)
            return False
    return True
