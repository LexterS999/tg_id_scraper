"""
Extractor functions for Telegram IDs
"""

import re
from typing import List, Optional

import config


def extract_telegram_ids(text: Optional[str]) -> List[str]:
    """
    Extract all Telegram IDs (@username) from a text string
    
    Args:
        text: String to search for Telegram IDs
        
    Returns:
        List of found Telegram IDs (including @ symbol)
    """
    if not text or not isinstance(text, str):
        return []
    
    # Use both patterns: strict and lenient
    ids = []
    
    # Strict pattern: word boundaries
    strict_matches = re.findall(
        config.TELEGRAM_ID_PATTERN_STRICT,
        text,
        re.IGNORECASE
    )
    ids.extend(strict_matches)
    
    # Lenient pattern: find all possible IDs
    lenient_matches = re.findall(
        config.TELEGRAM_ID_PATTERN,
        text,
        re.IGNORECASE
    )
    ids.extend(lenient_matches)
    
    # Remove duplicates while preserving order
    unique_ids = []
    seen = set()
    for id_ in ids:
        if id_ not in seen:
            unique_ids.append(id_)
            seen.add(id_)
    
    return unique_ids


def extract_telegram_ids_from_comment(comment: str) -> List[str]:
    """
    Extract Telegram IDs specifically from comment sections
    
    Args:
        comment: Comment string (e.g., "#@telegram_id")
        
    Returns:
        List of extracted Telegram IDs
    """
    return extract_telegram_ids(comment)


def extract_telegram_ids_from_url(url: str) -> List[str]:
    """
    Extract Telegram IDs from URL parameters and fragments
    
    Args:
        url: Full URL or link with parameters
        
    Returns:
        List of extracted Telegram IDs
    """
    return extract_telegram_ids(url)


def extract_telegram_ids_from_all_sources(text: str) -> List[str]:
    """
    Extract Telegram IDs from all possible sources in a string
    
    This combines multiple extraction strategies:
    1. Direct @username matches
    2. Matches in comments
    3. Matches in URL parameters
    
    Args:
        text: Full text content
        
    Returns:
        List of extracted Telegram IDs
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
    unique_ids = []
    seen = set()
    for id_ in ids:
        if id_ not in seen:
            unique_ids.append(id_)
            seen.add(id_)
    
    return unique_ids


def validate_telegram_id(id_str: str) -> bool:
    """
    Validate if a string is a valid Telegram ID format
    
    Args:
        id_str: String to validate (including @ symbol)
        
    Returns:
        True if valid format, False otherwise
    """
    pattern = r'^@[a-zA-Z0-9_]{5,32}$'
    return bool(re.match(pattern, id_str))


def clean_telegram_id(id_str: str) -> Optional[str]:
    """
    Clean and validate a Telegram ID
    
    Args:
        id_str: Raw ID string
        
    Returns:
        Cleaned ID with @ symbol if valid, None otherwise
    """
    if not id_str:
        return None
    
    # Remove whitespace
    cleaned = id_str.strip()
    
    # Ensure @ at the beginning if not present
    if cleaned and not cleaned.startswith('@'):
        # Check if it's a valid ID without @
        if re.match(r'^[a-zA-Z0-9_]{5,32}$', cleaned):
            cleaned = '@' + cleaned
        else:
            return None
    
    if validate_telegram_id(cleaned):
        return cleaned
    
    return None
