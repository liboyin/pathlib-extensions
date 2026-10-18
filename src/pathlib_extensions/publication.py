import os
import stat
from pathlib import Path

from pathlib_extensions.overwrite import OverwriteMode
from pathlib_extensions.prepare import prepare_output_dir, prepare_output_file

__all__ = ['publish_staged_file', 'resolve_publication_target']


def resolve_publication_target(path: Path) -> tuple[Path, int | None]:
    """
    Resolve a prepared destination through symlinks and capture its permission bits.

    Call this before writing a stage, so that the stage can be created beside the real
    target and receive the target's existing mode when it is published.

    Args:
        path (Path): Literal destination, already checked by `prepare_output_file`.

    Returns:
        tuple[Path, int | None]: The resolved target, prepared for output with parents
        created as needed, and its existing permission bits, or None when no file exists
        there yet.

    Raises:
        NotAFileError: If the resolved target exists but is not a file.
        PermissionError: If the resolved target exists but is not writable, or its directory cannot
            accept the new entries that staging and publication need.
    """
    target = path.resolve()
    prepare_output_file(target)
    # The stage is created beside the target and then linked or renamed over it, so the directory
    # must accept new entries even when an existing target is itself writable in place.
    prepare_output_dir(target.parent, create=False)
    try:
        mode: int | None = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        mode = None
    return target, mode


def publish_staged_file(stage: Path, target: Path, mode: int | None, overwrite: OverwriteMode) -> None:
    """
    Publish a completed stage file to its resolved target.

    The stage must be a completed regular file on the same filesystem as the target,
    normally a sibling created by the caller. Captured mode bits are applied to the stage
    first. NEVER and RENAME publish by hard-link create-if-absent: if a file (or a symlink
    to one) appeared at the target meanwhile, it is kept and the stage is not published;
    any other collision raises. Other modes atomically replace the target inode, so
    hardlinked aliases keep the old contents and ownership, ACLs and extended attributes
    may change. There is no fallback when hard links are unsupported, because copying
    could overwrite a competing file. Replacement consumes the stage pathname; callers
    remove any stage left behind. This protects against process interruption, not power
    loss: nothing is fsynced.

    Args:
        stage (Path): Completed, caller-owned stage beside the target.
        target (Path): Destination returned by `resolve_publication_target`.
        mode (int | None): Permission bits to retain, or None to keep the stage's.
        overwrite (OverwriteMode): Policy deciding create-if-absent or replacement.

    Raises:
        FileExistsError: If create-if-absent collides with something other than a file.
        OSError: If mode restoration, linking (including unsupported hard links) or
            replacement fails.
    """
    if mode is not None:
        stage.chmod(mode)
    if overwrite in (OverwriteMode.NEVER, OverwriteMode.RENAME):
        try:
            os.link(stage, target)
        except FileExistsError:
            if target.is_file():
                return
            raise
    else:
        stage.replace(target)
