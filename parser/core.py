"""
Core parsing functionality for subscription links
"""

import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

from .utils import parse_protocol
from .extractors import extract_telegram_ids
import config


logger = logging.getLogger(__name__)


class Parser:
    """Main parser class for subscription links"""
    
    def __init__(self):
        self.supported_protocols = config.SUPPORTED_PROTOCOLS
        
    def parse_link(self, link: str) -> Optional[Dict]:
        """
        Parse a single subscription link and extract its components
        
        Args:
            link: Full subscription link (vless://...)
            
        Returns:
            Dictionary with parsed components or None if parsing fails
        """
        if not link or not link.strip():
            return None
        
        link = link.strip()
        
        # Check if it's a supported protocol
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
        
        # Split into main part and comment (if exists)
        comment = None
        main_part = content
        
        # Look for comment after # or other delimiters
        for delimiter in config.COMMENT_DELIMITERS:
            if delimiter in content:
                parts = content.split(delimiter, 1)
                main_part = parts[0]
                comment = parts[1] if len(parts) > 1 else None
                break
        
        # Parse the main part
        result = {
            'protocol': protocol[:-3],  # Remove ://
            'raw': link,
            'comment': comment
        }
        
        # Parse UUID@host:port?params
        try:
            # Extract UUID and host part
            if '@' in main_part:
                uuid_part, rest = main_part.split('@', 1)
                result['uuid'] = uuid_part
                
                # Parse host:port and parameters
                if '?' in rest:
                    host_port, params_str = rest.split('?', 1)
                    result['params'] = params_str
                    # Parse query parameters
                    try:
                        params_dict = parse_qs(params_str)
                        for key, values in params_dict.items():
                            if values:
                                result[key] = values[0] if len(values) == 1 else values
                    except Exception as e:
                        logger.debug(f"Error parsing params: {e}")
                else:
                    host_port = rest
                
                # Parse host and port
                if ':' in host_port:
                    host, port = host_port.rsplit(':', 1)
                    result['host'] = host
                    if port.isdigit():
                        result['port'] = int(port)
                else:
                    result['host'] = host_port
                    
            else:
                # No UUID, just host:port?params
                if '?' in main_part:
                    host_port, params_str = main_part.split('?', 1)
                    result['params'] = params_str
                else:
                    host_port = main_part
                    
                if ':' in host_port:
                    host, port = host_port.rsplit(':', 1)
                    result['host'] = host
                    if port.isdigit():
                        result['port'] = int(port)
                else:
                    result['host'] = host_port
                    
        except Exception as e:
            logger.debug(f"Error parsing link: {e}")
            return None
        
        # Also extract IDs from host and comment
        all_ids = []
        if comment:
            all_ids.extend(extract_telegram_ids(comment))
        
        # Check other fields for IDs
        for field in ['host', 'sni', 'server', 'domain']:
            if field in result and result[field]:
                all_ids.extend(extract_telegram_ids(str(result[field])))
        
        if all_ids:
            result['found_telegram_ids'] = list(set(all_ids))
        
        return result
    
    def parse_links(self, links: List[str]) -> List[Dict]:
        """
        Parse multiple links
        
        Args:
            links: List of subscription links
            
        Returns:
            List of parsed dictionaries
        """
        results = []
        for link in links:
            if link and link.strip():
                parsed = self.parse_link(link)
                if parsed:
                    results.append(parsed)
        
        logger.info(f"Successfully parsed {len(results)} out of {len(links)} links")
        return results
    
    def extract_all_telegram_ids(self, links: List[str]) -> List[str]:
        """
        Extract all Telegram IDs from a list of links
        
        Args:
            links: List of subscription links
            
        Returns:
            List of extracted Telegram IDs (with duplicates)
        """
        all_ids = []
        results = self.parse_links(links)
        
        for result in results:
            if 'found_telegram_ids' in result:
                all_ids.extend(result['found_telegram_ids'])
                
            # Also extract from comment field if present
            if 'comment' in result and result['comment']:
                ids = extract_telegram_ids(result['comment'])
                all_ids.extend(ids)
        
        return all_ids
