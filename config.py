"""
Configuration settings for the Telegram ID Parser
"""

import os

# Default settings
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_OUTPUT_FORMAT = "both"  # 'json', 'txt', 'both'

# Regex patterns
TELEGRAM_ID_PATTERN = r'@[a-zA-Z0-9_]{5,32}'
TELEGRAM_ID_PATTERN_STRICT = r'(?<![a-zA-Z0-9_])@[a-zA-Z0-9_]{5,32}(?![a-zA-Z0-9_])'

# URL parameters to check for IDs
URL_PARAMS_TO_CHECK = ['host', 'sni', 'server', 'domain', 'add']

# Comment delimiters
COMMENT_DELIMITERS = ['#', '--', '//']

# Maximum file size for download (10 MB)
MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024

# Supported protocols
SUPPORTED_PROTOCOLS = ['vless://', 'trojan://', 'vmess://', 'ss://', 'ssr://']

# Logging
LOG_LEVEL = "INFO"

# Output filenames
OUTPUT_JSON = "telegram_ids.json"
OUTPUT_TXT = "telegram_ids.txt"
OUTPUT_FULL_JSON = "parsed_configs.json"
