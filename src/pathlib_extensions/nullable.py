from os import PathLike, fspath
from pathlib import Path
from typing import Any, Tuple, TypeVar, override

__all__ = ['NullablePath']
T = TypeVar('T')


# Optional* is already taken in Python; Maybe* is only used in Haskell. Nullable* should be less confusing?
class NullablePath(PathLike):
    def __new__(cls, *args, **kwargs) -> 'NullablePath':
        return super().__new__(cls)

    def __init__(self, p: PathLike | str | None = None) -> None:
        self.p: Path | None = Path(p) if p else None

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

    @override
    def __fspath__(self) -> str:
        # must be defined when super().__new__() is called
        if self.p:
            return fspath(self.p)
        return ''

    def __truediv__(self, other: PathLike | str | None) -> 'NullablePath':
        if not other or not self.p:
            return self.__class__()
        return self.__class__(self.p / fspath(other))

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.p})'

    def __str__(self) -> str:
        return repr(self)

    @property
    def parent(self) -> 'NullablePath':
        if self.p:
            return self.__class__(self.p.parent)
        return self.__class__()

    @property
    def parents(self) -> Tuple['NullablePath', ...]:
        if self.p:
            return tuple(self.__class__(x) for x in self.p.parents)
        return ()

    def _redirect_getattr(self, attr_name: str, default: T) -> T:
        if self.p:
            return getattr(self.p, attr_name)
        return default

    @property
    def name(self) -> str:
        return self._redirect_getattr('name', default='')

    @property
    def stem(self) -> str:
        return self._redirect_getattr('stem', default='')

    @property
    def suffix(self) -> str:
        return self._redirect_getattr('suffix', default='')

    @property
    def suffixes(self) -> list[str]:
        return self._redirect_getattr('suffixes', default=[])
    
    @property
    def root(self) -> str:
        return self._redirect_getattr('root', default='')

    @property
    def anchor(self) -> str:
        return self._redirect_getattr('anchor', default='')

    def mkdir(self, *args, **kwargs) -> None:
        if self.p:
            self.p.mkdir(*args, **kwargs)

    def _redirect_method_call(self, method_name: str, *args, default: T, **kwargs) -> T:
        if self.p:
            return getattr(self.p, method_name)(*args, **kwargs)
        return default

    def exists(self) -> bool:
        return self._redirect_method_call('exists', default=False)

    def is_file(self) -> bool:
        return self._redirect_method_call('is_file', default=False)

    def is_dir(self) -> bool:
        return self._redirect_method_call('is_dir', default=False)

    def with_name(self, name: str) -> 'NullablePath':
        return self.__class__(self._redirect_method_call('with_name', name, default=self))

    def with_stem(self, stem: str) -> 'NullablePath':
        return self.__class__(self._redirect_method_call('with_stem', stem, default=self))

    def with_suffix(self, suffix: str) -> 'NullablePath':
        return self.__class__(self._redirect_method_call('with_suffix', suffix, default=self))
