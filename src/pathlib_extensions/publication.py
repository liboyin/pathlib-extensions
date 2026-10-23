"""Deprecated staged-publication functions; use `StagedFile` instead."""
import warnings
from pathlib import Path

from pathlib_extensions.overwrite import OverwritePolicy
from pathlib_extensions.staging import _publish_staged_file, _resolve_publication_target

__all__ = ['publish_staged_file', 'resolve_publication_target']


def resolve_publication_target(path: Path, policy: OverwritePolicy = OverwritePolicy.ALWAYS) -> tuple[Path, int | None]:
    """
    Resolve a prepared destination through symlinks and capture its permission bits.

    Deprecated: use `StagedFile`, which resolves the destination on entry. This emits a
    DeprecationWarning, then behaves exactly as before.

    Call this before writing a stage, so that the stage can be created beside the real
    target and receive the target's existing mode when it is published. NEVER and RENAME
    never write over an existing file, so under them a file already at the target need not
    be writable and its mode is not captured: any published output is a new file and keeps
    the stage's own mode.

    Args:
        path (Path): Literal destination, normally returned by `OverwritePolicy.resolve`.
        policy (OverwritePolicy, optional): The policy the stage will be published under.
            Defaults to ALWAYS.

    Returns:
        tuple[Path, int | None]: The resolved target, prepared for output with parents
        created as needed, and its existing permission bits, or None when no file exists
        there yet or `policy` is not ALWAYS.

    Raises:
        NotAFileError: If the resolved target exists but is not a file.
        PermissionError: If the resolved target exists, is not writable and `policy` is
            ALWAYS, or its directory cannot accept the new entries that staging and
            publication need.
    """
    warnings.warn('resolve_publication_target is deprecated; use StagedFile instead', DeprecationWarning, stacklevel=2)
    return _resolve_publication_target(path, policy)


def publish_staged_file(stage: Path, target: Path, mode: int | None, policy: OverwritePolicy) -> Path | None:
    """
    Publish a completed stage file to its resolved target.

    Deprecated: use `StagedFile`, which publishes the staged file on a clean exit. This
    emits a DeprecationWarning, then behaves exactly as before.

    The stage must be a completed regular file on the same filesystem as the target,
    normally a sibling created by the caller. Captured mode bits are applied to the stage
    first. NEVER publishes by hard-link create-if-absent: if a file (or a symlink to one)
    appeared at the target meanwhile, it is kept, the stage is not published and None is
    returned; any other collision raises. RENAME also links create-if-absent, but on any
    collision moves on to the next numbered name beside the target (see
    `get_numbered_path`), so nothing existing is touched and a name taken during the
    caller's work is still avoided. ALWAYS atomically replaces the target inode, so
    hardlinked aliases keep the old contents and ownership, ACLs and extended attributes
    may change. There is no fallback when hard links are unsupported, because copying
    could overwrite a competing file. Replacement consumes the stage pathname; callers
    remove any stage left behind. This protects against process interruption, not power
    loss: nothing is fsynced.

    Args:
        stage (Path): Completed, caller-owned stage beside the target.
        target (Path): Destination returned by `resolve_publication_target`.
        mode (int | None): Permission bits to retain, or None to keep the stage's.
        policy (OverwritePolicy): The policy `target` was resolved under.

    Returns:
        Path | None: Where the stage was published: the target, or under RENAME a numbered
        name beside it when the target was taken; None when NEVER kept a competing file.

    Raises:
        ValueError: If a numbered name cannot be fitted in 255 bytes.
        FileExistsError: If create-if-absent under NEVER collides with something other than
            a file.
        OSError: If mode restoration, linking (including unsupported hard links) or
            replacement fails.
    """
    warnings.warn('publish_staged_file is deprecated; use StagedFile instead', DeprecationWarning, stacklevel=2)
    return _publish_staged_file(stage, target, mode, policy)
