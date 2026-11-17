import errno
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

_LINK_UNSUPPORTED = frozenset({errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP})
"""`os.link` errors that mean the filesystem offers no hard links, such as a macOS SMB mount."""


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

    NEVER publishes with a hard link, which never replaces a file. A filesystem without hard
    links, such as a macOS SMB mount, refuses that. With `rename_fallback`, NEVER then checks that
    no file is at the target and renames the stage there. A file that appears between the check
    and the rename is replaced, so only callers that accept that race opt in.

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

    def __init__(
        self, path: Path, policy: OverwritePolicy, *, name: str | None = None, rename_fallback: bool = False,
    ) -> None:
        """
        Remember the destination, policy and stage file name; nothing is touched until entry.

        Args:
            path (Path): Destination, normally returned by `OverwritePolicy.resolve`.
            policy (OverwritePolicy): How the file is published.
            name (str | None, optional): Name of the file at `path` inside the stage directory.
                It affects only staging: the file is still published to the target. Defaults
                to None, which names it like the target.
            rename_fallback (bool, optional): Under NEVER, when the filesystem refuses hard
                links, publish by a check followed by a rename instead of raising. A file that
                appears between the two is replaced. Other policies ignore it. Defaults to
                False, which raises when hard links are unsupported.

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
        self._rename_fallback = rename_fallback
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
                self.published = _publish_staged_file(
                    self.path, self.target, self._mode, self.policy, rename_fallback=self._rename_fallback,
                )
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


def _publish_staged_file(
    stage: Path, target: Path, mode: int | None, policy: OverwritePolicy, *, rename_fallback: bool = False,
) -> Path | None:
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
    may change. When hard links are unsupported, NEVER raises unless `rename_fallback` is
    set; then it checks and renames, as `_rename_if_absent` describes. There is no fallback
    for RENAME, and no copying fallback, because copying could overwrite a competing file.
    Replacement consumes the stage pathname; callers
    remove any stage left behind. This protects against process interruption, not power
    loss: nothing is fsynced.

    Args:
        stage (Path): Completed, caller-owned stage beside the target.
        target (Path): Destination returned by `_resolve_publication_target`.
        mode (int | None): Permission bits to retain, or None to keep the stage's.
        policy (OverwritePolicy): The policy `target` was resolved under.
        rename_fallback (bool, optional): Under NEVER, fall back to a check and a rename when
            the filesystem refuses hard links. Defaults to False.

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
        except OSError as error:
            if not (rename_fallback and error.errno in _LINK_UNSUPPORTED):
                raise
            return _rename_if_absent(stage, target)
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


def _rename_if_absent(stage: Path, target: Path) -> Path | None:
    """
    Publish `stage` at `target` by a rename, unless an entry is already there; NEVER without hard links.

    No portable primitive renames without replacing: a plain rename replaces an existing file,
    and filesystems such as a macOS SMB mount refuse exclusive renames as well as hard links.
    The target is therefore checked first. A file that appears between the check and the rename
    is replaced; the caller accepted that by choosing `rename_fallback`. The outcomes otherwise
    match the hard-link path: a file, or a symlink to one, is kept and any other entry raises.

    Args:
        stage (Path): Completed, caller-owned stage beside the target.
        target (Path): Destination returned by `_resolve_publication_target`.

    Returns:
        Path | None: `target` when the stage was renamed there, or None when a file was kept.

    Raises:
        FileExistsError: If something other than a file, or a symlink to one, is at the target.
        OSError: If the check or the rename fails.
    """
    try:
        target.lstat()
    except FileNotFoundError:
        stage.rename(target)
        logger.info('Hard links are unsupported; published by rename after checking: %s', target)
        return target
    if not target.is_file():
        raise FileExistsError(errno.EEXIST, 'Something other than a file is at the target', str(target))
    return None
