"""Configuration — env vars with validation, constants, send windows.
Fail fast on missing critical config. No defaults for secrets."""

import os
import sys
from datetime import time


def _require(key: str) -> str:
    """Get required env var or exit with clear message."""
    val = os.environ.get(key, "").strip()
    if not val:
        print(f"FATAL: Required environment variable {key} is not set.", file=sys.stderr)
        sys.exit(1)
    return val


def _optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


# --- Twitter OAuth 1.0a ---
CONSUMER_KEY = ""
CONSUMER_KEY_SECRET = ""
ACCESS_TOKEN = ""
ACCESS_TOKEN_SECRET = ""

# --- Claude ---
ANTHROPIC_API_KEY = ""

# --- Dashboard auth ---
DASHBOARD_USERNAME = ""
DASHBOARD_PASSWORD = ""
AUTH_SECRET_KEY = ""

# --- Email (optional) ---
GMAIL_ADDRESS = ""
GMAIL_APP_PASSWORD = ""
ALERT_RECIPIENT_EMAIL = ""

# --- Behavior ---
COOLDOWN_DAYS = 7
HOT_TWEET_THRESHOLD = 50000
MONITOR_INTERVAL_MINUTES = 15
SEND_CHECK_INTERVAL_MINUTES = 1
RATE_LIMIT_BUDGET = 55  # out of Twitter's 60 per 15-min window
MAX_TWEET_LENGTH = 280

# Search queries
SEARCH_QUERIES = [
    "gstack",
    "g-stack",
    '"garry tan" gstack',
    "@garrytan gstack",
    "gstack-auto",
]

# Send windows (name, start_hour, end_hour) — Eastern Time
SEND_WINDOWS = [
    ("morning", time(9, 0), time(11, 0)),
    ("lunch", time(12, 0), time(14, 0)),
    ("evening", time(17, 0), time(19, 0)),
]

# Database
DB_PATH = "data/gstack_replies.db"

# Cookie TTL
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days


def load_config() -> None:
    """Load and validate all config from env vars. Call once at startup."""
    global CONSUMER_KEY, CONSUMER_KEY_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
    global ANTHROPIC_API_KEY, DASHBOARD_USERNAME, DASHBOARD_PASSWORD, AUTH_SECRET_KEY
    global GMAIL_ADDRESS, GMAIL_APP_PASSWORD, ALERT_RECIPIENT_EMAIL
    global COOLDOWN_DAYS, HOT_TWEET_THRESHOLD, DB_PATH

    CONSUMER_KEY = _require("CONSUMER_KEY")
    CONSUMER_KEY_SECRET = _require("CONSUMER_KEY_SECRET")
    ACCESS_TOKEN = _require("ACCESS_TOKEN")
    ACCESS_TOKEN_SECRET = _require("ACCESS_TOKEN_SECRET")
    ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")
    DASHBOARD_USERNAME = _require("DASHBOARD_USERNAME")
    DASHBOARD_PASSWORD = _require("DASHBOARD_PASSWORD")
    AUTH_SECRET_KEY = _require("AUTH_SECRET_KEY")

    GMAIL_ADDRESS = _optional("GMAIL_ADDRESS")
    GMAIL_APP_PASSWORD = _optional("GMAIL_APP_PASSWORD")
    ALERT_RECIPIENT_EMAIL = _optional("ALERT_RECIPIENT_EMAIL")

    COOLDOWN_DAYS = int(_optional("COOLDOWN_DAYS", "7"))
    HOT_TWEET_THRESHOLD = int(_optional("HOT_TWEET_THRESHOLD", "50000"))
    DB_PATH = _optional("DB_PATH", "data/gstack_replies.db")
