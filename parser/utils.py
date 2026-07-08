"""
Utility functions for Telegram ID Parser
"""

import os
import json
import logging
from typing import List, Optional
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)


def load_links_from_file(file_path: str) -> List[str]:
    """
    Load subscription links from a local file (each line is a config string)
    """
    links = []
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    links.append(line)
    except Exception as e:
        raise Exception(f"Error reading file {file_path}: {e}")
    logger.debug(f"Loaded {len(links)} links from {file_path}")
    return links


def load_links_from_url(url: str, timeout: int = 30, retries: int = 3) -> List[str]:
    """
    Download a file from URL with automatic retries.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        
        if len(response.content) > config.MAX_DOWNLOAD_SIZE:
            raise Exception(f"File too large: {len(response.content)} bytes")
        
        links = []
        for line in response.text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                links.append(line)
        logger.debug(f"Downloaded {len(links)} config lines from {url}")
        return links
    except requests.RequestException as e:
        raise Exception(f"Error downloading URL {url}: {e}")


def save_json(data, file_path: str, indent: int = 2):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
