"""
Validation utilities for subscription links
"""

import re
from typing import Optional
import config


def is_valid_protocol(link: str) -> bool:
    """Check if link starts with a supported protocol."""
    if not link or not isinstance(link, str):
        return False
    for proto in config.SUPPORTED_PROTOCOLS:
        if link.startswith(proto):
            return True
    return False


def is_valid_link_format(link: str) -> bool:
    """
    Basic validation: must contain '@' and ':' (host:port pattern).
    This is a simple sanity check.
    """
    if not is_valid_protocol(link):
        return False
    # Remove protocol prefix
    content = link.split('://', 1)[1] if '://' in link else link
    # Must contain '@' and ':'
    if '@' not in content or ':' not in content:
        return False
    # Optional: check UUID format (for vless/vmess etc.) - too complex, skip for now
    return True


def extract_clean_telegram_id(text: str) -> Optional[str]:
    """
    Extract a valid @username from a string that may contain extra text.
    Example: "@channel (канал)" -> "@channel"
    """
    if not text:
        return None
    # Try to find pattern in the whole text
    matches = re.findall(config.TELEGRAM_ID_PATTERN, text, re.IGNORECASE)
    if matches:
        # Return the first valid match
        return matches[0]
    # Try strict pattern
    matches_strict = re.findall(config.TELEGRAM_ID_PATTERN_STRICT, text, re.IGNORECASE)
    if matches_strict:
        return matches_strict[0]
    return None
