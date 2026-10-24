import logging
import os
import shutil
import stat
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Self

from pathlib_extensions.naming import get_numbered_path
from pathlib_extensions.overwrite import OverwritePolicy
from pathlib_extensions.prepare import (
    NotAFileError,
    prepare_output_dir,
    prepare_output_file,
)

__all__ = ['StagedFile']

logger = logging.getLogger(__name__)


class StagedFile:
    """
    Context manager that stages a file beside its destination and publishes it on success.

    On entry the destination is resolved through symlinks and prepared for output, and
    a private hidden directory is created beside the resolved target. The body writes the
    file at `path`, which is inside that directory and does not exist yet, so external tools
    can write to it by path and keep their own temporary files there. The file is named like
    the target unless `name` chooses another name, for tools that pick a format from the file
    name or expand templates in it.
    On a clean exit the file must be a regular file; it is then published to the target
    under `policy`, and the result is stored in `published`. If the
    body raises, nothing is published and the target is left untouched. The stage directory
    is removed on every exit. A process that is killed outright can leave it behind.

    Decide first with `OverwritePolicy.resolve`, so that no work is done when an existing
    file must be kept:

        target = policy.resolve(path)
        if target is not None:
            with StagedFile(target, policy) as staged:
                download(url, staged.path)
            print(staged.published)

    An instance can be entered only once.

    Attributes:
        policy (OverwritePolicy): How the file is published.
        target (Path): The resolved destination, set on entry.
        path (Path): Where the body writes the file, set on entry: inside the stage
            directory, named `name` if given and like the target otherwise.
        published (Path | None): Where the file was published, set on a clean exit: the
            target, or under RENAME a numbered name beside it; None under NEVER when a file
            appeared at the target meanwhile and was kept, and before publication.
    """

    target: Path
    path: Path

    def __init__(self, path: Path, policy: OverwritePolicy, *, name: str | None = None) -> None:
        """
        Remember the destination, policy and stage file name; nothing is touched until entry.

        Args:
            path (Path): Destination, normally returned by `OverwritePolicy.resolve`.
            policy (OverwritePolicy): How the file is published.
            name (str | None, optional): Name of the file at `path` inside the stage directory.
                It affects only staging: the file is still published to the target. Defaults
                to None, which names it like the target.

        Raises:
            ValueError: If `name` is not a single plain path component: empty, `.` or `..`,
                or containing a path separator or NUL.
        """
        if name is not None:
            separators = [sep for sep in (os.sep, os.altsep) if sep]
            if name in ('', '.', '..') or '\0' in name or any(sep in name for sep in separators):
                raise ValueError(f'A stage file name must be a single path component: {name!r}')
        self.policy = policy
        self.published: Path | None = None
        self._destination = path
        self._name = name
        self._mode: int | None = None
        self._stage_dir: Path | None = None
        self._entered = False

    def __enter__(self) -> Self:
        """
        Prepare the target and create the stage directory beside it.

        Returns:
            StagedFile: This instance, with `target` and `path` set.

        Raises:
            RuntimeError: If this instance was entered before.
            NotAFileError: If the resolved target exists but is not a file.
            PermissionError: As raised by `_resolve_publication_target`.
            OSError: If the stage directory cannot be created.
        """
        if self._entered:
            raise RuntimeError('A StagedFile can be entered only once')
        self._entered = True
        self.target, self._mode = _resolve_publication_target(self._destination, self.policy)
        self._stage_dir = Path(tempfile.mkdtemp(prefix='.staging-', dir=self.target.parent))
        self.path = self._stage_dir / (self.target.name if self._name is None else self._name)
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        """
        Publish the staged file after a clean exit, then remove the stage directory.

        Exceptions from the body propagate unchanged; failing to remove the stage directory
        then is ignored so that it does not hide them. After a clean exit, a cleanup failure
        is raised, even though the file may already be published.

        Raises:
            FileNotFoundError: If the body left no file at `path`.
            NotAFileError: If the body left something other than a regular file at `path`.
            OSError: As raised by `_publish_staged_file`, or if the stage directory cannot be
                removed.
        """
        assert self._stage_dir is not None  # set by __enter__
        try:
            if exc_type is None:
                try:
                    mode = self.path.lstat().st_mode
                except FileNotFoundError:
                    raise FileNotFoundError(f'Nothing was staged at {self.path}') from None
                if not stat.S_ISREG(mode):
                    raise NotAFileError(self.path)
                self.published = _publish_staged_file(self.path, self.target, self._mode, self.policy)
        except BaseException:
            shutil.rmtree(self._stage_dir, ignore_errors=True)
            raise
        shutil.rmtree(self._stage_dir, ignore_errors=exc_type is not None)


def _resolve_publication_target(path: Path, policy: OverwritePolicy = OverwritePolicy.ALWAYS) -> tuple[Path, int | None]:
    """
    Resolve a prepared destination through symlinks and capture its permission bits.

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
    target = path.resolve()
    keeping = policy is not OverwritePolicy.ALWAYS
    # A file that will be kept is only checked to be a file; its own write permission is irrelevant.
    if not (keeping and target.is_file()):
        prepare_output_file(target)
    # The stage is created beside the target and then linked or renamed over it, so the directory
    # must accept new entries even when an existing target is itself writable in place.
    prepare_output_dir(target.parent, create=False)
    if keeping:
        return target, None
    try:
        mode: int | None = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        mode = None
    return target, mode


def _publish_staged_file(stage: Path, target: Path, mode: int | None, policy: OverwritePolicy) -> Path | None:
    """
    Publish a completed stage file to its resolved target.

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
        target (Path): Destination returned by `_resolve_publication_target`.
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
    if mode is not None:
        stage.chmod(mode)
    if policy is OverwritePolicy.ALWAYS:
        stage.replace(target)
        return target
    if policy is OverwritePolicy.NEVER:
        try:
            os.link(stage, target)
        except FileExistsError:
            if not target.is_file():
                raise
            return None
        return target
    return _link_to_free_name(stage, target)


def _link_to_free_name(stage: Path, target: Path) -> Path:
    """
    Hard-link `stage` at `target`, or at its first free numbered name, and return that path.

    Any existing entry, whether a file, directory or dangling symlink, counts as taken and
    is left untouched.
    """
    candidate = target
    number = 0
    while True:
        try:
            os.link(stage, candidate)
        except FileExistsError:
            number += 1
            candidate = get_numbered_path(target, number)
        else:
            if number:
                logger.info('Renamed path: %s -> %s', target, candidate)
            return candidate
