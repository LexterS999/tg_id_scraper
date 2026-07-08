"""
Utility functions for Telegram ID Parser
"""

import os
import json
import logging
import time
from typing import List, Optional, Dict, Any
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)

# Simple in-memory cache (TTL based)
_cache = {}
_cache_timestamps = {}


def load_links_from_file(file_path: str) -> List[str]:
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


def load_links_from_url(url: str, timeout: int = 30, retries: int = 3, use_cache: bool = True) -> List[str]:
    """
    Download a file from URL with automatic retries and optional caching.
    """
    # Check cache
    if use_cache and url in _cache:
        cached_time = _cache_timestamps.get(url, 0)
        if time.time() - cached_time < config.CACHE_TTL:
            logger.debug(f"Using cached data for {url}")
            return _cache[url]
    
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
        
        # Update cache
        if use_cache:
            _cache[url] = links
            _cache_timestamps[url] = time.time()
        
        logger.debug(f"Downloaded {len(links)} config lines from {url}")
        return links
    except requests.RequestException as e:
        raise Exception(f"Error downloading URL {url}: {e}")


def save_json(data, file_path: str, indent: int = 2):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_previous_ids(file_path: str) -> List[str]:
    """Load previously saved Telegram IDs from a file."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            # Simple TXT format: one ID per line
            return [line.strip() for line in content.splitlines() if line.strip()]
    except Exception as e:
        logger.warning(f"Could not load previous IDs from {file_path}: {e}")
        return []


def save_intermediate_results(ids: List[str], file_path: str):
    """Save intermediate results to a temporary file (for resilience)."""
    temp_file = file_path + ".tmp"
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            for id_ in ids:
                f.write(f"{id_}\n")
        os.replace(temp_file, file_path)
    except Exception as e:
        logger.warning(f"Failed to save intermediate results: {e}")
