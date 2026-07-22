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
from typing import List, Optional, Set, Dict, Any
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from collections import Counter

from parser.core import Parser
from parser.utils import (
    load_links_from_file,
    load_links_from_url,
    load_previous_ids,
    save_intermediate_results,
    save_metadata,
    save_json
)
from parser.async_utils import fetch_all_links
from parser.extractors import extract_telegram_ids
import config


def setup_logging(verbose: bool = False):
    """
    Настройка логирования:
    - в консоль выводятся только критические ошибки (ERROR и выше)
    - в файл пишется всё (DEBUG), с ротацией
    """
    from logging.handlers import RotatingFileHandler

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Все уровни обрабатываются

    # Консольный обработчик — только ERROR и выше (если не verbose)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO if verbose else logging.ERROR)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(console_formatter)
    logger.addHandler(console)

    # Файловый обработчик — все сообщения, с ротацией
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
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
        help="Enable verbose output (also shows INFO level in console)"
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
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https', 'file')
    except Exception:
        return False


def collect_links_from_urls_sync(url_list: List[str], logger: logging.Logger, max_workers: int = 10) -> List[str]:
    all_links = []
    urls = [u.strip() for u in url_list if u.strip() and not u.startswith('#')]
    if not urls:
        return all_links

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
                logger.info(f"Downloaded {len(links)} config lines from {url}")
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
    return all_links


async def collect_links_from_urls_async(url_list: List[str], logger: logging.Logger, max_workers: int = 10) -> List[str]:
    urls = [u.strip() for u in url_list if u.strip() and not u.startswith('#')]
    if not urls:
        return []
    valid_urls = [u for u in urls if is_valid_url(u)]
    invalid_urls = [u for u in urls if not is_valid_url(u)]
    if invalid_urls:
        logger.warning(f"Skipping invalid URLs: {invalid_urls}")
    urls = valid_urls

    logger.info(f"Fetching {len(urls)} URLs with {max_workers} workers")
    results = await fetch_all_links(urls, max_workers=max_workers)
    logger.info(f"Fetched {len(results)} config lines from {len(urls)} sources")
    return results


def generate_summary(
    sources_count: int,
    sources_loaded: int,
    total_config_lines: int,
    parsed_count: int,
    parsed_with_ids: int,
    total_id_occurrences: int,
    unique_ids: int,
    protocol_counts: Dict[str, int],
    incremental: bool,
    added: List[str],
    removed: List[str],
    duration: float,
    output_dir: str
) -> str:
    """Генерирует текстовую сводку результатов."""
    lines = []
    lines.append("=" * 60)
    lines.append("📊 SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Sources (URLs)          : {sources_count} total, {sources_loaded} loaded successfully")
    lines.append(f"Config lines collected  : {total_config_lines}")
    lines.append(f"Parsed successfully     : {parsed_count}")
    lines.append(f"Containing Telegram IDs : {parsed_with_ids}")
    lines.append(f"Total ID occurrences    : {total_id_occurrences}")
    lines.append(f"Unique IDs              : {unique_ids}")
    if incremental:
        lines.append(f"Added (new)             : {len(added)}")
        lines.append(f"Removed (expired)       : {len(removed)}")
    lines.append(f"Duration                : {duration:.2f} seconds")
    lines.append(f"Output directory        : {output_dir}")
    if protocol_counts:
        lines.append("")
        lines.append("Protocol distribution:")
        for proto, count in sorted(protocol_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {proto:12s} : {count}")
    lines.append("=" * 60)
    return "\n".join(lines)


def print_summary(
    sources_count: int,
    sources_loaded: int,
    total_config_lines: int,
    parsed_count: int,
    parsed_with_ids: int,
    total_id_occurrences: int,
    unique_ids: int,
    protocol_counts: Dict[str, int],
    incremental: bool,
    added: List[str],
    removed: List[str],
    duration: float,
    output_dir: str,
    logger: logging.Logger
):
    """Выводит сводку в консоль и в лог."""
    summary = generate_summary(
        sources_count, sources_loaded, total_config_lines,
        parsed_count, parsed_with_ids, total_id_occurrences,
        unique_ids, protocol_counts, incremental, added, removed,
        duration, output_dir
    )
    print(summary)
    logger.info("\n" + summary)


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

    # Определяем изменения для инкрементального режима
    added = []
    removed = []
    if incremental and previous_ids is not None:
        prev_set = set(previous_ids)
        curr_set = set(unique_ids)
        added = list(curr_set - prev_set)
        removed = list(prev_set - curr_set)

    # Сохраняем как TXT — теперь в формате URL
    txt_path = output_path / config.OUTPUT_TXT
    with txt_path.open('w', encoding='utf-8') as f:
        for id_ in unique_ids:
            clean_id = id_.lstrip('@')
            f.write(f"https://t.me/s/{clean_id}\n")
    logger.info(f"Saved TXT (URLs) to: {txt_path}")

    # JSON с полными данными (если требуется) — теперь со сжатием
    if output_format in ['json', 'both']:
        json_path = output_path / config.OUTPUT_FULL_JSON
        save_json(full_data, str(json_path), compress=config.COMPRESS_JSON)
        logger.info(f"Saved full data to: {json_path}" + (".gz" if config.COMPRESS_JSON else ""))

    # JSON Lines (если требуется)
    if output_format == 'jsonl':
        jsonl_path = output_path / "telegram_ids.jsonl"
        with jsonl_path.open('w', encoding='utf-8') as f:
            for id_ in unique_ids:
                f.write(json.dumps({"id": id_}) + "\n")
        logger.info(f"Saved JSON Lines to: {jsonl_path}")

    # Отчёт об изменениях
    if incremental and (added or removed):
        changes_path = output_path / config.OUTPUT_CHANGES_TXT
        with changes_path.open('w', encoding='utf-8') as f:
            if added:
                f.write("Added IDs:\n")
                for id_ in sorted(added):
                    clean_id = id_.lstrip('@')
                    f.write(f"  + https://t.me/s/{clean_id}\n")
            if removed:
                f.write("Removed IDs:\n")
                for id_ in sorted(removed):
                    clean_id = id_.lstrip('@')
                    f.write(f"  - https://t.me/s/{clean_id}\n")
        logger.info(f"Saved change report to: {changes_path}")

    # Метаданные
    if metadata:
        save_metadata(metadata, output_dir)

    # Возвращаем added, removed, unique_ids для сводки
    return added, removed, unique_ids


async def async_main(args, logger):
    links = []
    start_time = datetime.now()
    sources_loaded = 0
    sources_count = 0

    try:
        if args.url:
            logger.info(f"Downloading from single URL: {args.url}")
            sources_count = 1
            if args.async_mode:
                links = await fetch_all_links([args.url], max_workers=1)
            else:
                links = load_links_from_url(args.url)
            if links:
                sources_loaded = 1

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

            sources_count = len(url_list)
            logger.info(f"Found {sources_count} URLs in input file")
            if args.async_mode:
                links = await collect_links_from_urls_async(url_list, logger, max_workers=args.workers)
            else:
                links = collect_links_from_urls_sync(url_list, logger, max_workers=args.workers)

            # sources_loaded — приблизительно, считаем что все загружены, если есть ссылки
            sources_loaded = len(url_list) if links else 0

        else:
            logger.error("Either --input-file or --url must be specified")
            sys.exit(1)

        if not links:
            logger.warning("No config links collected from any source. Check your URLs.")
            return

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
        protocol_counter = Counter()

        for result in results:
            ids = result.get('found_telegram_ids', [])
            if ids:
                telegram_ids.extend(ids)
                full_data.append(result)
                # Считаем протоколы
                proto = result.get('protocol', 'unknown')
                protocol_counter[proto] += 1

        # Save intermediate results (in case of crash)
        if args.output:
            temp_path = Path(args.output) / (config.OUTPUT_TXT + ".intermediate")
            save_intermediate_results(telegram_ids, str(temp_path))

        # Сохраняем результаты и получаем статистику изменений
        added, removed, unique_ids = save_results(
            telegram_ids=telegram_ids,
            output_dir=args.output,
            output_format=args.format,
            full_data=full_data,
            logger=logger,
            incremental=not args.no_incremental,
            previous_ids=previous_ids
        )

        # Metadata
        metadata = {
            "run_time": start_time.isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "input_file": args.input_file,
            "url": args.url,
            "total_links": len(links),
            "parsed_results": len(results),
            "unique_ids": len(unique_ids),
            "total_occurrences": len(telegram_ids),
            "output_format": args.format,
            "async_mode": args.async_mode,
            "workers": args.workers,
            "incremental": not args.no_incremental,
            "sources_count": sources_count,
            "sources_loaded": sources_loaded
        }
        save_metadata(metadata, args.output)

        # Выводим сводку
        parsed_with_ids = len(full_data)
        total_id_occurrences = len(telegram_ids)
        unique_count = len(unique_ids)
        duration = (datetime.now() - start_time).total_seconds()

        print_summary(
            sources_count=sources_count,
            sources_loaded=sources_loaded,
            total_config_lines=len(links),
            parsed_count=len(results),
            parsed_with_ids=parsed_with_ids,
            total_id_occurrences=total_id_occurrences,
            unique_ids=unique_count,
            protocol_counts=dict(protocol_counter),
            incremental=not args.no_incremental,
            added=added if not args.no_incremental else [],
            removed=removed if not args.no_incremental else [],
            duration=duration,
            output_dir=args.output,
            logger=logger
        )

        logger.info(f"Found {total_id_occurrences} occurrences, {unique_count} unique IDs")

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    asyncio.run(async_main(args, logger))


if __name__ == "__main__":
    main()
