#!/usr/bin/env python3
"""
Main entry point for Telegram ID Parser
"""

import os
import sys
import argparse
import logging
import json
from typing import List, Optional

from parser.core import Parser
from parser.utils import load_links_from_file, load_links_from_url
from parser.extractors import extract_telegram_ids
import config


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments"""
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
    
    return parser.parse_args()


def collect_links_from_urls(url_list: List[str], logger: logging.Logger) -> List[str]:
    """
    Download each URL and extract config lines (vless://, vmess://, etc.)
    """
    all_links = []
    for url in url_list:
        url = url.strip()
        if not url or url.startswith('#'):
            continue
        try:
            logger.info(f"Fetching configs from: {url}")
            links = load_links_from_url(url)
            logger.debug(f"Got {len(links)} config lines from {url}")
            all_links.extend(links)
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
    return all_links


def save_results(
    telegram_ids: List[str],
    output_dir: str,
    output_format: str,
    full_data: Optional[List[dict]] = None,
    logger: logging.Logger = None
):
    """Save extracted Telegram IDs to files"""
    
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
    
    # Save as JSON (Python list format)
    if output_format in ['json', 'both']:
        json_path = os.path.join(output_dir, config.OUTPUT_JSON)
        # Generate SOURCE_URLS list
        source_urls = [f"https://t.me/s/{id_.lstrip('@')}" for id_ in unique_ids]
        json_content = "SOURCE_URLS = [\n"
        for url in source_urls:
            json_content += f'    "{url}",\n'
        json_content += "]"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_content)
        logger.info(f"Saved JSON to: {json_path}")
        
        if full_data:
            full_json_path = os.path.join(output_dir, config.OUTPUT_FULL_JSON)
            with open(full_json_path, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved full data to: {full_json_path}")
    
    # Save as TXT (simple list of @ids)
    if output_format in ['txt', 'both']:
        txt_path = os.path.join(output_dir, config.OUTPUT_TXT)
        with open(txt_path, 'w', encoding='utf-8') as f:
            for id_ in unique_ids:
                f.write(f"{id_}\n")
        logger.info(f"Saved TXT to: {txt_path}")


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
            links = collect_links_from_urls(url_list, logger)
        
        else:
            logger.error("Either --input-file or --url must be specified")
            sys.exit(1)
        
        if not links:
            logger.error("No config links found from any source")
            sys.exit(1)
        
        logger.info(f"Total config lines collected: {len(links)}")
        
        parser = Parser()
        results = parser.parse_links(links)
        
        telegram_ids = []
        full_data = []
        
        for result in results:
            if result.get('comment'):
                ids = extract_telegram_ids(result['comment'])
                if ids:
                    telegram_ids.extend(ids)
                    result['found_ids'] = ids
                    full_data.append(result)
            
            for param in ['host', 'sni', 'server', 'domain']:
                if result.get(param):
                    ids = extract_telegram_ids(str(result[param]))
                    if ids:
                        telegram_ids.extend(ids)
                        if 'found_ids' not in result:
                            result['found_ids'] = []
                        result['found_ids'].extend(ids)
                        if result not in full_data:
                            full_data.append(result)
        
        save_results(
            telegram_ids=telegram_ids,
            output_dir=args.output,
            output_format=args.format,
            full_data=full_data,
            logger=logger
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
