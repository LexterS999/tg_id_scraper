#!/usr/bin/env python3
"""
Main entry point for Telegram ID Parser
"""

import os
import sys
import argparse
import logging
from pathlib import Path
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
  python main.py -i subscriptions.txt
  python main.py -u https://example.com/configs.txt -o results
  python main.py -i data.txt -f json -v
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        help="Path to input file with links",
        required=False
    )
    
    parser.add_argument(
        '-u', '--url',
        type=str,
        help="URL to download and parse",
        required=False
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


def save_results(
    telegram_ids: List[str],
    output_dir: str,
    output_format: str,
    full_data: Optional[List[dict]] = None,
    logger: logging.Logger = None
):
    """Save extracted Telegram IDs to files"""
    
    # Create output directory if it doesn't exist
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
    
    # Save as JSON
    if output_format in ['json', 'both']:
        json_path = os.path.join(output_dir, config.OUTPUT_JSON)
        parser.save_json(unique_ids, json_path)
        logger.info(f"Saved JSON to: {json_path}")
        
        if full_data:
            full_json_path = os.path.join(output_dir, config.OUTPUT_FULL_JSON)
            parser.save_json(full_data, full_json_path)
            logger.info(f"Saved full data to: {full_json_path}")
    
    # Save as TXT
    if output_format in ['txt', 'both']:
        txt_path = os.path.join(output_dir, config.OUTPUT_TXT)
        with open(txt_path, 'w', encoding='utf-8') as f:
            for id_ in unique_ids:
                f.write(f"{id_}\n")
        logger.info(f"Saved TXT to: {txt_path}")


def main():
    """Main execution function"""
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    # Validate input source
    if not args.input and not args.url:
        logger.error("Either --input or --url must be specified")
        sys.exit(1)
    
    links = []
    
    try:
        if args.input:
            logger.info(f"Loading links from file: {args.input}")
            links = load_links_from_file(args.input)
        elif args.url:
            logger.info(f"Downloading links from URL: {args.url}")
            links = load_links_from_url(args.url)
        
        if not links:
            logger.error("No links found in source")
            sys.exit(1)
        
        logger.info(f"Loaded {len(links)} links")
        
        # Parse links
        parser = Parser()
        results = parser.parse_links(links)
        
        # Extract Telegram IDs
        telegram_ids = []
        full_data = []
        
        for result in results:
            ids = extract_telegram_ids(result['comment'])
            # Also check in host/sni parameters
            for param in ['host', 'sni', 'server']:
                if param in result and result[param]:
                    ids.extend(extract_telegram_ids(result[param]))
            
            if ids:
                telegram_ids.extend(ids)
                result['found_ids'] = ids
                full_data.append(result)
                
                logger.debug(f"Found IDs in {result.get('comment', 'unknown')}: {ids}")
        
        # Save results
        save_results(
            telegram_ids=telegram_ids,
            output_dir=args.output,
            output_format=args.format,
            full_data=full_data,
            logger=logger
        )
        
        # Print summary
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
