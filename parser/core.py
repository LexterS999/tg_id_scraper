"""
Core parsing functionality for subscription links
"""

import re
import logging
import base64
import json
from typing import List, Dict, Optional, Any, Union
from functools import lru_cache
from urllib.parse import urlparse, parse_qs

from .utils import load_links_from_file, load_links_from_url
from .extractors import extract_telegram_ids
from .validators import is_valid_link_format, extract_clean_telegram_id
import config


logger = logging.getLogger(__name__)


class Parser:
    """Main parser class for subscription links"""
    
    def __init__(self):
        self.supported_protocols = config.SUPPORTED_PROTOCOLS
        
    def _decode_base64_params(self, content: str) -> Optional[Dict]:
        """Try to decode base64-encoded parameters (for vmess:// etc.)"""
        try:
            # Some protocols like vmess:// have base64 after the protocol
            # The format is usually: vmess://base64data
            # Remove protocol prefix
            if '://' in content:
                content = content.split('://', 1)[1]
            # Decode base64
            decoded = base64.b64decode(content, validate=True).decode('utf-8')
            # Try to parse as JSON
            data = json.loads(decoded)
            return data
        except json.JSONDecodeError as e:
            logger.debug(f"JSON decode error in base64: {e}")
            return None
        except Exception as e:
            logger.debug(f"Base64 decode error: {e}")
            return None
    
    def _extract_ids_from_dict_iter(self, obj: Dict[str, Any]) -> List[str]:
        """Iteratively extract Telegram IDs from all string values in a dict (avoid recursion)."""
        ids = []
        stack = [obj]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, value in current.items():
                    if isinstance(value, str):
                        found = extract_telegram_ids(value)
                        if found:
                            ids.extend(found)
                        cleaned = extract_clean_telegram_id(value)
                        if cleaned:
                            ids.append(cleaned)
                    elif isinstance(value, dict):
                        stack.append(value)
                    elif isinstance(value, list):
                        stack.extend(value)
            elif isinstance(current, list):
                stack.extend(current)
        return ids

    @lru_cache(maxsize=config.CACHE_MAX_SIZE)
    def _parse_link_cached(self, link: str) -> Optional[Dict]:
        """Cached version of parse_link."""
        return self.parse_link(link)

    def parse_link(self, link: str) -> Optional[Dict]:
        """
        Parse a single subscription link and extract its components.
        """
        if not link or not link.strip():
            return None
        
        link = link.strip()
        
        # --- Обработка прямых ссылок на Telegram-каналы ---
        if link.startswith('https://t.me/s/'):
            channel_name = link.replace('https://t.me/s/', '').split('?')[0].split('#')[0].strip('/')
            if channel_name and len(channel_name) >= 5:
                if not channel_name.startswith('@'):
                    channel_name = '@' + channel_name
                return {
                    'protocol': 'telegram_channel',
                    'raw': link,
                    'found_telegram_ids': [channel_name],
                    'comment': None,
                    'uuid': None,
                    'host': None,
                    'port': None,
                    'params': None
                }
            else:
                return None  # некорректная ссылка
        # ----------------------------------------------------
        
        # Validate link format
        if not is_valid_link_format(link):
            logger.debug(f"Invalid link format: {link[:50]}...")
            return None
        
        # Check protocol
        protocol = None
        for proto in self.supported_protocols:
            if link.startswith(proto):
                protocol = proto
                break
        
        if not protocol:
            logger.debug(f"Unsupported protocol in: {link[:50]}...")
            return None
        
        # Remove protocol prefix
        content = link[len(protocol):]
        
        # For vmess:// and possibly others, try to decode base64
        decoded_data = None
        if protocol in ['vmess://', 'vless://']:  # vless sometimes also has base64
            decoded_data = self._decode_base64_params(link)
            if decoded_data:
                logger.debug(f"Base64 decoded data: {decoded_data}")
        
        # Split into main part and comment
        comment = None
        main_part = content
        for delimiter in config.COMMENT_DELIMITERS:
            if delimiter in content:
                parts = content.split(delimiter, 1)
                main_part = parts[0]
                comment = parts[1] if len(parts) > 1 else None
                break
        
        result = {
            'protocol': protocol[:-3],
            'raw': link,
            'comment': comment
        }
        
        # Parse main part (UUID@host:port?params)
        try:
            parsed = self._parse_link_parts(main_part)
            result.update(parsed)
        except Exception as e:
            logger.debug(f"Error parsing link: {e}")
            # Return partial result anyway
            result['parse_error'] = str(e)
            return result
        
        # If we have decoded data, merge it
        if decoded_data:
            # Merge decoded data into result, but don't overwrite existing keys
            for key, value in decoded_data.items():
                if key not in result or not result[key]:
                    result[key] = value
        
        # --- SMART EXTRACTION ---
        # 1. Extract from comment
        all_ids = []
        if comment:
            all_ids.extend(extract_telegram_ids(comment))
            cleaned = extract_clean_telegram_id(comment)
            if cleaned:
                all_ids.append(cleaned)
        
        # 2. Extract from all string values in the result dict (including host, params, etc.)
        # We'll traverse the result and extract from any string value
        for key, value in result.items():
            if isinstance(value, str):
                ids = extract_telegram_ids(value)
                if ids:
                    all_ids.extend(ids)
                cleaned = extract_clean_telegram_id(value)
                if cleaned:
                    all_ids.append(cleaned)
            elif isinstance(value, dict):
                ids = self._extract_ids_from_dict_iter(value)
                all_ids.extend(ids)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        ids = extract_telegram_ids(item)
                        if ids:
                            all_ids.extend(ids)
                        cleaned = extract_clean_telegram_id(item)
                        if cleaned:
                            all_ids.append(cleaned)
                    elif isinstance(item, dict):
                        ids = self._extract_ids_from_dict_iter(item)
                        all_ids.extend(ids)
        
        # Remove duplicates and keep only valid @username
        valid_ids = []
        seen = set()
        for id_ in all_ids:
            if id_ not in seen and id_.startswith('@') and len(id_) >= 6:
                # Additional validation: must match pattern
                if re.match(config.TELEGRAM_ID_PATTERN, id_):
                    valid_ids.append(id_)
                    seen.add(id_)
        
        if valid_ids:
            result['found_telegram_ids'] = valid_ids
        
        return result
    
    def _parse_link_parts(self, main_part: str) -> Dict:
        """Parse core part (UUID@host:port?params) into dict."""
        result = {}
        if '@' in main_part:
            uuid_part, rest = main_part.split('@', 1)
            result['uuid'] = uuid_part
        else:
            rest = main_part
        
        if '?' in rest:
            host_port, params_str = rest.split('?', 1)
            result['params'] = params_str
            try:
                params_dict = parse_qs(params_str)
                for key, values in params_dict.items():
                    if values:
                        result[key] = values[0] if len(values) == 1 else values
            except Exception:
                pass
        else:
            host_port = rest
        
        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
            result['host'] = host
            if port.isdigit():
                result['port'] = int(port)
        else:
            result['host'] = host_port
        
        return result
    
    def parse_links(self, links: List[str]) -> List[Dict]:
        results = []
        for link in links:
            if link and link.strip():
                parsed = self.parse_link(link)
                if parsed:
                    results.append(parsed)
        logger.info(f"Successfully parsed {len(results)} out of {len(links)} links")
        return results
    
    def extract_all_telegram_ids(self, links: List[str]) -> List[str]:
        all_ids = []
        results = self.parse_links(links)
        for result in results:
            if 'found_telegram_ids' in result:
                all_ids.extend(result['found_telegram_ids'])
        return all_ids
