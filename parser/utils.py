"""
Utility functions for Telegram ID Parser
"""

import os
import json
import logging
from typing import List, Optional
from pathlib import Path

import requests

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


def load_links_from_url(url: str, timeout: int = 30) -> List[str]:
    """
    Download a file from URL and extract config lines (one per line)
    """
    links = []
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # Check file size
        if len(response.content) > config.MAX_DOWNLOAD_SIZE:
            raise Exception(f"File too large: {len(response.content)} bytes")
        
        content = response.text
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                links.append(line)
    except requests.RequestException as e:
        raise Exception(f"Error downloading URL {url}: {e}")
    
    logger.debug(f"Downloaded {len(links)} config lines from {url}")
    return links


def save_json(data, file_path: str, indent: int = 2):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
