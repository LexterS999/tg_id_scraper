"""
Utility functions for Telegram ID Parser
"""

import os
import json
import logging
from typing import List, Optional
from pathlib import Path

import requests


logger = logging.getLogger(__name__)


def load_links_from_file(file_path: str) -> List[str]:
    """
    Load subscription links from a local file
    
    Args:
        file_path: Path to the file
        
    Returns:
        List of links (one per line)
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
    Download and load subscription links from a URL
    
    Args:
        url: URL to download
        timeout: Request timeout in seconds
        
    Returns:
        List of links (one per line)
    """
    links = []
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if 'text' not in content_type and 'application' not in content_type:
            logger.warning(f"Unexpected content type: {content_type}")
        
        # Check file size
        content_length = len(response.content)
        if content_length > config.MAX_DOWNLOAD_SIZE:
            raise Exception(f"File too large: {content_length} bytes (max {config.MAX_DOWNLOAD_SIZE})")
        
        # Decode and parse
        content = response.text
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                links.append(line)
                
    except requests.RequestException as e:
        raise Exception(f"Error downloading URL {url}: {e}")
    
    logger.debug(f"Downloaded {len(links)} links from {url}")
    return links


def save_json(data, file_path: str, indent: int = 2):
    """
    Save data to a JSON file
    
    Args:
        data: Data to save
        file_path: Path to output file
        indent: JSON indentation
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def parse_protocol(link: str) -> Optional[str]:
    """
    Extract protocol from a link
    
    Args:
        link: Full link
        
    Returns:
        Protocol string (e.g., 'vless') or None
    """
    for proto in config.SUPPORTED_PROTOCOLS:
        if link.startswith(proto):
            return proto[:-3]  # Remove ://
    return None


def safe_filename(filename: str) -> str:
    """
    Convert string to safe filename
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    return ''.join(c for c in filename if c.isalnum() or c in '._- ').strip()


def create_output_directory(directory: str) -> str:
    """
    Create output directory if it doesn't exist
    
    Args:
        directory: Directory path
        
    Returns:
        Path to created directory
    """
    Path(directory).mkdir(parents=True, exist_ok=True)
    return directory
