"""
Integration tests for the full parsing pipeline
"""

import pytest
import tempfile
import os
from unittest.mock import patch, Mock

from parser.core import Parser
from parser.utils import load_links_from_url
from main import collect_links_from_urls, save_results


@patch('main.load_links_from_url')
def test_collect_links_from_urls(mock_load):
    mock_load.side_effect = [
        ["vless://a@h:443#@id1"],
        ["vless://b@h:443#@id2"],
        Exception("Network error")
    ]
    urls = ["http://a.com", "http://b.com", "http://c.com"]
    logger = Mock()
    links = collect_links_from_urls(urls, logger)
    assert links == ["vless://a@h:443#@id1", "vless://b@h:443#@id2"]
    # Проверяем, что ошибка залогирована
    logger.error.assert_called_once()


@patch('main.os.makedirs')
def test_save_results(mock_makedirs):
    with tempfile.TemporaryDirectory() as tmpdir:
        ids = ["@id1", "@id2", "@id1"]
        full_data = [{"found_telegram_ids": ["@id1"]}, {"found_telegram_ids": ["@id2"]}]
        logger = Mock()
        save_results(ids, tmpdir, "both", full_data, logger)
        
        # Проверяем создание файлов
        py_path = os.path.join(tmpdir, "telegram_ids.py")
        txt_path = os.path.join(tmpdir, "telegram_ids.txt")
        full_json_path = os.path.join(tmpdir, "parsed_configs.json")
        
        assert os.path.exists(py_path)
        assert os.path.exists(txt_path)
        assert os.path.exists(full_json_path)
        
        with open(py_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'SOURCE_URLS = [' in content
            assert '"https://t.me/s/id1"' in content
            assert '"https://t.me/s/id2"' in content
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
            assert set(lines) == {"@id1", "@id2"}
