from pathlib_extensions.filesystem import replace_os_reserved_chars


def test_remove_os_reserved_chars():
    assert replace_os_reserved_chars("file?name") == "file_name"
    assert replace_os_reserved_chars("file*name") == "file_name"
    assert replace_os_reserved_chars("file:name") == "file_name"
    assert replace_os_reserved_chars("file<name") == "file_name"
    assert replace_os_reserved_chars("file>name") == "file_name"
    assert replace_os_reserved_chars("file|name") == "file_name"
    assert replace_os_reserved_chars("file/name") == "file_name"
    assert replace_os_reserved_chars("file\\name") == "file_name"
    assert replace_os_reserved_chars('file"name') == "file_name"
