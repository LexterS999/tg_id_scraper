#!/usr/bin/env python3
"""
Example script demonstrating how to use the Telegram ID Parser
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser import Parser, load_links_from_file

# Load sample links
sample_file = os.path.join(os.path.dirname(__file__), 'sample.txt')
links = load_links_from_file(sample_file)

print(f"Loaded {len(links)} links from sample file")

# Create parser instance
parser = Parser()

# Parse all links
results = parser.parse_links(links)

print(f"\nParsed {len(results)} links")

# Extract all Telegram IDs
all_ids = parser.extract_all_telegram_ids(links)

print(f"\nFound {len(all_ids)} Telegram IDs:")
unique_ids = set(all_ids)
for id_ in sorted(unique_ids):
    print(f"  {id_}")

# Show detailed results
print("\nDetailed results:")
for result in results:
    if 'found_telegram_ids' in result:
        print(f"  {result.get('uuid', 'N/A')[:8]}... -> {result['found_telegram_ids']}")
