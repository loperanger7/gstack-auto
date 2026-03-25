"""App configuration from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32).hex())
    DATABASE = os.path.join(os.path.dirname(__file__), '..', 'instance', 'app.db')

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    # Anthropic
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

    # Admin bootstrap
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')

    # Rate limits
    MAX_SESSIONS_PER_DAY = int(os.environ.get('MAX_SESSIONS_PER_DAY', '3'))
    MAX_MESSAGES_PER_SESSION = int(os.environ.get('MAX_MESSAGES_PER_SESSION', '100'))

    # Spend ceiling (tokens per day)
    DAILY_TOKEN_CEILING = int(os.environ.get('DAILY_TOKEN_CEILING', '500000'))

    # SMTP (for build completion notifications)
    SMTP_HOST = os.environ.get('PATTAYA_SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('PATTAYA_SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('PATTAYA_SMTP_USER', '')
    SMTP_PASS = os.environ.get('PATTAYA_SMTP_PASS', '')
    NOTIFY_FROM = os.environ.get('NOTIFY_FROM', '')

    # Server
    BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000')


class TestConfig(Config):
    TESTING = True
    DATABASE = ':memory:'
    SECRET_KEY = 'test-secret-key'
    GOOGLE_CLIENT_ID = 'test-client-id'
    GOOGLE_CLIENT_SECRET = 'test-client-secret'
    ANTHROPIC_API_KEY = 'test-api-key'
    ADMIN_EMAIL = 'admin@test.com'
    DAILY_TOKEN_CEILING = 100000
