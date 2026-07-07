"""
Unit tests for extractor functions
"""

import pytest
from parser.extractors import (
    extract_telegram_ids,
    extract_telegram_ids_from_comment,
    validate_telegram_id,
    clean_telegram_id
)


def test_extract_basic():
    text = "Join @telegram_channel for updates"
    ids = extract_telegram_ids(text)
    assert len(ids) == 1
    assert ids[0] == '@telegram_channel'


def test_extract_multiple():
    text = "Follow @channel1 and @channel2_news for info"
    ids = extract_telegram_ids(text)
    assert len(ids) == 2
    assert '@channel1' in ids
    assert '@channel2_news' in ids


def test_extract_with_comment():
    comment = "#@iguanaVPN6 and @other_channel"
    ids = extract_telegram_ids_from_comment(comment)
    assert len(ids) == 2
    assert '@iguanaVPN6' in ids
    assert '@other_channel' in ids


def test_extract_from_url_params():
    text = "host=example.com&sni=@telegram_id&domain=@another"
    ids = extract_telegram_ids(text)
    assert len(ids) == 2
    assert '@telegram_id' in ids
    assert '@another' in ids


def test_extract_case_sensitive():
    text = "@TelegramChannel and @telegramchannel"
    ids = extract_telegram_ids(text)
    # Should return both as they are (case sensitive matching)
    assert len(ids) == 2
    assert '@TelegramChannel' in ids
    assert '@telegramchannel' in ids


def test_extract_no_ids():
    text = "No Telegram IDs here"
    ids = extract_telegram_ids(text)
    assert len(ids) == 0


def test_validate_valid_ids():
    assert validate_telegram_id('@valid_channel') is True
    assert validate_telegram_id('@short') is False  # < 5 chars
    assert validate_telegram_id('@way_too_long_channel_name') is False  # > 32 chars


def test_validate_invalid_ids():
    assert validate_telegram_id('invalid') is False  # No @
    assert validate_telegram_id('@invalid!') is False  # Special char
    assert validate_telegram_id('') is False


def test_clean_telegram_id():
    assert clean_telegram_id('valid_channel') == '@valid_channel'
    assert clean_telegram_id('@valid_channel') == '@valid_channel'
    assert clean_telegram_id('  @valid_channel  ') == '@valid_channel'
    assert clean_telegram_id('invalid!') is None
    assert clean_telegram_id('') is None


def test_extract_with_duplicates():
    text = "@channel1 and @channel1 again"
    ids = extract_telegram_ids(text)
    assert len(ids) == 1  # Should remove duplicates
    assert ids[0] == '@channel1'
