from os import fspath
from pathlib import Path

import pytest

from pathlib_extensions.nullable import NullablePath


def test_null_path():
    mp = NullablePath()
    assert not mp
    assert fspath(mp) == ''
    assert hash(mp) == hash(None)
    for k in ['exists', 'is_file', 'is_dir']:
        assert getattr(mp, k)() is False
    for k in ['name', 'suffix', 'stem', 'parent', 'root', 'anchor']:
        assert isinstance(getattr(type(mp), k), property)
        assert getattr(mp, k) == ''
    assert isinstance(getattr(type(mp), 'parents'), property)
    assert mp.parents == ()


def test_valid_path():
    p = Path(__file__)
    mp = NullablePath(p)
    assert mp
    assert fspath(mp) == fspath(p)
    assert hash(mp) == hash(p)
    for k in ['exists', 'is_file', 'is_dir']:
        assert getattr(mp, k)() == getattr(p, k)()
    for k in ['name', 'suffix', 'stem', 'parent', 'root', 'anchor']:
        assert isinstance(getattr(type(mp), k), property)
        assert getattr(mp, k) == getattr(p, k)
    assert isinstance(getattr(type(mp), 'parents'), property)
    for x, y in zip(mp.parents, p.parents):
        assert x.p == y


def test_concat():
    assert NullablePath('a') / 'b' == NullablePath('a/b')
    assert NullablePath('a') / Path('b') == NullablePath('a/b')
    assert NullablePath('a') / NullablePath('b') == NullablePath('a/b')
    assert NullablePath('a') / None == NullablePath()
    assert NullablePath('a') / NullablePath() == NullablePath()
    assert NullablePath() / None == NullablePath()
    assert NullablePath() / 'b' == NullablePath()
    assert NullablePath() / Path('b') == NullablePath()
    assert NullablePath() / NullablePath() == NullablePath()
    assert NullablePath() / NullablePath('b') == NullablePath()
    for left in [None, '/a']:
        with pytest.raises(TypeError):
            left / NullablePath()


def test_eq():
    assert NullablePath() != ''
    assert NullablePath() != None
    assert NullablePath('a/b') != 'a/b'
    assert NullablePath('a/b') == Path('a/b')
    assert NullablePath('a/b') == NullablePath('a/b')


def test_repr():
    assert repr(NullablePath()) == 'NullablePath(None)'
    assert str(NullablePath()) == 'NullablePath(None)'
    assert repr(NullablePath('a/b')) == 'NullablePath(a/b)'
    assert str(NullablePath('a/b')) == 'NullablePath(a/b)'
