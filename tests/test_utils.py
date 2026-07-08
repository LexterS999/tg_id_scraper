"""
Unit tests for utility functions (loading, saving)
"""

import pytest
import tempfile
import os
import json
from unittest.mock import patch, Mock

from parser.utils import load_links_from_file, load_links_from_url, save_json


def test_load_links_from_file():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
        f.write("vless://example1\n")
        f.write("# comment line\n")
        f.write("vless://example2\n")
        f.write("\n")
        f.flush()
        links = load_links_from_file(f.name)
        assert links == ["vless://example1", "vless://example2"]
    os.unlink(f.name)


def test_load_links_from_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_links_from_file("non_existent_file.txt")


@patch('parser.utils.requests.Session.get')
def test_load_links_from_url_success(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"vless://line1\nvless://line2\n#comment\n"
    mock_response.text = "vless://line1\nvless://line2\n#comment\n"
    mock_get.return_value = mock_response
    
    links = load_links_from_url("http://example.com/config.txt")
    assert links == ["vless://line1", "vless://line2"]


@patch('parser.utils.requests.Session.get')
def test_load_links_from_url_retry(mock_get):
    # First two attempts fail, third succeeds
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"vless://ok"
    mock_response.text = "vless://ok"
    mock_get.side_effect = [Exception("Timeout"), Exception("Connection error"), mock_response]
    
    links = load_links_from_url("http://example.com/config.txt", retries=3)
    assert links == ["vless://ok"]
    assert mock_get.call_count == 3


def test_save_json():
    data = {"key": "value"}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        save_json(data, path)
        with open(path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == data
