"""
Utility functions for Telegram ID Parser
"""

import os
import json
import logging
import time
import random
from typing import List, Optional, Dict, Any
from pathlib import Path
from functools import lru_cache
from threading import Lock

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)

# Rate limiting
_last_request_time = 0
_request_lock = Lock()

def _rate_limited_request(url: str, min_interval: float = 1.0, **kwargs) -> requests.Response:
    """Make a request with rate limiting (minimum interval between requests)."""
    global _last_request_time
    with _request_lock:
        elapsed = time.time() - _last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        _last_request_time = time.time()
    # Rotate User-Agent
    kwargs.setdefault('headers', {})
    kwargs['headers']['User-Agent'] = config.get_random_user_agent()
    return requests.get(url, **kwargs)

def load_links_from_file(file_path: str) -> List[str]:
    links = []
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    try:
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    links.append(line)
    except Exception as e:
        raise Exception(f"Error reading file {file_path}: {e}")
    logger.debug(f"Loaded {len(links)} links from {file_path}")
    return links

@lru_cache(maxsize=config.CACHE_MAX_SIZE)
def load_links_from_url(url: str, timeout: int = 30, retries: int = 3, use_cache: bool = True) -> List[str]:
    """
    Download a file from URL with automatic retries and caching.
    Cached using lru_cache.
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
        # Check Content-Length before full download (if available)
        head_resp = _rate_limited_request(url, timeout=timeout, stream=True, method='HEAD')
        if head_resp.status_code == 200:
            content_length = head_resp.headers.get('Content-Length')
            if content_length and int(content_length) > config.MAX_DOWNLOAD_SIZE:
                raise Exception(f"File too large: {content_length} bytes (max {config.MAX_DOWNLOAD_SIZE})")
        
        response = _rate_limited_request(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Stream reading with limit
        links = []
        for i, line in enumerate(response.iter_lines(decode_unicode=True)):
            if i >= config.MAX_LINES:
                logger.warning(f"Reached max lines limit ({config.MAX_LINES}) for {url}")
                break
            line = line.strip()
            if line and not line.startswith('#'):
                links.append(line)
        
        logger.debug(f"Downloaded {len(links)} config lines from {url}")
        return links
    except requests.RequestException as e:
        raise Exception(f"Error downloading URL {url}: {e}")

def load_links_from_url_stream(url: str, max_lines: int = config.MAX_LINES, timeout: int = 30) -> List[str]:
    """Load only first N lines from a URL without caching (streaming)."""
    session = requests.Session()
    try:
        response = _rate_limited_request(url, timeout=timeout, stream=True)
        response.raise_for_status()
        links = []
        for i, line in enumerate(response.iter_lines(decode_unicode=True)):
            if i >= max_lines:
                break
            line = line.strip()
            if line and not line.startswith('#'):
                links.append(line)
        return links
    except requests.RequestException as e:
        raise Exception(f"Error streaming URL {url}: {e}")

def save_json(data, file_path: str, indent: int = 2):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

def load_previous_ids(file_path: str) -> List[str]:
    """Load previously saved Telegram IDs from a file."""
    path = Path(file_path)
    if not path.exists():
        return []
    try:
        with path.open('r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            return [line.strip() for line in content.splitlines() if line.strip()]
    except Exception as e:
        logger.warning(f"Could not load previous IDs from {file_path}: {e}")
        return []

def save_intermediate_results(ids: List[str], file_path: str):
    """Save intermediate results to a temporary file (for resilience)."""
    path = Path(file_path)
    temp_file = path.with_suffix(path.suffix + ".tmp")
    try:
        with temp_file.open('w', encoding='utf-8') as f:
            for id_ in ids:
                f.write(f"{id_}\n")
        temp_file.rename(path)
    except Exception as e:
        logger.warning(f"Failed to save intermediate results: {e}")

def save_metadata(metadata: Dict[str, Any], output_dir: str):
    """Save run metadata to a JSON file."""
    path = Path(output_dir) / config.OUTPUT_METADATA_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved metadata to {path}")
