from os import fspath
from pathlib import Path
from unittest import mock

import pytest

import pathlib_extensions.nullable as testee


def test_null_path():
    np = testee.NullablePath()
    assert not np
    assert fspath(np) == ''
    assert hash(np) == hash(None)
    for k in ['exists', 'is_file', 'is_dir']:
        assert getattr(np, k)() is False
    for k in ['with_name', 'with_stem', 'with_suffix']:
        assert getattr(np, k)('.any') == np
    for k in ['name', 'suffix', 'stem', 'root', 'anchor']:
        assert isinstance(getattr(type(np), k), property)
        assert getattr(np, k) == ''
    assert isinstance(type(np).parent, property)
    assert np.parent == np
    assert isinstance(type(np).parents, property)
    assert np.parents == ()


def test_valid_path():
    p = Path(__file__)
    np = testee.NullablePath(p)
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
    assert isinstance(type(np).parent, property)
    assert np.parent.p == p.parent
    assert isinstance(type(np).parents, property)
    for x, y in zip(np.parents, p.parents):
        assert x.p == y


def test_concat():
    assert testee.NullablePath('a') / 'b' == testee.NullablePath('a/b')
    assert testee.NullablePath('a') / Path('b') == testee.NullablePath('a/b')
    assert testee.NullablePath('a') / testee.NullablePath('b') == testee.NullablePath('a/b')
    assert testee.NullablePath('a') / None == testee.NullablePath()
    assert testee.NullablePath('a') / testee.NullablePath() == testee.NullablePath()
    assert testee.NullablePath() / None == testee.NullablePath()
    assert testee.NullablePath() / 'b' == testee.NullablePath()
    assert testee.NullablePath() / Path('b') == testee.NullablePath()
    assert testee.NullablePath() / testee.NullablePath() == testee.NullablePath()
    assert testee.NullablePath() / testee.NullablePath('b') == testee.NullablePath()
    for left in [None, '/a']:
        with pytest.raises(TypeError):
            left / testee.NullablePath()  # type: ignore


def test_eq():
    assert testee.NullablePath() != ''
    assert testee.NullablePath() is not None
    assert testee.NullablePath() == testee.NullablePath('')
    assert testee.NullablePath('a/b') != 'a/b'
    assert testee.NullablePath('a/b') == Path('a/b')
    assert testee.NullablePath('a/b') == testee.NullablePath('a/b')


def test_repr():
    assert repr(testee.NullablePath()) == 'NullablePath(None)'
    assert str(testee.NullablePath()) == 'NullablePath(None)'
    assert repr(testee.NullablePath('a/b')) == 'NullablePath(a/b)'
    assert str(testee.NullablePath('a/b')) == 'NullablePath(a/b)'


def test_mkdir():
    np = testee.NullablePath()
    np.mkdir()
    np.p = mock.MagicMock()
    np.p.mkdir = mock_mkdir = mock.MagicMock()
    np.mkdir('a', b='b')
    mock_mkdir.assert_called_once_with('a', b='b')
