import pytest
from main import resource_path

def test_resource_path_returns_path():
    path = resource_path("testfile.txt")
    assert isinstance(path, str)
    assert path.endswith("testfile.txt")