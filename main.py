#!/usr/bin/env python3
"""
Main entry point for Telegram ID Parser
"""

import os
import sys
import argparse
import logging
import json
from typing import List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from parser.core import Parser
from parser.utils import (
    load_links_from_file,
    load_links_from_url,
    load_previous_ids,
    save_intermediate_results
)
from parser.extractors import extract_telegram_ids
import config


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
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
        choices=['json', 'txt', 'both'],
        default=config.DEFAULT_OUTPUT_FORMAT,
        help=f"Output format: json, txt, or both (default: {config.DEFAULT_OUTPUT_FORMAT})"
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
    return parser.parse_args()


def collect_links_from_urls(url_list: List[str], logger: logging.Logger, max_workers: int = 10) -> List[str]:
    all_links = []
    urls = [u.strip() for u in url_list if u.strip() and not u.startswith('#')]
    if not urls:
        return all_links

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


def save_results(
    telegram_ids: List[str],
    output_dir: str,
    output_format: str,
    full_data: Optional[List[dict]] = None,
    logger: logging.Logger = None,
    incremental: bool = True,
    previous_ids: List[str] = None
):
    """Save extracted Telegram IDs to files, with incremental update and change report."""
    os.makedirs(output_dir, exist_ok=True)
    
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
    
    # Save as Python module
    if output_format in ['json', 'both']:
        py_path = os.path.join(output_dir, config.OUTPUT_JSON)
        source_urls = [f"https://t.me/s/{id_.lstrip('@')}" for id_ in unique_ids]
        py_content = "SOURCE_URLS = [\n"
        for url in source_urls:
            py_content += f'    "{url}",\n'
        py_content += "]"
        with open(py_path, 'w', encoding='utf-8') as f:
            f.write(py_content)
        logger.info(f"Saved Python module to: {py_path}")
        
        if full_data:
            full_json_path = os.path.join(output_dir, config.OUTPUT_FULL_JSON)
            with open(full_json_path, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved full data to: {full_json_path}")
    
    # Save as TXT
    if output_format in ['txt', 'both']:
        txt_path = os.path.join(output_dir, config.OUTPUT_TXT)
        with open(txt_path, 'w', encoding='utf-8') as f:
            for id_ in unique_ids:
                f.write(f"{id_}\n")
        logger.info(f"Saved TXT to: {txt_path}")
    
    # Save change report
    if incremental and (added or removed):
        changes_path = os.path.join(output_dir, config.OUTPUT_CHANGES_TXT)
        with open(changes_path, 'w', encoding='utf-8') as f:
            if added:
                f.write("Added IDs:\n")
                for id_ in sorted(added):
                    f.write(f"  + {id_}\n")
            if removed:
                f.write("Removed IDs:\n")
                for id_ in sorted(removed):
                    f.write(f"  - {id_}\n")
        logger.info(f"Saved change report to: {changes_path}")
    
    # Log summary
    logger.info(f"Total unique IDs: {len(unique_ids)}")
    if incremental:
        logger.info(f"New IDs: {len(added)}, Removed IDs: {len(removed)}")


def main():
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    links = []
    
    try:
        if args.url:
            logger.info(f"Downloading from single URL: {args.url}")
            links = load_links_from_url(args.url)
        
        elif args.input_file:
            if not os.path.exists(args.input_file):
                logger.error(f"Input file not found: {args.input_file}")
                sys.exit(1)
            
            logger.info(f"Reading URL list from: {args.input_file}")
            with open(args.input_file, 'r', encoding='utf-8') as f:
                url_list = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not url_list:
                logger.error("No URLs found in input file")
                sys.exit(1)
            
            logger.info(f"Found {len(url_list)} URLs in input file")
            links = collect_links_from_urls(url_list, logger, max_workers=args.workers)
        
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
            txt_path = os.path.join(args.output, config.OUTPUT_TXT)
            previous_ids = load_previous_ids(txt_path)
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
            temp_path = os.path.join(args.output, config.OUTPUT_TXT + ".intermediate")
            save_intermediate_results(telegram_ids, temp_path)
        
        save_results(
            telegram_ids=telegram_ids,
            output_dir=args.output,
            output_format=args.format,
            full_data=full_data,
            logger=logger,
            incremental=not args.no_incremental,
            previous_ids=previous_ids
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


if __name__ == "__main__":
    main()
