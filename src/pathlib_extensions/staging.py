import os
import shutil
import stat
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Self

from pathlib_extensions.overwrite import OverwritePolicy
from pathlib_extensions.prepare import NotAFileError
from pathlib_extensions.publication import (
    publish_staged_file,
    resolve_publication_target,
)

__all__ = ['StagedFile']


class StagedFile:
    """
    Context manager that stages a file beside its destination and publishes it on success.

    On entry the destination is resolved and prepared with `resolve_publication_target`, and
    a private hidden directory is created beside the resolved target. The body writes the
    file at `path`, which is inside that directory and does not exist yet, so external tools
    can write to it by path and keep their own temporary files there. The file is named like
    the target unless `name` chooses another name, for tools that pick a format from the file
    name or expand templates in it.
    On a clean exit the file must be a regular file; it is then published with
    `publish_staged_file` under `policy`, and the result is stored in `published`. If the
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
            PermissionError: As raised by `resolve_publication_target`.
            OSError: If the stage directory cannot be created.
        """
        if self._entered:
            raise RuntimeError('A StagedFile can be entered only once')
        self._entered = True
        self.target, self._mode = resolve_publication_target(self._destination, self.policy)
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
            OSError: As raised by `publish_staged_file`, or if the stage directory cannot be
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
                self.published = publish_staged_file(self.path, self.target, self._mode, self.policy)
        except BaseException:
            shutil.rmtree(self._stage_dir, ignore_errors=True)
            raise
        shutil.rmtree(self._stage_dir, ignore_errors=exc_type is not None)
