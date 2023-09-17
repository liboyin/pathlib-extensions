from os import fspath
from pathlib import Path
from unittest import mock

import pytest

from pathlib_extensions.nullable import NullablePath


def test_null_path():
    mp = NullablePath()
    assert not mp
    assert fspath(mp) == ''
    assert hash(mp) == hash(None)
    for k in ['exists', 'is_file', 'is_dir']:
        assert getattr(mp, k)() is False
    for k in ['with_name', 'with_stem', 'with_suffix']:
        assert getattr(mp, k)('.any') == mp
    for k in ['name', 'suffix', 'stem', 'root', 'anchor']:
        assert isinstance(getattr(type(mp), k), property)
        assert getattr(mp, k) == ''
    assert isinstance(getattr(type(mp), 'parent'), property)
    assert mp.parent == mp
    assert isinstance(getattr(type(mp), 'parents'), property)
    assert mp.parents == ()


def test_valid_path():
    p = Path(__file__)
    np = NullablePath(p)
    assert np
    assert fspath(np) == fspath(p)
    assert hash(np) == hash(p)
    for k in ['exists', 'is_file', 'is_dir']:
        assert getattr(np, k)() == getattr(p, k)()
    for k in ['with_name', 'with_stem', 'with_suffix']:
        # suffix must start with a dot
        assert getattr(np, k)('.any').p == getattr(p, k)('.any')
    for k in ['name', 'suffix', 'stem', 'root', 'anchor']:
        assert isinstance(getattr(type(np), k), property)
        assert getattr(np, k) == getattr(p, k)
    assert isinstance(getattr(type(np), 'parent'), property)
    assert np.parent.p == p.parent
    assert isinstance(getattr(type(np), 'parents'), property)
    for x, y in zip(np.parents, p.parents):
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


def test_mkdir():
    np = NullablePath()
    assert np.mkdir() is None
    np.p = mock.MagicMock()
    np.p.mkdir = mock_mkdir = mock.MagicMock()
    np.mkdir('a', b='b')
    mock_mkdir.assert_called_once_with('a', b='b')
