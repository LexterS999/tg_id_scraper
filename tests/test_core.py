"""
Unit tests for core parsing functionality
"""

import pytest
from parser.core import Parser


@pytest.fixture
def parser():
    return Parser()


def test_parse_vless_with_comment(parser):
    link = 'vless://03707fb7-0990-440f-88f6-b0e0f7242a38@104.16.75.234:443?path=/&security=tls#@iguanaVPN6'
    result = parser.parse_link(link)
    
    assert result is not None
    assert result['protocol'] == 'vless'
    assert result['uuid'] == '03707fb7-0990-440f-88f6-b0e0f7242a38'
    assert result['host'] == '104.16.75.234'
    assert result['port'] == 443
    assert result['comment'] == '@iguanaVPN6'
    assert '@iguanaVPN6' in result.get('found_telegram_ids', [])


def test_parse_vless_with_multiple_ids(parser):
    link = 'vless://03fcc618-b93d-6796-6aed-8a38c975d581@186.190.211.188:443?security=tls#🇬🇧 Join+Telegram:@Farah_VPN 🇬🇧'
    result = parser.parse_link(link)
    
    assert result is not None
    assert 'found_telegram_ids' in result
    assert '@Farah_VPN' in result['found_telegram_ids']


def test_parse_vless_with_host_id(parser):
    link = 'vless://03755506-780d-4809-93c5-7d9caf6549f7@cloud.pointspeed.sbs:443?security=tls#🇬🇧 • 🚀𝗙𝗿𝗲𝗲 𝗦𝗽𝗲𝗰𝗶𝗮𝗹 | @NewsDarya'
    result = parser.parse_link(link)
    
    assert result is not None
    assert result['comment'] == '🇬🇧 • 🚀𝗙𝗿𝗲𝗲 𝗦𝗽𝗲𝗰𝗶𝗮𝗹 | @NewsDarya'
    assert '@NewsDarya' in result.get('found_telegram_ids', [])


def test_parse_unsupported_protocol(parser):
    link = 'http://example.com/config'
    result = parser.parse_link(link)
    assert result is None


def test_parse_batch(parser):
    links = [
        'vless://uuid1@host1:443#@id1',
        'vless://uuid2@host2:443#@id2',
    ]
    results = parser.parse_links(links)
    assert len(results) == 2
    assert results[0]['uuid'] == 'uuid1'
    assert results[1]['uuid'] == 'uuid2'


def test_extract_all_ids(parser):
    links = [
        'vless://a@h:443#@id1',
        'vless://b@h:443#@id2',
        'vless://c@h:443#No id here',
    ]
    ids = parser.extract_all_telegram_ids(links)
    assert len(ids) == 2
    assert '@id1' in ids
    assert '@id2' in ids
