"""
Asynchronous utilities for fetching links from URLs.
"""

import asyncio
import aiohttp
from typing import List, Optional
import logging

import config

logger = logging.getLogger(__name__)

async def fetch_links_from_url(session: aiohttp.ClientSession, url: str, max_lines: int = config.MAX_LINES) -> List[str]:
    """Fetch links from a single URL asynchronously with streaming."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            response.raise_for_status()
            # Check content length if available
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > config.MAX_DOWNLOAD_SIZE:
                logger.warning(f"File too large ({content_length} bytes) for {url}, skipping")
                return []
            links = []
            i = 0
            async for line in response.content:
                if i >= max_lines:
                    logger.warning(f"Reached max lines limit ({max_lines}) for {url}")
                    break
                i += 1
                line = line.decode('utf-8').strip()
                if line and not line.startswith('#'):
                    links.append(line)
            return links
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return []

async def fetch_all_links(urls: List[str], max_workers: int = 10) -> List[str]:
    """Fetch links from multiple URLs asynchronously with concurrency limit."""
    connector = aiohttp.TCPConnector(limit=max_workers, limit_per_host=5)
    headers = {'User-Agent': config.get_random_user_agent()}
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [fetch_links_from_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_links = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed: {result}")
                continue
            all_links.extend(result)
        return all_links
