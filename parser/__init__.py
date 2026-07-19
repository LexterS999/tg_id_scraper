"""
Telegram ID Parser package
"""

from .core import Parser
from .extractors import extract_telegram_ids
from .utils import load_links_from_file, load_links_from_url, load_links_from_url_stream
from .async_utils import fetch_all_links, fetch_links_from_url

__all__ = [
    'Parser',
    'extract_telegram_ids',
    'load_links_from_file',
    'load_links_from_url',
    'load_links_from_url_stream',
    'fetch_all_links',
    'fetch_links_from_url',
]
