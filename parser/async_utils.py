"""
Asynchronous utilities for fetching links from URLs.
"""

import asyncio
import aiohttp
from typing import List, Optional
import logging

import config

logger = logging.getLogger(__name__)

async def fetch_links_from_url(
    session: aiohttp.ClientSession,
    url: str,
    max_lines: int = config.MAX_LINES,
    max_size: int = config.MAX_DOWNLOAD_SIZE,
    retries: int = config.DEFAULT_RETRIES
) -> List[str]:
    """
    Fetch links from a single URL asynchronously with streaming,
    error handling, and retries.
    """
    for attempt in range(retries + 1):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                # Проверяем статус ответа
                if response.status == 404:
                    logger.error(f"URL not found (404): {url}")
                    return []
                elif response.status == 400:
                    logger.error(f"Bad request (400) for {url} — possibly too large or malformed")
                    # Пробуем прочитать с ограничением
                    return await _read_with_limit(response, max_lines, max_size)
                elif response.status != 200:
                    logger.error(f"HTTP {response.status} for {url}")
                    return []

                # Проверяем Content-Length
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > max_size:
                    logger.warning(f"File too large ({content_length} bytes) for {url}, skipping")
                    return []

                return await _read_stream(response, max_lines)

        except aiohttp.ClientError as e:
            logger.warning(f"Attempt {attempt+1}/{retries+1} failed for {url}: {e}")
            if attempt == retries:
                logger.error(f"All retries exhausted for {url}")
                return []
            await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return []

    return []


async def _read_stream(response: aiohttp.ClientResponse, max_lines: int) -> List[str]:
    """Read lines from a stream with a limit."""
    links = []
    i = 0
    async for line in response.content:
        if i >= max_lines:
            logger.warning(f"Reached max lines limit ({max_lines})")
            break
        i += 1
        line = line.decode('utf-8', errors='ignore').strip()
        if line and not line.startswith('#'):
            links.append(line)
    return links


async def _read_with_limit(
    response: aiohttp.ClientResponse,
    max_lines: int,
    max_size: int
) -> List[str]:
    """
    Read a response with both line and size limits.
    Used for 400 responses where size is unknown.
    """
    links = []
    i = 0
    bytes_read = 0
    async for chunk in response.content.iter_chunks():
        if i >= max_lines:
            break
        if bytes_read > max_size:
            logger.warning(f"Reached size limit ({max_size} bytes) during read")
            break
        # chunk is a tuple (data, end_of_chunk)
        data = chunk[0]
        bytes_read += len(data)
        lines = data.decode('utf-8', errors='ignore').splitlines()
        for line in lines:
            if i >= max_lines:
                break
            line = line.strip()
            if line and not line.startswith('#'):
                links.append(line)
            i += 1
    return links


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
