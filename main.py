#!/usr/bin/env python3
"""
Main entry point for Telegram ID Parser
"""

import os
import sys
import argparse
import logging
import json
import asyncio
from typing import List, Optional, Set
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from parser.core import Parser
from parser.utils import (
    load_links_from_file,
    load_links_from_url,
    load_previous_ids,
    save_intermediate_results,
    save_metadata
)
from parser.async_utils import fetch_all_links
from parser.extractors import extract_telegram_ids
import config


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    # Use rotating file handler
    from logging.handlers import RotatingFileHandler
    
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler with rotation
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract Telegram IDs from subscription links",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input-file input.txt
  python main.py -i subscriptions.txt -o results
  python main.py -u https://example.com/configs.txt -o output -v
  python main.py -i input.txt --output-format jsonl
        """
    )
    
    parser.add_argument(
        '-i', '--input-file',
        type=str,
        help="Path to text file containing list of URLs (one per line) to fetch configs from"
    )
    parser.add_argument(
        '-u', '--url',
        type=str,
        help="Single URL to download and parse (overrides --input-file)"
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=config.DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {config.DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['json', 'txt', 'both', 'jsonl'],
        default=config.DEFAULT_OUTPUT_FORMAT,
        help=f"Output format: json, txt, both, or jsonl (default: {config.DEFAULT_OUTPUT_FORMAT})"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose output"
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=config.DEFAULT_WORKERS,
        help=f"Number of parallel workers for downloading (default: {config.DEFAULT_WORKERS})"
    )
    parser.add_argument(
        '--no-incremental',
        action='store_true',
        help="Disable incremental update (always overwrite output)"
    )
    parser.add_argument(
        '--async',
        dest='async_mode',
        action='store_true',
        help="Use asynchronous downloading (aiohttp) for better performance"
    )
    return parser.parse_args()


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS/file URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https', 'file')
    except Exception:
        return False


def collect_links_from_urls_sync(url_list: List[str], logger: logging.Logger, max_workers: int = 10) -> List[str]:
    """Synchronous collection using ThreadPoolExecutor."""
    all_links = []
    urls = [u.strip() for u in url_list if u.strip() and not u.startswith('#')]
    if not urls:
        return all_links

    # Validate URLs
    valid_urls = [u for u in urls if is_valid_url(u)]
    invalid_urls = [u for u in urls if not is_valid_url(u)]
    if invalid_urls:
        logger.warning(f"Skipping invalid URLs: {invalid_urls}")
    urls = valid_urls

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(load_links_from_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                links = future.result()
                all_links.extend(links)
                logger.debug(f"Got {len(links)} config lines from {url}")
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
    return all_links


async def collect_links_from_urls_async(url_list: List[str], logger: logging.Logger, max_workers: int = 10) -> List[str]:
    """Asynchronous collection using aiohttp."""
    urls = [u.strip() for u in url_list if u.strip() and not u.startswith('#')]
    if not urls:
        return []
    valid_urls = [u for u in urls if is_valid_url(u)]
    invalid_urls = [u for u in urls if not is_valid_url(u)]
    if invalid_urls:
        logger.warning(f"Skipping invalid URLs: {invalid_urls}")
    urls = valid_urls
    return await fetch_all_links(urls, max_workers=max_workers)


def save_results(
    telegram_ids: List[str],
    output_dir: str,
    output_format: str,
    full_data: Optional[List[dict]] = None,
    logger: logging.Logger = None,
    incremental: bool = True,
    previous_ids: List[str] = None,
    metadata: Optional[dict] = None
):
    """Save extracted Telegram IDs to files, with incremental update and change report."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Remove duplicates while preserving order
    unique_ids = []
    seen = set()
    for id_ in telegram_ids:
        if id_ not in seen:
            unique_ids.append(id_)
            seen.add(id_)
    
    if not unique_ids:
        logger.warning("No Telegram IDs found to save")
        return
    
    # Determine changes
    added = []
    removed = []
    if incremental and previous_ids is not None:
        prev_set = set(previous_ids)
        curr_set = set(unique_ids)
        added = list(curr_set - prev_set)
        removed = list(prev_set - curr_set)
    
    # Save as TXT (always)
    txt_path = output_path / config.OUTPUT_TXT
    with txt_path.open('w', encoding='utf-8') as f:
        for id_ in unique_ids:
            f.write(f"{id_}\n")
    logger.info(f"Saved TXT to: {txt_path}")
    
    # Save as JSON (if requested)
    if output_format in ['json', 'both']:
        json_path = output_path / config.OUTPUT_FULL_JSON
        with json_path.open('w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved full data to: {json_path}")
    
    # Save as JSON Lines (if requested)
    if output_format == 'jsonl':
        jsonl_path = output_path / "telegram_ids.jsonl"
        with jsonl_path.open('w', encoding='utf-8') as f:
            for id_ in unique_ids:
                f.write(json.dumps({"id": id_}) + "\n")
        logger.info(f"Saved JSON Lines to: {jsonl_path}")
    
    # Save change report
    if incremental and (added or removed):
        changes_path = output_path / config.OUTPUT_CHANGES_TXT
        with changes_path.open('w', encoding='utf-8') as f:
            if added:
                f.write("Added IDs:\n")
                for id_ in sorted(added):
                    f.write(f"  + {id_}\n")
            if removed:
                f.write("Removed IDs:\n")
                for id_ in sorted(removed):
                    f.write(f"  - {id_}\n")
        logger.info(f"Saved change report to: {changes_path}")
    
    # Save metadata
    if metadata:
        save_metadata(metadata, output_dir)
    
    # Log summary
    logger.info(f"Total unique IDs: {len(unique_ids)}")
    if incremental:
        logger.info(f"New IDs: {len(added)}, Removed IDs: {len(removed)}")


async def async_main(args, logger):
    links = []
    start_time = datetime.now()
    
    try:
        if args.url:
            logger.info(f"Downloading from single URL: {args.url}")
            if args.async_mode:
                # Single URL async
                links = await fetch_all_links([args.url], max_workers=1)
            else:
                links = load_links_from_url(args.url)
        
        elif args.input_file:
            input_path = Path(args.input_file)
            if not input_path.exists():
                logger.error(f"Input file not found: {args.input_file}")
                sys.exit(1)
            
            logger.info(f"Reading URL list from: {args.input_file}")
            with input_path.open('r', encoding='utf-8') as f:
                url_list = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not url_list:
                logger.error("No URLs found in input file")
                sys.exit(1)
            
            logger.info(f"Found {len(url_list)} URLs in input file")
            if args.async_mode:
                links = await collect_links_from_urls_async(url_list, logger, max_workers=args.workers)
            else:
                links = collect_links_from_urls_sync(url_list, logger, max_workers=args.workers)
        
        else:
            logger.error("Either --input-file or --url must be specified")
            sys.exit(1)
        
        if not links:
            logger.error("No config links found from any source")
            sys.exit(1)
        
        logger.info(f"Total config lines collected: {len(links)}")
        
        # Load previous IDs for incremental update
        previous_ids = []
        if not args.no_incremental:
            txt_path = Path(args.output) / config.OUTPUT_TXT
            previous_ids = load_previous_ids(str(txt_path))
            logger.info(f"Loaded {len(previous_ids)} previous IDs")
        
        parser = Parser()
        results = parser.parse_links(links)
        
        telegram_ids = []
        full_data = []
        
        for result in results:
            ids = result.get('found_telegram_ids', [])
            if ids:
                telegram_ids.extend(ids)
                full_data.append(result)
        
        # Save intermediate results (in case of crash)
        if args.output:
            temp_path = Path(args.output) / (config.OUTPUT_TXT + ".intermediate")
            save_intermediate_results(telegram_ids, str(temp_path))
        
        # Prepare metadata
        metadata = {
            "run_time": start_time.isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "input_file": args.input_file,
            "url": args.url,
            "total_links": len(links),
            "parsed_results": len(results),
            "unique_ids": len(set(telegram_ids)),
            "total_occurrences": len(telegram_ids),
            "output_format": args.format,
            "async_mode": args.async_mode,
            "workers": args.workers,
            "incremental": not args.no_incremental
        }
        
        save_results(
            telegram_ids=telegram_ids,
            output_dir=args.output,
            output_format=args.format,
            full_data=full_data,
            logger=logger,
            incremental=not args.no_incremental,
            previous_ids=previous_ids,
            metadata=metadata
        )
        
        unique_count = len(set(telegram_ids))
        logger.info(f"✅ Extraction complete. Found {len(telegram_ids)} occurrences, {unique_count} unique IDs")
        
        if unique_count > 0:
            print("\n📊 Found Telegram IDs:")
            for id_ in sorted(set(telegram_ids)):
                print(f"  {id_}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    if args.async_mode:
        asyncio.run(async_main(args, logger))
    else:
        # Run synchronous version
        # We'll reuse async_main but with async_mode False, but simpler: just call a sync version
        # For simplicity, we'll adapt the logic: we'll create a wrapper that runs async_main with sync_mode fallback
        # But to avoid duplication, we'll just run async_main with args (it will handle both)
        asyncio.run(async_main(args, logger))


if __name__ == "__main__":
    main()
