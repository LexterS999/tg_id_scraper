"""
Configuration settings for the Telegram ID Parser
"""

import os
import random

# Default settings
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_OUTPUT_FORMAT = "both"  # 'json', 'txt', 'both', 'jsonl'

# Regex patterns
TELEGRAM_ID_PATTERN = r'@[a-zA-Z0-9_]{5,32}'
TELEGRAM_ID_PATTERN_STRICT = r'(?<![a-zA-Z0-9_])@[a-zA-Z0-9_]{5,32}(?![a-zA-Z0-9_])'

# URL parameters to check for IDs (now we check all, but kept for reference)
URL_PARAMS_TO_CHECK = ['host', 'sni', 'server', 'domain', 'add']

# Comment delimiters
COMMENT_DELIMITERS = ['#', '--', '//']

# Maximum file size for download (10 MB)
MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024

# Maximum lines to read from a file when streaming
MAX_LINES = 100000

# Supported protocols (extended)
SUPPORTED_PROTOCOLS = [
    'vless://', 'vmess://', 'trojan://', 'ss://', 'ssr://',
    'hysteria://', 'tuic://'
]

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "parser.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Output filenames
OUTPUT_TXT = "telegram_ids.txt"      # Simple list (now contains URLs)
OUTPUT_FULL_JSON = "parsed_configs.json"
OUTPUT_CHANGES_TXT = "changes.txt"   # Report of changes
OUTPUT_METADATA_JSON = "metadata.json"  # Run metadata

# Cache settings
CACHE_TTL = 3600  # seconds (1 hour)
CACHE_MAX_SIZE = 128

# Default number of parallel workers
DEFAULT_WORKERS = 10

# User-Agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.50",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.131 Mobile Safari/537.36"
]

# Сжатие JSON
COMPRESS_JSON = True  # если True, файл будет в формате .json.gz


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)
