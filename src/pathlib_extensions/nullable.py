from functools import partial
from os import PathLike, fspath
from pathlib import Path
from typing import Any, Tuple


# Optional* is already taken in Python; Maybe* is only used in Haskell. Nullable* should be less confusing?
class NullablePath(PathLike):
    def __new__(cls, *args, **kwargs) -> 'NullablePath':
        # properties can only be set at the class level, not at the instance level
        for k in ['name', 'suffix', 'stem', 'parent', 'root', 'anchor']:
            # for lambda functions defined in a loop, variable binding happens at run time
            # this line uses functools.partial to bind x early while binding self late
            setattr(cls, k, property(partial(lambda self, x: getattr(self.p, x, ''), x=k)))
        return super().__new__(cls)

    def __init__(self, p: PathLike | None = None) -> None:
        self.p: Path | None = Path(p) if p else None
        for k in ['exists', 'is_file', 'is_dir']:
            # self must be bound to the time when the method is called because p is mutable
            setattr(self, k, partial(lambda x: getattr(self.p, x)() if self else False, x=k))

    def __bool__(self) -> bool:
        return self.p is not None

    def __hash__(self) -> int:
        return hash(self.p)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, NullablePath):
            return self.p == other.p
        if isinstance(other, Path):
            return self.p == other
        return NotImplemented
    
    def __fspath__(self) -> str:
        # must be defined when super().__new__() is called
        if self:
            return fspath(self.p)
        return ''

    def __truediv__(self, other: PathLike | None) -> 'NullablePath':
        if not other or not self:
            return self.__class__()
        return self.__class__(self.p / fspath(other))

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.p})'

    def __str__(self) -> str:
        return repr(self)

    @property
    def parents(self) -> Tuple['NullablePath', ...]:
        if self:
            return tuple(self.__class__(x) for x in self.p.parents)
        return ()
