"""
Extractor functions for Telegram IDs
"""

import re
from typing import List, Optional

import config

# Compile regex once for performance
TELEGRAM_ID_RE = re.compile(
    r'(?<![a-zA-Z0-9_])@[a-zA-Z0-9_]{5,32}(?![a-zA-Z0-9_])|@[a-zA-Z0-9_]{5,32}',
    re.IGNORECASE
)

def extract_telegram_ids(text: Optional[str]) -> List[str]:
    """
    Extract all Telegram IDs (@username) from a text string.
    Uses a single regex pass and removes duplicates while preserving order.
    """
    if not text or not isinstance(text, str):
        return []
    
    matches = TELEGRAM_ID_RE.findall(text)
    # Remove duplicates preserving order
    return list(dict.fromkeys(matches))

def extract_telegram_ids_from_comment(comment: str) -> List[str]:
    """Extract Telegram IDs specifically from comment sections."""
    return extract_telegram_ids(comment)

def extract_telegram_ids_from_url(url: str) -> List[str]:
    """Extract Telegram IDs from URL parameters and fragments."""
    return extract_telegram_ids(url)

def extract_telegram_ids_from_all_sources(text: str) -> List[str]:
    """
    Extract Telegram IDs from all possible sources in a string.
    This combines multiple extraction strategies:
    1. Direct @username matches
    2. Matches in comments
    3. Matches in URL parameters
    """
    ids = []
    
    # Direct extraction
    ids.extend(extract_telegram_ids(text))
    
    # Try to split by common delimiters to handle multiple sections
    for delimiter in config.COMMENT_DELIMITERS:
        if delimiter in text:
            parts = text.split(delimiter)
            for part in parts:
                ids.extend(extract_telegram_ids(part))
    
    # Remove duplicates
    return list(dict.fromkeys(ids))

def validate_telegram_id(id_str: str) -> bool:
    """
    Validate if a string is a valid Telegram ID format.
    """
    pattern = r'^@[a-zA-Z0-9_]{5,32}$'
    return bool(re.match(pattern, id_str))

def clean_telegram_id(id_str: str) -> Optional[str]:
    """
    Clean and validate a Telegram ID.
    """
    if not id_str:
        return None
    
    cleaned = id_str.strip()
    
    if cleaned and not cleaned.startswith('@'):
        if re.match(r'^[a-zA-Z0-9_]{5,32}$', cleaned):
            cleaned = '@' + cleaned
        else:
            return None
    
    if validate_telegram_id(cleaned):
        return cleaned
    
    return None
